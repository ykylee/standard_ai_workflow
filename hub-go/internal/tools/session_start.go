package tools

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"regexp"
	"sort"
	"strconv"
	"strings"

	"github.com/ykylee/standard_ai_workflow/hub-go/internal/store"
)

var branchAheadBehind = regexp.MustCompile(`^# branch\.ab \+(\d+) -(\d+)$`)
var entryGuide = regexp.MustCompile(`<!-- workflow-hub:begin project=\S+ guide=(\S+) sha256=[0-9a-f]{64} -->`)

func sessionStart(s *store.Store, ctx store.Ctx, args map[string]any) (map[string]any, error) {
	p, err := store.NeedCallsign(ctx)
	if err != nil {
		return nil, err
	}
	guideVersion := 0
	_ = s.DB().QueryRow("SELECT COALESCE(MAX(version),0) FROM guide WHERE project_id=?", p.ProjectID).Scan(&guideVersion)
	seen := sql.NullString{}
	var setupComplete int
	_ = s.DB().QueryRow("SELECT guide_version_seen,setup_complete FROM callsign WHERE project_id=? AND id=?", p.ProjectID, p.Callsign).Scan(&seen, &setupComplete)
	currentGuide := fmt.Sprintf("%s+p%d", KitVersion, guideVersion)
	guide := map[string]any{"current": currentGuide, "seen": nil, "changed": !seen.Valid || seen.String != currentGuide}
	if seen.Valid {
		guide["seen"] = seen.String
	}
	if guide["changed"] == true {
		guide["notice"] = "[바뀜] 지침이 바뀌었다 — hub_guide_render 로 진입 파일을 다시 쓰고 먼저 읽는다"
	}
	myTasks, err := queryMaps(s.DB(), `SELECT id,title,status,version,progress_note,progress_at FROM task WHERE project_id=? AND assignee=? AND status!='done' ORDER BY created_at`, p.ProjectID, p.Callsign)
	if err != nil {
		return nil, err
	}
	freeTasks, err := queryMaps(s.DB(), `SELECT id,title,status FROM task WHERE project_id=? AND assignee IS NULL AND status!='done' ORDER BY created_at LIMIT 50`, p.ProjectID)
	if err != nil {
		return nil, err
	}
	commits := map[string][]string{}
	rows, err := s.DB().Query(`SELECT c.task_id,c.sha FROM task_commit c JOIN task t ON t.project_id=c.project_id AND t.id=c.task_id WHERE c.project_id=? AND t.assignee=? AND t.status!='done'`, p.ProjectID, p.Callsign)
	if err != nil {
		return nil, err
	}
	for rows.Next() {
		var taskID, sha string
		if err := rows.Scan(&taskID, &sha); err != nil {
			_ = rows.Close()
			return nil, err
		}
		commits[sha] = append(commits[sha], taskID)
	}
	if err := rows.Err(); err != nil {
		_ = rows.Close()
		return nil, err
	}
	if err := rows.Close(); err != nil {
		return nil, err
	}
	entryRows, err := s.DB().Query(`SELECT path FROM setup_step WHERE project_id=? AND callsign=? AND kind='entry'`, p.ProjectID, p.Callsign)
	if err != nil {
		return nil, err
	}
	entries := []string{}
	for entryRows.Next() {
		var path string
		if err := entryRows.Scan(&path); err != nil {
			_ = entryRows.Close()
			return nil, err
		}
		entries = append(entries, path)
	}
	if err := entryRows.Err(); err != nil {
		_ = entryRows.Close()
		return nil, err
	}
	if err := entryRows.Close(); err != nil {
		return nil, err
	}
	sort.Strings(entries)
	handoff := any(nil)
	var handoffJSON string
	if err := s.DB().QueryRow("SELECT sections_json FROM handoff WHERE project_id=? AND callsign=?", p.ProjectID, p.Callsign).Scan(&handoffJSON); err == nil {
		var sections map[string]any
		if err := jsonUnmarshal(handoffJSON, &sections); err != nil {
			return nil, err
		}
		handoff = map[string]any{"callsign": p.Callsign, "handoff": sections}
	} else if err != sql.ErrNoRows {
		return nil, err
	}
	client, err := localClient(args["client"])
	if err != nil {
		return nil, err
	}
	hub := map[string]any{"guide": guide, "setup_complete": setupComplete != 0, "my_tasks": myTasks, "unassigned_open_tasks": freeTasks, "handoff": handoff, "local_client": client}
	commands := map[string]any{"fetch": []string{"git", "fetch", "--prune"}, "status": []string{"git", "status", "--porcelain=v2", "--branch"}, "default_branch": []string{"git", "rev-parse", "--abbrev-ref", "origin/HEAD"}, "check_ignore": []string{"git", "check-ignore", "-v", ".workflow-hub/env"}}
	for _, path := range entries {
		commands["entry_head:"+path] = []string{"git", "grep", "--no-index", "-h", "-e", "workflow-hub:begin", "--", path}
	}
	shas := make([]string, 0, len(commits))
	for sha := range commits {
		shas = append(shas, sha)
	}
	sort.Strings(shas)
	for _, sha := range shas {
		commands["commit:"+sha] = []string{"git", "cat-file", "-e", sha + "^{commit}"}
	}
	confirmed := []string{"hub: 닿음", "hub: 지침 판", "hub: 내 task", "hub: 맡은 이 없는 열린 task", "hub: 내 handoff"}
	results, exists := args["repo_results"]
	if !exists || results == nil {
		return map[string]any{"phase": 1, "hub": hub, "repo_check": map[string]any{"commands": commands, "rules": []string{"각 명령을 저장소 뿌리에서 그대로 돌리고 {name: {rc, output}} 로 repo_results 에 싣는다 — 이름의 : · . 를 키로 못 싣는 하네스는 [{name, rc, output}] 목록으로", "명령을 고치거나 건너뛰지 않는다 — 못 돌린 명령은 싣지 않는다 (미확인으로 남는다)"}}, "verdict": "unconfirmed", "confirmed": confirmed, "unconfirmed": unconfirmedCommands(commands), "next": "hub_session_start(repo_results=…)"}, nil
	}
	return sessionStartPhase2(s, ctx, hub, commands, entries, commits, confirmed, results)
}

