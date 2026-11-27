package tools

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"regexp"
	"sort"
	"strconv"
	"strings"

	"github.com/ykylee/standard_ai_workflow/hub-go/internal/assets"
	"github.com/ykylee/standard_ai_workflow/hub-go/internal/judge"
	"github.com/ykylee/standard_ai_workflow/hub-go/internal/store"
)

// 1.x 파일 읽기 — Python hub/migrate1x.py 의 parse_task_file · parse_handoff · hand_written · parse_times.

// taskLabels: 정본 라벨이 앞, 옛 표기가 뒤 (common/project_docs.TASK_FIELD_LABELS · ALIASES).
var taskLabels = map[string][]string{
	"status": {"Status", "상태"}, "priority": {"Priority", "우선순위"},
	"affected_documents": {"Affected documents", "영향 문서"}, "summary": {"Description", "작업 내용"},
	"done_criteria": {"Completion criteria", "완료 기준"}, "progress": {"Progress", "진행 현황"},
	"next_step": {"Next session starting point", "다음 세션 시작 포인트"}, "risks": {"Remaining risks", "남은 리스크"},
	"result": {"Result", "작업 결과"}, "validation": {"Verification", "검증 결과"}, "follow_up": {"Follow-up", "후속 작업"},
}

var (
	migFrontmatter = regexp.MustCompile(`(?s)\A---\n(.*?)\n---\n`)
	migMetaLine    = regexp.MustCompile(`(?m)^(\w+):\s*(.*?)\s*$`)
	migHeader      = regexp.MustCompile(`(?m)^#\s+(\S+)\s+[—-]\s+(.+)$`)
	migNextSection = regexp.MustCompile(`(?m)^## `)
	migDate        = regexp.MustCompile(`^\d{4}-\d{2}-\d{2}$`)
	migKitLine     = regexp.MustCompile(`^<!-- (?:standard-ai-workflow-kit[^>]*|generated-from:[^>]*) -->$`)
	migHubRegion   = regexp.MustCompile(`(?s)<!-- workflow-hub:begin .*?<!-- workflow-hub:end -->\n?`)
	taskStatuses   = map[string]bool{"planned": true, "in_progress": true, "blocked": true, "done": true}
)

type commitTime struct {
	at  int
	sha string
}

// parseTimes reads `git log --format=@%ct %H --name-only`: the first time a path appears is its last commit.
func parseTimes(output string) map[string]commitTime {
	out := map[string]commitTime{}
	var current *commitTime
	for _, line := range judge.SplitLines(output) {
		line = judge.Strip(line)
		if line == "" {
			continue
		}
		if strings.HasPrefix(line, "@") {
			ct, sha, _ := strings.Cut(line[1:], " ")
			current = nil
			if n, err := strconv.Atoi(ct); err == nil && n >= 0 {
				current = &commitTime{n, sha}
			}
		} else if current != nil {
			if _, seen := out[line]; !seen {
				out[line] = *current
			}
		}
	}
	return out
}

func labelValue(line, key string) (string, bool) {
	text := judge.Strip(line)
	for _, label := range taskLabels[key] {
		prefix := "- " + label + ":"
		if text == prefix || strings.HasPrefix(text, prefix+" ") {
			return judge.Strip(text[len(prefix):]), true
		}
	}
	return "", false
}

func taskListField(lines []string, key string) []string {
	out := []string{}
	for i := range lines {
		if _, ok := labelValue(lines[i], key); !ok {
			continue
		}
		for _, line := range lines[i:] {
			v, ok := labelValue(line, key)
			if !ok {
				break
			}
			if v != "" {
				out = append(out, v)
			}
		}
		break
	}
	return out
}

func taskAffected(lines []string) []string {
	out := []string{}
	for i, line := range lines {
		if v, ok := labelValue(line, "affected_documents"); !ok || v != "" {
			continue
		}
		for _, item := range lines[i+1:] {
			if !strings.HasPrefix(item, "  - ") {
				break
			}
			out = append(out, strings.Trim(judge.Strip(judge.Strip(item)[1:]), "`"))
		}
		break
	}
	return out
}

func mdSection(text, marker string) string {
	head := regexp.MustCompile(`(?m)^## [^\n]*` + regexp.QuoteMeta(marker) + `[^\n]*\n`).FindStringIndex(text)
	if head == nil {
		return ""
	}
	body := text[head[1]:]
	if next := migNextSection.FindStringIndex(body); next != nil {
		body = body[:next[0]]
	}
	if judge.Strip(body) == "" {
		return ""
	}
	return strings.Trim(body, "\n") + "\n"
}

type migTask struct {
	id, title, status, priority, wbs, exempt, description, planMD, progress, created string
	fields                                                                           map[string]any
}

func (t migTask) scan() map[string]any {
	return map[string]any{"id": t.id, "title": t.title, "status": t.status, "priority": t.priority, "wbs": t.wbs,
		"wbs_exempt_reason": t.exempt, "description": t.description, "plan_md": t.planMD, "fields": t.fields,
		"progress_note": t.progress, "created_at": t.created}
}

func parseTaskFile(text string) (migTask, error) {
	var t migTask
	fm := migFrontmatter.FindStringSubmatch(text)
	if fm == nil {
		return t, store.InvalidField("task", "frontmatter 가 없어요")
	}
	meta := map[string]string{}
	for _, m := range migMetaLine.FindAllStringSubmatch(fm[1], -1) {
		meta[m[1]] = m[2]
	}
	t.id = meta["id"]
	if !strings.HasPrefix(t.id, "TASK-") {
		return t, store.InvalidField("task", "frontmatter 에 id 가 없어요")
	}
	lines := judge.SplitLines(text)
	first := func(key string) string {
		if v := taskListField(lines, key); len(v) > 0 {
			return v[0]
		}
		return ""
	}
	t.title = t.id
	for _, m := range migHeader.FindAllStringSubmatch(text, -1) {
		if m[1] == t.id {
			t.title = judge.Strip(m[2])
			break
		}
	}
	if r := []rune(t.title); len(r) > 200 {
		t.title = string(r[:200])
	}
	if t.status = meta["status"]; t.status == "" {
		t.status = first("status")
	}
	if !taskStatuses[t.status] {
		return t, store.InvalidField("status", "1.x 상태가 네 값 밖이에요: "+strconv.Quote(t.status))
	}
	if t.priority = first("priority"); t.priority != "high" && t.priority != "low" {
		t.priority = "medium"
	}
	t.wbs, t.exempt, t.created = meta["wbs"], meta["wbs_exempt_reason"], meta["created_at"]
	if t.planMD = mdSection(text, "🧭 Plan"); t.planMD == "" {
		t.planMD = mdSection(text, "Plan")
	}
	t.fields = map[string]any{}
	putList := func(key string, v []string) {
		if len(v) > 0 {
			t.fields[key] = v
		}
	}
	putList("affected_documents", taskAffected(lines))
	for _, key := range []string{"done_criteria", "risks", "follow_up"} {
		putList(key, taskListField(lines, key))
	}
	for _, pair := range [][2]string{{"result", "result"}, {"validation_result", "validation"}, {"next_step", "next_step"}} {
		if v := strings.Join(taskListField(lines, pair[1]), "\n"); v != "" {
			t.fields[pair[0]] = v
		}
	}
	t.description = strings.Join(taskListField(lines, "summary"), "\n")
	if p := taskListField(lines, "progress"); len(p) > 0 {
		t.progress = p[len(p)-1]
	}
	return t, nil
}

func handoffBullets(text string, heads ...string) []string {
	out := []string{}
	for _, head := range heads {
		body := mdSection(text, head)
		if body == "" {
			continue
		}
		for _, line := range judge.SplitLines(body) {
			line = judge.Strip(line)
			if !strings.HasPrefix(line, "- ") {
				continue
			}
			if v := judge.Strip(line[2:]); v != "" && v != "-" {
				out = append(out, v)
			}
		}
		break
	}
	return out
}

func parseHandoffFile(text string) (map[string]any, []string) {
	data := judge.ParseHandoffText(text, "handoff-copy.md")
	dropped := []string{}
	tasks := func(items []string) []string {
		out := []string{}
		for _, item := range items {
			s := judge.Strip(item)
			if strings.HasPrefix(s, "TASK-") {
				out = append(out, s)
			} else if s != "" && s != "-" {
				dropped = append(dropped, s)
			}
		}
		return out
	}
	str := func(v *string) string {
		if v == nil {
			return ""
		}
		return *v
	}
	out := map[string]any{"baseline": str(data.CurrentBaseline), "focus": str(data.CurrentAxis)}
	out["in_progress"] = tasks(data.InProgressItems)
	out["blocked"] = tasks(data.BlockedItems)
	out["recent_done"] = tasks(data.RecentDoneItems)
	out["next"] = handoffBullets(text, "다음 세션 시작 포인트", "Next session")
	out["risks"] = handoffBullets(text, "남은 리스크", "Remaining risks")
	return out, dropped
}

func knownGenerated(title, body string) bool {
	var known map[string][]string
	if json.Unmarshal(assets.KnownSectionsJSON, &known) != nil {
		return false
	}
	sum := sha256.Sum256([]byte(strings.Join(strings.Fields(body), " ")))
	want := hex.EncodeToString(sum[:])[:16]
	list := known[title]
	i := sort.SearchStrings(list, want)
	return i < len(list) && list[i] == want
}

// handWritten removes kit-generated sections from an entry file and keeps what people wrote.
func handWritten(text string) (string, []string) {
	text = migHubRegion.ReplaceAllString(text, "")
	dropped, kept := []string{}, []string{}
	var head []string
	type section struct {
		title string
		lines []string
	}
	sections := []section{}
	for _, line := range strings.Split(text, "\n") {
		if strings.HasPrefix(line, "## ") {
			sections = append(sections, section{title: judge.Strip(line[3:])})
		} else if n := len(sections); n > 0 {
			sections[n-1].lines = append(sections[n-1].lines, line)
		} else {
			head = append(head, line)
		}
	}
	strip := func(lines []string, dropTitle bool) string {
		out := []string{}
		for _, line := range lines {
			if migKitLine.MatchString(judge.Strip(line)) || (dropTitle && strings.HasPrefix(line, "# ")) {
				continue
			}
			out = append(out, line)
		}
		return judge.Strip(strings.Join(out, "\n"))
	}
	if h := strip(head, true); h != "" && !strings.HasPrefix(h, "- 문서 목적") {
		kept = append(kept, h)
	}
	for _, sec := range sections {
		body := strings.Join(sec.lines, "\n")
		if knownGenerated(sec.title, body) || strings.Contains(body, "<!-- generated-from:") {
			dropped = append(dropped, sec.title)
			continue
		}
		if clean := strip(sec.lines, false); clean != "" {
			kept = append(kept, "## "+sec.title+"\n\n"+clean)
		}
	}
	if len(kept) == 0 {
		return "", dropped
	}
	return strings.Join(kept, "\n\n") + "\n", dropped
}