func queryMaps(dbq interface {
	Query(string, ...any) (*sql.Rows, error)
}, query string, args ...any) ([]map[string]any, error) {
	rows, err := dbq.Query(query, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	cols, err := rows.Columns()
	if err != nil {
		return nil, err
	}
	out := []map[string]any{}
	for rows.Next() {
		values := make([]any, len(cols))
		dest := make([]any, len(cols))
		for i := range values {
			dest[i] = &values[i]
		}
		if err := rows.Scan(dest...); err != nil {
			return nil, err
		}
		row := map[string]any{}
		for i, col := range cols {
			if b, ok := values[i].([]byte); ok {
				row[col] = string(b)
			} else {
				row[col] = values[i]
			}
		}
		out = append(out, row)
	}
	return out, rows.Err()
}

func localClient(raw any) (map[string]any, error) {
	if raw == nil {
		return map[string]any{"status": "none", "note": "선택 클라이언트 없음 — 보낼편지함 · 캐시를 쓰지 않는 환경이다 (R12.1)"}, nil
	}
	c, ok := raw.(map[string]any)
	if !ok {
		return nil, store.InvalidField("client", "{version, outbox_pending(0 이상 정수)}")
	}
	for key := range c {
		if key != "version" && key != "outbox_pending" {
			return nil, store.InvalidField("client", "{version, outbox_pending(0 이상 정수)}")
		}
	}
	pending, ok := intValue(c["outbox_pending"])
	if !ok || pending < 0 {
		return nil, store.InvalidField("client", "{version, outbox_pending(0 이상 정수)}")
	}
	version := ""
	if value, exists := c["version"]; exists && value != nil {
		version = fmt.Sprint(value)
	}
	out := map[string]any{"status": "present", "version": version, "outbox_pending": pending}
	if pending > 0 {
		out["notice"] = fmt.Sprintf("보낼편지함에 %d건 — hub_client.py flush 로 보낸다 (409 는 남는다, D4)", pending)
	}
	return out, nil
}

func unconfirmedCommands(commands map[string]any) []string {
	names := make([]string, 0, len(commands))
	for name := range commands {
		names = append(names, name)
	}
	sort.Strings(names)
	out := make([]string, 0, len(names))
	for _, name := range names {
		out = append(out, "repo: "+name)
	}
	return out
}

func normalizeRepoResults(raw any) (map[string]any, error) {
	switch v := raw.(type) {
	case map[string]any:
		return v, nil
	case []any:
		out := map[string]any{}
		for i, item := range v {
			row, ok := item.(map[string]any)
			if !ok {
				return nil, store.InvalidField(fmt.Sprintf("repo_results[%d]", i), "{name, rc, output}")
			}
			name, ok := row["name"].(string)
			if !ok {
				return nil, store.InvalidField(fmt.Sprintf("repo_results[%d].name", i), "문자열이어야 한다")
			}
			if _, exists := out[name]; exists {
				return nil, store.InvalidField(fmt.Sprintf("repo_results[%d].name", i), "같은 이름이 두 번: "+name)
			}
			output := row["output"]
			if output == nil {
				output = ""
			}
			out[name] = map[string]any{"rc": row["rc"], "output": output}
		}
		return out, nil
	default:
		return nil, store.InvalidField("repo_results", "{name: {rc, output}} 객체 또는 [{name, rc, output}] 목록")
	}
}

func sessionStartPhase2(s *store.Store, ctx store.Ctx, hub map[string]any, commands map[string]any, entries []string, commits map[string][]string, confirmed []string, raw any) (map[string]any, error) {
	results, err := normalizeRepoResults(raw)
	if err != nil {
		return nil, err
	}
	unknown := []string{}
	for name := range results {
		if _, ok := commands[name]; !ok {
			unknown = append(unknown, name)
		}
	}
	if len(unknown) > 0 {
		sort.Strings(unknown)
		return nil, store.InvalidField("repo_results", "요청하지 않은 명령 결과: "+strings.Join(unknown, ", "))
	}
	unconfirmed := []string{}
	findings := []string{}
	verdict := "start"
	get := func(name string) (int, string, bool) {
		raw, ok := results[name]
		if !ok {
			return 0, "", false
		}
		row, ok := raw.(map[string]any)
		if !ok {
			return 0, "", false
		}
		rc, ok := intValue(row["rc"])
		if !ok {
			return 0, "", false
		}
		output, _ := row["output"].(string)
		return rc, output, true
	}
	if rc, _, ok := get("fetch"); !ok || rc != 0 {
		unconfirmed = append(unconfirmed, "repo: 원격 (fetch 결과 없음 또는 실패 — 아래 차이는 마지막 fetch 기준)")
	} else {
		confirmed = append(confirmed, "repo: fetch")
	}
	if rc, output, ok := get("status"); !ok || rc != 0 {
		unconfirmed = append(unconfirmed, "repo: 브랜치 · 변경 (status 결과 없음)")
		verdict = "unconfirmed"
	} else {
		lines := strings.Split(output, "\n")
		ahead, behind, hasAB, hasUpstream := 0, 0, false, false
		dirty := []string{}
		for _, line := range lines {
			trimmed := strings.TrimSpace(line)
			if match := branchAheadBehind.FindStringSubmatch(trimmed); match != nil {
				ahead, _ = strconv.Atoi(match[1])
				behind, _ = strconv.Atoi(match[2])
				hasAB = true
			}
			if strings.HasPrefix(line, "# branch.upstream ") {
				hasUpstream = true
			}
			if trimmed != "" && !strings.HasPrefix(line, "#") {
				dirty = append(dirty, line)
			}
		}
		confirmed = append(confirmed, "repo: 브랜치 · 변경")
		if len(dirty) > 0 {
			verdict = "stop_and_ask"
			findings = append(findings, fmt.Sprintf("커밋 안 된 변경 %d건 — 멈추고 묻는다", len(dirty)))
		}
		if !hasUpstream || !hasAB {
			unconfirmed = append(unconfirmed, "repo: 원격 추적 브랜치 없음 — 뒤처짐 · 앞섬을 잴 수 없다")
			if verdict == "start" {
				verdict = "unconfirmed"
			}
		} else if ahead > 0 && behind > 0 {
			verdict = "stop_and_ask"
			findings = append(findings, fmt.Sprintf("갈라짐 (앞섬 %d · 뒤처짐 %d) — 멈추고 묻는다", ahead, behind))
		} else if behind > 0 && verdict == "start" {
			verdict = "fast_forward_then_start"
			findings = append(findings, fmt.Sprintf("뒤처짐 %d — fast-forward 뒤 시작", behind))
		} else if ahead > 0 {
			findings = append(findings, fmt.Sprintf("앞섬 %d — push 전 커밋이 있다", ahead))
		}
	}
	if rc, output, ok := get("check_ignore"); !ok {
		unconfirmed = append(unconfirmed, "repo: .gitignore 규칙")
	} else if ok, why := checkIgnoreOK(rc, output); ok {
		confirmed = append(confirmed, "repo: .gitignore 규칙")
	} else {
		findings = append(findings, ".gitignore 규칙이 듣지 않는다 — "+why)
	}
	seen := []*string{}
	for _, path := range entries {
		_, output, ok := get("entry_head:" + path)
		if !ok {
			unconfirmed = append(unconfirmed, "repo: "+path+" 지침 판")
			continue
		}
		match := entryGuide.FindStringSubmatch(output + "\n")
		var got *string
		if match != nil {
			value := match[1]
			got = &value
		}
		seen = append(seen, got)
		confirmed = append(confirmed, "repo: "+path+" 지침 판")
		current := hub["guide"].(map[string]any)["current"].(string)
		if got == nil || *got != current {
			actual := "<없음>"
			if got != nil {
				actual = *got
			}
			findings = append(findings, fmt.Sprintf("[바뀜] %s 의 지침 판 %s ≠ 허브 %s — hub_guide_render", path, actual, current))
		}
	}
	if len(entries) > 0 && len(seen) == len(entries) {
		unique := map[string]bool{}
		for _, v := range seen {
			if v != nil {
				unique[*v] = true
			}
		}
		if len(unique) == 1 {
			var value string
			for v := range unique {
				value = v
			}
			guide := hub["guide"].(map[string]any)
			if value != guide["seen"] {
				if _, err := s.DB().Exec("UPDATE callsign SET guide_version_seen=? WHERE project_id=? AND id=?", value, ctx.Principal.ProjectID, ctx.Principal.Callsign); err != nil {
					return nil, err
				}
			}
			guide["seen"] = value
			guide["changed"] = value != guide["current"]
			if !guide["changed"].(bool) {
				delete(guide, "notice")
			}
		}
	}
	for sha, tasks := range commits {
		rc, _, ok := get("commit:" + sha)
		short := sha
		if len(short) > 12 {
			short = short[:12]
		}
		if !ok {
			unconfirmed = append(unconfirmed, "repo: 커밋 "+short)
		} else if rc != 0 {
			findings = append(findings, fmt.Sprintf("task %s 에 묶인 커밋 %s 이 이 저장소에 없다 (push 전 · 다른 원격)", strings.Join(tasks, ", "), short))
		} else {
			confirmed = append(confirmed, "repo: 커밋 "+short)
		}
	}
	return map[string]any{"phase": 2, "hub": hub, "verdict": verdict, "findings": findings, "confirmed": confirmed, "unconfirmed": unconfirmed}, nil
}

func intValue(v any) (int, bool) {
	switch n := v.(type) {
	case int:
		return n, true
	case int64:
		return int(n), true
	case float64:
		if n == float64(int(n)) {
			return int(n), true
		}
	}
	return 0, false
}

func checkIgnoreOK(rc int, output string) (bool, string) {
	if rc != 0 {
		return false, "무시되지 않는다 (rc != 0 — 규칙이 없거나 이미 추적 중인 파일)"
	}
	lines := strings.Split(strings.TrimSpace(output), "\n")
	if len(lines) == 0 || lines[0] == "" {
		return false, "출력이 없다"
	}
	head := strings.SplitN(lines[0], "\t", 2)[0]
	parts := strings.SplitN(head, ":", 3)
	pattern := head
	if len(parts) == 3 {
		pattern = parts[2]
	}
	if strings.HasPrefix(pattern, "!") {
		return false, "부정 규칙에 걸렸다: " + pattern
	}
	if !strings.Contains(lines[0], ".workflow-hub/env") {
		return false, "다른 경로의 결과다: " + lines[0]
	}
	return true, ""
}

// keep the stdlib JSON implementation behind one small helper for direct session data decoding.
func jsonUnmarshal(raw string, out any) error { return json.Unmarshal([]byte(raw), out) }
