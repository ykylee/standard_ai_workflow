package tools

import (
	"bytes"
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"regexp"
	"sort"
	"strings"

	"github.com/ykylee/standard_ai_workflow/hub-go/internal/db"
	"github.com/ykylee/standard_ai_workflow/hub-go/internal/judge"
	"github.com/ykylee/standard_ai_workflow/hub-go/internal/store"
)

// 1.x 전환 — 감지 · 계획 · 들여오기 · 표식. Python hub/migrate1x.py 와 같은 계약 (hub_spec §6.6).
// 허브는 저장소를 읽거나 쓰지 않는다. 에이전트가 명령 결과와 파일 내용을 보낸다.

const (
	migActive   = "ai-workflow/memory/active/"
	migArchived = "ai-workflow/memory/archived/"
	migPurpose  = migActive + "PURPOSE.md"
	migWikiRoot = "ai-workflow/wiki/"
	migHandoff  = "session_handoff.md"
)

var (
	migProfiles   = []string{"docs/PROJECT_PROFILE.md", migActive + "PROJECT_PROFILE.md"}
	migEntryFiles = []string{"CLAUDE.md", "AGENTS.md", "MiniMax.md", "ANTIGRAVITY.md", "GEMINI.md"}
	migEntryOwner = map[string]string{"CLAUDE.md": "claude-code", "AGENTS.md": "codex", "MiniMax.md": "minimax-code", "ANTIGRAVITY.md": "antigravity", "GEMINI.md": "antigravity"}
	migTraces     = [][2]string{
		{".claude-plugin/", "claude-code"}, {".claude/", "claude-code"}, {".mcp.json", "claude-code"},
		{".codex/", "codex"}, {".minimax/", "minimax-code"}, {".agents/", "antigravity"},
		{".grok/", "grok-build"}, {".opencode/", "opencode"}, {"opencode.json", "opencode"}, {".pi/", "pi-dev"},
	}
	// 이 순서로 들인다 — 결정 응답의 자격은 그 task 의 계획으로 판정하므로 task 뒤다.
	migKinds = []string{"tasks", "archive", "handoff", "roadmap", "wiki", "memory_index", "checkpoint", "guide_draft", "plan_responses", "project_docs"}

	migTaskFile     = regexp.MustCompile(`^(.+?)/backlog/tasks/([^/]+)\.md$`)
	migArchiveFile  = regexp.MustCompile(`^(.+?)/(?:session_handoff\.md|lessons\.md|baselines\.md|sessions/.+\.md|backlog/\d{4}-\d{2}-\d{2}\.md|\.archived\.json)$`)
	migResponseFile = regexp.MustCompile(`^(.+?)/plan_responses/([^/]+\.md)$`)
	migResponseName = regexp.MustCompile(`^((?:TASK|WF)-[A-Za-z0-9._-]+)-[0-9]+\.md$`)
	migKitMarker    = regexp.MustCompile(`standard-ai-workflow-kit:\s*v?([0-9][0-9A-Za-z.+-]*)`)

	migLeft = []struct {
		re  *regexp.Regexp
		why string
	}{
		{regexp.MustCompile(`(^|/)state\.json(\.template)?$|/roadmap_state\.json$`), "생성물 — 허브가 다시 만든다"},
		{regexp.MustCompile(`/plan_responses/inbox/`), "받은편지함 — 아직 반영 안 된 응답 (1.x 에서 plan-import 한 뒤 다시 전환한다)"},
		{regexp.MustCompile(`(^|/)\.gitkeep$|(^|/)\.frozen$|\.bak$`), "자리 표시 · 백업 파일"},
		{regexp.MustCompile(`^ai-workflow/memory/active/PROJECT_PROFILE\.md$`), "프로젝트 프로필 사본 — docs/PROJECT_PROFILE.md 를 들였다"},
		{regexp.MustCompile(`^ai-workflow/memory/(archive|release|plans)/|^ai-workflow/memory/log\.md$`), "옛 스냅숏 · 발행 기록 — 저장소에 남는다"},
		{regexp.MustCompile(`^ai-workflow/wiki/`), "위키의 페이지가 아닌 파일"},
		{regexp.MustCompile(`^ai-workflow/memory/active/memory_index/`), "memory_index 의 entry 가 아닌 파일"},
	}
)

const migRevertWarning = "허브 쪽 기록(task · handoff · 위키 …)은 지우지 않는다 — 되돌림에 데이터 이동은 없다 (R14.7). 되돌린 뒤 1.x 에서 " +
	"바뀐 것은 다시 전환해도 '이미 있음' 으로 건너뛴다 — 다시 전환하기 전에 허브 쪽 기록을 어떻게 할지 정한다."

func migrateCommands() map[string]any {
	seen, traces := map[string]bool{}, []string{}
	for _, t := range migTraces {
		if p := strings.TrimRight(t[0], "/"); !seen[p] {
			seen[p] = true
			traces = append(traces, p)
		}
	}
	sort.Strings(traces)
	join := func(head []string, tails ...[]string) []string {
		out := append([]string{}, head...)
		for _, t := range tails {
			out = append(out, t...)
		}
		return out
	}
	return map[string]any{
		"branch":     []string{"git", "rev-parse", "--abbrev-ref", "HEAD"},
		"default":    []string{"git", "rev-parse", "--abbrev-ref", "origin/HEAD"},
		"head":       []string{"git", "rev-parse", "HEAD"},
		"ls_tracked": join([]string{"git", "ls-files", "--", "ai-workflow", "docs/PROJECT_PROFILE.md"}, migEntryFiles, traces),
		"ls_ignored": []string{"git", "ls-files", "--others", "--ignored", "--exclude-standard", "--", "ai-workflow/memory/active"},
		"times":      []string{"git", "log", "--format=@%ct %H", "--name-only", "--", "ai-workflow/memory/active", "ai-workflow/memory/archived"},
		"kit_marker": join([]string{"git", "grep", "-n", "-e", "standard-ai-workflow-kit:", "--"}, migEntryFiles),
		"dirty":      join([]string{"git", "status", "--porcelain", "--untracked-files=all", "--", "ai-workflow"}, migEntryFiles),
	}
}

var migCommandOrder = []string{"branch", "default", "head", "ls_tracked", "ls_ignored", "times", "kit_marker", "dirty"}

func migOwner(ctx store.Ctx) (*store.Principal, error) {
	p := ctx.Principal
	if p == nil || p.Kind != "callsign" || p.Role != "owner" || p.CallsignKind != "human" || !p.HumanApproved {
		return nil, store.Forbidden("1.x 전환은 프로젝트 소유자(승인된 human)가 한다 (R14.2 — 등록자가 확인한 것만 들인다)")
	}
	return p, nil
}

func migNamespace(path string) (string, bool) {
	archived := strings.HasPrefix(path, migArchived)
	rest := strings.TrimPrefix(path, migActive)
	if archived {
		rest = path[len(migArchived):]
	}
	for _, re := range []*regexp.Regexp{migTaskFile, migArchiveFile, migResponseFile} {
		if m := re.FindStringSubmatch(rest); m != nil {
			return m[1], archived
		}
	}
	if i := strings.LastIndexByte(rest, '/'); i >= 0 {
		return rest[:i], archived
	}
	return rest, archived
}

// plainJSON turns nested Go values into the generic JSON shape stored and scanned elsewhere.
func plainJSON(v any) (map[string]any, error) {
	raw, err := store.EncodeJSON(v)
	if err != nil {
		return nil, err
	}
	decoded, err := DecodeJSONValue([]byte(raw))
	if err != nil {
		return nil, err
	}
	out, _ := decoded.(map[string]any)
	return out, nil
}

func sortedSet(m map[string]bool) []string {
	out := make([]string, 0, len(m))
	for k := range m {
		out = append(out, k)
	}
	sort.Strings(out)
	return out
}

type migCandidate struct {
	Namespace   string `json:"namespace"`
	Archived    bool   `json:"archived"`
	Path        string `json:"path"`
	CommittedAt int    `json:"committed_at"`
	Commit      string `json:"commit"`
	Reason      string `json:"reason,omitempty"`
}

func migratePlan(s *store.Store, ctx store.Ctx, rawScan any) (map[string]any, error) {
	p, err := store.NeedCallsign(ctx) // 계획은 기록만 남긴다 — 들여오기는 소유자이거나 승인이 있어야 한다
	if err != nil {
		return nil, err
	}
	if rawScan == nil {
		return map[string]any{"phase": 1, "commands": migrateCommands(),
			"rules": []string{"저장소 뿌리에서 그대로 돌리고 {name: {rc, output}} 로 scan 에 싣는다",
				"명령을 고치거나 건너뛰지 않는다 — 못 돌린 명령은 싣지 않는다 (미확인으로 남는다)"},
			"next": "hub_migrate_plan(scan=…)"}, nil
	}
	scan, ok := rawScan.(map[string]any)
	if !ok {
		return nil, store.InvalidField("scan", "{name: {rc, output}}")
	}
	commands := migrateCommands()
	unknown := map[string]bool{}
	for k := range scan {
		if _, ok := commands[k]; !ok {
			unknown[k] = true
		}
	}
	if len(unknown) > 0 {
		return nil, store.InvalidField("scan", "요청하지 않은 명령 결과: "+strings.Join(sortedSet(unknown), ", "))
	}
	rcs, outputs, unmeasured := map[string]int{}, map[string]string{}, []string{}
	for _, name := range migCommandOrder {
		m, ok := scan[name].(map[string]any)
		raw, has := m["rc"]
		if !ok || !has {
			unmeasured = append(unmeasured, name)
			continue
		}
		rc, err := confirmRC(raw, true)
		if err != nil {
			return nil, store.InvalidField("scan."+name+".rc", "정수")
		}
		rcs[name] = rc
		outputs[name], _ = m["output"].(string)
	}
	if rc, ok := rcs["ls_tracked"]; !ok || rc != 0 {
		return nil, store.InvalidField("scan.ls_tracked", "git ls-files 결과가 필요하다 (rc 0)")
	}
	lines := func(name string) []string {
		out := []string{}
		for _, line := range judge.SplitLines(outputs[name]) {
			if line = judge.Strip(line); line != "" {
				out = append(out, line)
			}
		}
		return out
	}
	tracked := lines("ls_tracked")
	has := map[string]bool{}
	for _, path := range tracked {
		has[path] = true
	}
	times := parseTimes(outputs["times"])
	branch, head := judge.Strip(outputs["branch"]), judge.Strip(outputs["head"])
	def := strings.TrimPrefix(judge.Strip(outputs["default"]), "origin/")
	kit := map[string]bool{}
	for _, m := range migKitMarker.FindAllStringSubmatch(outputs["kit_marker"], -1) {
		kit[m[1]] = true
	}

	tasks := map[string][]migCandidate{}
	archive, roadmap, wiki, memidx, entries, responses := []string{}, []string{}, []string{}, []string{}, []string{}, []string{}
	traces := []map[string]string{}
	namespaces, archivedNS := map[string]bool{}, map[string]bool{}
	isEntry := func(path string) bool { _, ok := migEntryOwner[path]; return ok }
	for _, path := range tracked {
		isArchived := strings.HasPrefix(path, migArchived)
		switch {
		case isArchived || strings.HasPrefix(path, migActive):
			rest := strings.TrimPrefix(path, migActive)
			nsSet := namespaces
			if isArchived {
				rest, nsSet = path[len(migArchived):], archivedNS
			}
			if !isArchived {
				if strings.HasPrefix(rest, "roadmap/") && strings.HasSuffix(rest, ".md") && strings.Count(rest, "/") == 1 {
					roadmap = append(roadmap, path)
					continue
				}
				if strings.HasPrefix(rest, "memory_index/entries/") && strings.HasSuffix(rest, ".json") {
					memidx = append(memidx, path)
					continue
				}
				if strings.HasPrefix(rest, "roadmap/") || strings.HasPrefix(rest, "memory_index/") {
					continue
				}
			}
			if m := migTaskFile.FindStringSubmatch(rest); m != nil && strings.HasPrefix(m[2], "TASK-") {
				nsSet[m[1]] = true
				ct := times[path]
				tasks[m[2]] = append(tasks[m[2]], migCandidate{Namespace: m[1], Archived: isArchived, Path: path, CommittedAt: ct.at, Commit: ct.sha})
			} else if m := migArchiveFile.FindStringSubmatch(rest); m != nil {
				nsSet[m[1]] = true
				archive = append(archive, path)
			} else if migResponseFile.MatchString(rest) {
				responses = append(responses, path)
			}
		case strings.HasPrefix(path, migWikiRoot) && strings.HasSuffix(path, ".md"):
			wiki = append(wiki, path)
		case isEntry(path):
			entries = append(entries, path)
		default:
			for _, t := range migTraces {
				if strings.HasPrefix(path, t[0]) {
					traces = append(traces, map[string]string{"path": path, "harness": t[1]})
					break
				}
			}
		}
	}
	docs := []string{}
	if has[migPurpose] {
		docs = append(docs, migPurpose)
	}
	for _, path := range migProfiles {
		if has[path] {
			docs = append(docs, path)
			break
		}
	}
	taskPaths := []string{}
	for _, cands := range tasks {
		for _, c := range cands {
			taskPaths = append(taskPaths, c.Path)
		}
	}
	for _, list := range [][]string{taskPaths, archive, roadmap, wiki, memidx, entries, responses} {
		sort.Strings(list)
	}
	covered := map[string]bool{}
	for _, list := range [][]string{taskPaths, archive, roadmap, wiki, memidx, entries, responses, docs} {
		for _, path := range list {
			covered[path] = true
		}
	}
	left, leftTotal := map[string][]string{}, 0
	for _, path := range tracked {
		if covered[path] || !strings.HasPrefix(path, "ai-workflow/") || strings.HasSuffix(path, "/session_handoff.md") || strings.HasSuffix(path, ".compact/checkpoint.json") {
			continue
		}
		why := "이 전환이 다루지 않는다 — 저장소에 남는다"
		for _, r := range migLeft {
			if r.re.MatchString(path) {
				why = r.why
				break
			}
		}
		left[why] = append(left[why], path)
		leftTotal++
	}
	leftOut := map[string]any{}
	for why, paths := range left {
		leftOut[why] = map[string]any{"files": len(paths), "sample": paths[:min(3, len(paths))]}
	}
	dirty := []string{}
	for _, line := range judge.SplitLines(outputs["dirty"]) {
		if len(line) > 3 {
			dirty = append(dirty, judge.Strip(line[3:]))
		}
	}
	currentNS := ""
	if namespaces[branch] {
		currentNS = branch
	} else if namespaces[def] {
		currentNS = def
	}
	checkpoint, handoff := []string{}, []string{}
	if currentNS != "" {
		path := migActive + currentNS + "/.compact/checkpoint.json"
		found := has[path]
		for _, ignored := range lines("ls_ignored") {
			found = found || ignored == path
		}
		if found {
			checkpoint = append(checkpoint, path)
		}
		if path := migActive + currentNS + "/" + migHandoff; has[path] {
			handoff = append(handoff, path)
		}
	}

	canonical := map[string]string{}
	conflicts := []map[string]any{}
	ids := make([]string, 0, len(tasks))
	for id := range tasks {
		ids = append(ids, id)
	}
	sort.Strings(ids)
	for _, id := range ids {
		ranked := append([]migCandidate{}, tasks[id]...)
		notDefault := func(c migCandidate) bool { return c.Archived || c.Namespace != def }
		sort.SliceStable(ranked, func(i, j int) bool {
			a, b := ranked[i], ranked[j]
			if a.CommittedAt != b.CommittedAt {
				return a.CommittedAt > b.CommittedAt
			}
			if notDefault(a) != notDefault(b) {
				return !notDefault(a)
			}
			if a.Archived != b.Archived {
				return !a.Archived
			}
			return a.Namespace < b.Namespace
		})
		win := ranked[0]
		canonical[id] = win.Path
		if len(ranked) == 1 {
			continue
		}
		second := ranked[1]
		switch {
		case win.CommittedAt > second.CommittedAt:
			win.Reason = "마지막 커밋 시각이 가장 늦다"
		case !notDefault(win):
			win.Reason = "커밋 시각이 같아 기본 브랜치"
		case !win.Archived && second.Archived:
			win.Reason = "커밋 시각이 같아 활성 브랜치 (아카이브보다 앞)"
		default:
			win.Reason = "커밋 시각이 같고 기본 브랜치가 없어 이름순"
		}
		conflicts = append(conflicts, map[string]any{"task_id": id, "canonical": win, "variants": ranked[1:]})
	}
	harnesses := map[string]bool{}
	byHarness := map[string][]string{}
	for _, t := range traces {
		harnesses[t["harness"]] = true
		if _, ok := guideEntries[t["harness"]]; ok {
			byHarness[t["harness"]] = append(byHarness[t["harness"]], t["path"])
		}
	}
	for _, e := range entries {
		harnesses[migEntryOwner[e]] = true
	}
	unsupported := []string{}
	for _, h := range sortedSet(harnesses) {
		if _, ok := guideEntries[h]; !ok {
			unsupported = append(unsupported, h)
		}
	}
	files := map[string][]string{"tasks": taskPaths, "archive": archive, "handoff": handoff, "roadmap": roadmap, "wiki": wiki,
		"memory_index": memidx, "checkpoint": checkpoint, "guide_draft": entries, "plan_responses": responses, "project_docs": docs}
	counts := map[string]any{}
	table := []map[string]any{}
	for _, k := range migKinds {
		counts[k] = len(files[k])
		table = append(table, map[string]any{"kind": k, "files": len(files[k]), "default": true})
	}
	planTimes := map[string]any{}
	for _, list := range [][]string{taskPaths, archive} {
		for _, path := range list {
			if ct, ok := times[path]; ok {
				planTimes[path] = []any{ct.at, ct.sha}
			}
		}
	}
	guidance := []string{}
	if len(dirty) > 0 {
		guidance = append(guidance, fmt.Sprintf("커밋 안 된 파일 %d개는 계획에 없다 — 커밋한 뒤 계획을 다시 낸다: %s", len(dirty), strings.Join(dirty[:min(5, len(dirty))], ", ")))
	}
	for _, h := range unsupported {
		guidance = append(guidance, h+": 2.0 지원 대상 아님 — 1.x 줄에 남거나 원격 MCP 를 손으로 등록한다 (R14.9)")
	}
	hs := []string{}
	for h := range byHarness {
		hs = append(hs, h)
	}
	sort.Strings(hs)
	for _, h := range hs {
		paths, more := byHarness[h], ""
		if len(paths) > 4 {
			more = " …"
		}
		guidance = append(guidance, fmt.Sprintf("%s: 설정 흔적 %d개 (%s%s) — 이 가운데 kit 가 만든 "+
			"플러그인 · hook · stdio MCP 서버(workflow_kit.server…)만 허브 MCP 로 바꾼 뒤 지운다. 프로젝트가 직접 만든 "+
			"에이전트 · hook 과 허브 항목(workflow-hub)은 남긴다. 지우는 것은 소유자 확인 뒤 (I4)", h, len(paths), strings.Join(paths[:min(4, len(paths))], ", "), more))
	}
	plan, err := plainJSON(map[string]any{
		"detected": map[string]any{
			"namespaces": sortedSet(namespaces), "archived_namespaces": sortedSet(archivedNS), "current_namespace": currentNS,
			"branch": branch, "default_branch": def, "head": head, "kit_versions": sortedSet(kit), "counts": counts, "task_ids": len(tasks),
			"entry_files": entries, "harness_traces": traces, "unsupported_harnesses": unsupported, "unmeasured": unmeasured,
			"left_in_repo": leftOut, "left_in_repo_total": leftTotal, "uncommitted": dirty,
		},
		"files": files, "conflicts": conflicts, "canonical": canonical, "times": planTimes, "guidance": guidance,
	})
	if err != nil {
		return nil, err
	}
	if err := store.ScanSecrets(plan, "plan"); err != nil {
		return nil, err
	}
	encoded, err := store.EncodeJSON(plan)
	if err != nil {
		return nil, err
	}
	mig := ""
	_, err = s.WriteTx(func(tx *sql.Tx) (map[string]any, error) {
		var n int
		if err := tx.QueryRow("SELECT COUNT(*) FROM migration_1x WHERE project_id=?", p.ProjectID).Scan(&n); err != nil {
			return nil, err
		}
		mig = fmt.Sprintf("MIG-%04d", n+1)
		if _, err := tx.Exec("INSERT INTO migration_1x (project_id,id,at,callsign,status,plan_json) VALUES (?,?,?,?,'planned',?)", p.ProjectID, mig, db.FormatISO(ctx.Now), p.Callsign, encoded); err != nil {
			return nil, err
		}
		return nil, s.RecordEvent(tx, ctx, &p.ProjectID, "migration_1x", mig, "plan", nil, counts, nil)
	})
	if err != nil {
		return nil, err
	}
	out := map[string]any{"phase": 2, "migration_id": mig, "table": table,
		"next": "고를 종류(kinds)를 소유자에게 확인한 뒤 hub_migrate_import(migration_id, kinds, files=[{path, content}]) — " +
			"요청 상한(256KB) 안으로 나눠 보내고 마지막에 final=true. 원본 파일은 지우지 않는다"}
	for k, v := range plan {
		out[k] = v
	}
	return out, nil
}

type migRow struct {
	at, callsign, status string
	plan, report         map[string]any
}

func loadMigration(s *store.Store, pid, mig string) (migRow, error) {
	var r migRow
	var plan, report string
	err := s.DB().QueryRow("SELECT at,callsign,status,plan_json,report_json FROM migration_1x WHERE project_id=? AND id=?", pid, mig).Scan(&r.at, &r.callsign, &r.status, &plan, &report)
	if errors.Is(err, sql.ErrNoRows) {
		return r, store.NotFound("전환 계획이 없다: " + mig)
	}
	if err != nil {
		return r, err
	}
	for _, pair := range []struct {
		raw string
		out *map[string]any
	}{{plan, &r.plan}, {report, &r.report}} {
		v, err := DecodeJSONValue([]byte(pair.raw))
		if err != nil {
			return r, err
		}
		if *pair.out, _ = v.(map[string]any); *pair.out == nil {
			*pair.out = map[string]any{}
		}
	}
	return r, nil
}

func migrateReport(s *store.Store, ctx store.Ctx, mig string) (map[string]any, error) {
	p, err := store.NeedReader(ctx)
	if err != nil {
		return nil, err
	}
	r, err := loadMigration(s, p.ProjectID, mig)
	if err != nil {
		return nil, err
	}
	return map[string]any{"migration_id": mig, "status": r.status, "at": r.at, "callsign": r.callsign, "plan": r.plan, "report": r.report}, nil
}

type migImporter struct {
	s     *store.Store
	ctx   store.Ctx
	p     *store.Principal
	plan  map[string]any
	batch map[string]map[string][]any
}

func (m *migImporter) add(kind, key string, item any) {
	if m.batch[kind] == nil {
		m.batch[kind] = map[string][]any{}
	}
	m.batch[kind][key] = append(m.batch[kind][key], item)
}

func (m *migImporter) commitOf(path string) (int, string) {
	times, _ := m.plan["times"].(map[string]any)
	pair, _ := times[path].([]any)
	if len(pair) != 2 {
		return 0, ""
	}
	at, _ := pair[0].(int)
	sha, _ := pair[1].(string)
	return at, sha
}

func exists(tx *sql.Tx, query string, args ...any) (bool, error) {
	var one int
	err := tx.QueryRow(query, args...).Scan(&one)
	if errors.Is(err, sql.ErrNoRows) {
		return false, nil
	}
	return err == nil, err
}

func countGroups(in map[string]any) map[string]any {
	out := map[string]any{}
	for kind, raw := range in {
		groups, ok := raw.(map[string]any)
		if !ok {
			continue
		}
		c := map[string]any{}
		for key, items := range groups {
			list, _ := items.([]any)
			c[key] = len(list)
		}
		out[kind] = c
	}
	return out
}

func migrateImport(s *store.Store, ctx store.Ctx, args map[string]any) (map[string]any, error) {
	mig, approvalID := strArg(args, "migration_id", ""), strArg(args, "approval_id", "")
	kinds, ok := stringList(args["kinds"])
	known := map[string]bool{}
	for _, k := range migKinds {
		known[k] = true
	}
	bad := []string{}
	chosen := map[string]bool{}
	for _, k := range kinds {
		chosen[k] = true
		if !known[k] {
			bad = append(bad, k)
		}
	}
	if !ok || len(kinds) == 0 || len(bad) > 0 {
		return nil, store.InvalidField("kinds", fmt.Sprintf("%s 가운데 하나 이상 — 모르는 값: %v", strings.Join(migKinds, " · "), bad))
	}
	var p *store.Principal
	var err error
	if approvalID != "" {
		p, err = s.ApprovalAuthorize(ctx, approvalID, "migrate_import", map[string]any{"migration_id": mig, "kinds": sortedSet(chosen)})
	} else {
		p, err = migOwner(ctx)
	}
	if err != nil {
		return nil, err
	}
	row, err := loadMigration(s, p.ProjectID, mig)
	if err != nil {
		return nil, err
	}
	if row.status == "done" {
		return nil, &store.HubError{Status: 409, Code: "already_done", Message: mig + " 는 이미 끝난 전환이다"}
	}
	// 한 파일이 여러 종류에 속할 수 있다 — 현재 브랜치 handoff 는 보관 원문이자 콜사인 handoff 의 출처다.
	kindsOf := map[string][]string{}
	planFiles, _ := row.plan["files"].(map[string]any)
	for _, kind := range migKinds {
		list, _ := planFiles[kind].([]any)
		for _, raw := range list {
			path, _ := raw.(string)
			kindsOf[path] = append(kindsOf[path], kind)
		}
	}
	var rawFiles []any
	if v, has := args["files"]; has && v != nil {
		if rawFiles, ok = v.([]any); !ok {
			return nil, store.InvalidField("files", "[{path, content}]")
		}
	}
	byKind := map[string][][2]string{}
	for i, raw := range rawFiles {
		f, _ := raw.(map[string]any)
		path, okP := f["path"].(string)
		content, okC := f["content"].(string)
		if !okP || !okC {
			return nil, store.InvalidField(fmt.Sprintf("files[%d]", i), "{path, content}")
		}
		owners, found := kindsOf[path]
		if !found {
			return nil, store.InvalidField(fmt.Sprintf("files[%d].path", i), "전환 계획에 없는 경로: "+path)
		}
		used := false
		for _, kind := range owners {
			if chosen[kind] {
				used = true
				byKind[kind] = append(byKind[kind], [2]string{path, content})
			}
		}
		if !used {
			return nil, store.InvalidField(fmt.Sprintf("files[%d].path", i), "고르지 않은 종류("+strings.Join(owners, ", ")+")의 파일")
		}
	}
	m := &migImporter{s: s, ctx: ctx, p: p, plan: row.plan, batch: map[string]map[string][]any{}}
	handlers := map[string]func(path, content string) error{
		"tasks": m.task, "archive": m.archive, "handoff": m.handoff, "roadmap": m.roadmap, "memory_index": m.memoryIndex,
		"checkpoint": m.checkpoint, "guide_draft": m.guideDraft, "plan_responses": m.planResponse, "project_docs": m.projectDoc,
	}
	fail := func(kind, path string, err error) error {
		he, ok := store.AsHubError(err)
		if !ok {
			return err
		}
		m.add(kind, "failed", map[string]any{"path": path, "error_code": he.Code, "message": he.Message})
		return nil
	}
	for _, kind := range migKinds {
		if kind == "wiki" {
			if len(byKind[kind]) == 0 {
				continue
			}
			if err := m.wiki(byKind[kind]); err != nil {
				for _, f := range byKind[kind] {
					if err := fail(kind, f[0], err); err != nil {
						return nil, err
					}
				}
			}
			continue
		}
		for _, f := range byKind[kind] {
			if err := handlers[kind](f[0], f[1]); err != nil {
				if err := fail(kind, f[0], err); err != nil {
					return nil, err
				}
			}
		}
	}
	batch, err := plainJSON(m.batch)
	if err != nil {
		return nil, err
	}
	report := row.report
	for kind, raw := range batch {
		merged, _ := report[kind].(map[string]any)
		if merged == nil {
			merged = map[string]any{}
		}
		for key, items := range raw.(map[string]any) {
			old, _ := merged[key].([]any)
			add, _ := items.([]any)
			merged[key] = append(old, add...)
		}
		report[kind] = merged
	}
	allKinds := map[string]bool{}
	prev, _ := report["kinds"].([]any)
	for _, k := range prev {
		if text, ok := k.(string); ok {
			allKinds[text] = true
		}
	}
	for k := range chosen {
		allKinds[k] = true
	}
	report["kinds"] = sortedSet(allKinds)
	final, _ := args["final"].(bool)
	status, next := "importing", "남은 파일을 이어 보내고 마지막에 final=true"
	if final {
		status, next = "done", "끝났다 — 원본은 그대로다. hub_migrate_marker(migration_id, action='issue') 로 '허브로 옮김' 표식을 남긴다"
		report["done_at"] = db.FormatISO(ctx.Now)
	}
	total := countGroups(report)
	encoded, err := store.EncodeJSON(report)
	if err != nil {
		return nil, err
	}
	return s.WriteTx(func(tx *sql.Tx) (map[string]any, error) {
		if _, err := tx.Exec("UPDATE migration_1x SET status=?,report_json=? WHERE project_id=? AND id=?", status, encoded, p.ProjectID, mig); err != nil {
			return nil, err
		}
		if final {
			var before any
			if approvalID != "" {
				before = map[string]any{"approval_id": approvalID}
				if err := store.ApprovalConsume(tx, ctx, p.ProjectID, approvalID); err != nil {
					return nil, err
				}
			}
			if err := s.RecordEvent(tx, ctx, &p.ProjectID, "migration_1x", mig, "done", before, total, nil); err != nil {
				return nil, err
			}
		}
		return map[string]any{"migration_id": mig, "status": status, "summary": countGroups(batch), "total": total, "next": next}, nil
	})
}

func (m *migImporter) task(path, content string) error {
	t, err := parseTaskFile(content)
	if err != nil {
		return err
	}
	if err := store.ScanSecrets(t.scan(), "task"); err != nil {
		return err
	}
	pid := m.p.ProjectID
	ns, archived := migNamespace(path)
	at, sha := m.commitOf(path)
	canon, _ := m.plan["canonical"].(map[string]any)
	winner, _ := canon[t.id].(string)
	var key string
	var item map[string]any
	_, err = m.s.WriteTx(func(tx *sql.Tx) (map[string]any, error) {
		if winner != path {
			seen, err := exists(tx, "SELECT 1 FROM event WHERE project_id=? AND target_kind='task' AND target_id=? AND op='imported_variant' AND json_extract(after_json,'$.path')=?", pid, t.id, path)
			if err != nil {
				return nil, err
			}
			if seen {
				key, item = "skipped_exists", map[string]any{"id": t.id, "path": path, "variant": true}
				return nil, nil
			}
			var canonValue any
			if winner != "" {
				canonValue = winner
			}
			key, item = "variants", map[string]any{"id": t.id, "path": path}
			return nil, m.s.RecordEvent(tx, m.ctx, &pid, "task", t.id, "imported_variant", nil, map[string]any{
				"namespace": ns, "archived": archived, "path": path, "commit": sha, "committed_at": at,
				"title": t.title, "status": t.status, "canonical": canonValue}, nil)
		}
		found, err := exists(tx, "SELECT 1 FROM task WHERE project_id=? AND id=?", pid, t.id)
		if err != nil {
			return nil, err
		}
		item = map[string]any{"id": t.id, "path": path}
		if found {
			key = "skipped_exists"
			return nil, nil
		}
		now := db.FormatISO(m.ctx.Now)
		created, branch := now, ns
		if migDate.MatchString(t.created) {
			created = t.created + "T00:00:00+00:00"
		}
		if archived {
			branch = "archived/" + ns
		}
		fields, err := store.EncodeJSON(t.fields)
		if err != nil {
			return nil, err
		}
		if _, err := tx.Exec("INSERT INTO task (project_id,id,title,status,priority,branch,wbs,wbs_exempt_reason,description,plan_md,fields_json,progress_note,created_by,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
			pid, t.id, t.title, t.status, t.priority, branch, t.wbs, t.exempt, t.description, t.planMD, fields, t.progress, m.p.Callsign, created, now); err != nil {
			return nil, err
		}
		key = "imported"
		return nil, m.s.RecordEvent(tx, m.ctx, &pid, "task", t.id, "import_1x", nil, map[string]any{
			"namespace": ns, "archived": archived, "path": path, "commit": sha, "committed_at": at}, nil)
	})
	if err == nil {
		m.add("tasks", key, item)
	}
	return err
}

func (m *migImporter) note(tx *sql.Tx, title, body string, meta map[string]any) error {
	_, err := tx.Exec("INSERT INTO memory_note (project_id,callsign,kind,title,body_md,meta_json,created_at) VALUES (?,?,'archive_1x',?,?,?,?)",
		m.p.ProjectID, m.p.Callsign, title, body, store.MustJSON(meta), db.FormatISO(m.ctx.Now))
	return err
}

func (m *migImporter) archive(path, content string) error {
	ns, archived := migNamespace(path)
	rel := strings.TrimPrefix(path, migActive)
	if archived {
		rel = path[len(migArchived):]
	}
	at, sha := m.commitOf(path)
	key := "imported"
	_, err := m.s.WriteTx(func(tx *sql.Tx) (map[string]any, error) {
		dup, err := exists(tx, "SELECT 1 FROM memory_note WHERE project_id=? AND kind='archive_1x' AND title=?", m.p.ProjectID, path)
		if err != nil {
			return nil, err
		}
		if dup {
			key = "skipped_exists"
			return nil, nil
		}
		return nil, m.note(tx, path, content, map[string]any{"branch": ns, "archived": archived, "path": path, "rel": rel,
			"commit": sha, "committed_at": at, "imported_at": db.FormatISO(m.ctx.Now)})
	})
	if err == nil {
		m.add("archive", key, path)
	}
	return err
}

func (m *migImporter) handoff(path, content string) error {
	sections, dropped := parseHandoffFile(content)
	current, err := m.s.HandoffGet(m.ctx, m.p.Callsign)
	if err != nil {
		return err
	}
	if current["version"].(int) > 0 {
		m.add("handoff", "skipped_exists", map[string]any{"callsign": m.p.Callsign, "path": path})
		return nil
	}
	zero := 0
	if _, err := m.s.HandoffPut(m.ctx, &zero, sections); err != nil {
		return err
	}
	m.add("handoff", "imported", map[string]any{"callsign": m.p.Callsign, "path": path, "dropped_lines": dropped})
	return nil
}

func (m *migImporter) roadmap(path, content string) error {
	name := path[strings.LastIndexByte(path, '/')+1:]
	jb := &JudgeBridge{Store: m.s}
	current, err := jb.RoadmapGet(m.ctx)
	if err != nil {
		return err
	}
	docs, _ := current["docs"].([]map[string]any)
	for _, d := range docs {
		if d["path"] == name {
			m.add("roadmap", "skipped_exists", name)
			return nil
		}
	}
	zero := 0
	if _, err := jb.RoadmapPut(m.ctx, name, &zero, content); err != nil {
		return err
	}
	m.add("roadmap", "imported", name)
	return nil
}

func (m *migImporter) wiki(items [][2]string) error {
	current, err := m.s.WikiList(m.ctx, "")
	if err != nil {
		return err
	}
	have := map[string]bool{}
	for _, page := range current["pages"].([]map[string]any) {
		have[page["path"].(string)] = true
	}
	send := []any{}
	skipped := []string{}
	for _, f := range items {
		rel := strings.TrimPrefix(f[0], migWikiRoot)
		if have[rel] {
			skipped = append(skipped, rel)
		} else {
			send = append(send, map[string]any{"path": rel, "content": f[1]})
		}
	}
	for _, rel := range skipped {
		m.add("wiki", "skipped_exists", rel)
	}
	if len(send) == 0 {
		return nil
	}
	out, err := m.s.WikiImportDir(m.ctx, send, "1.x 전환 — 위키 들여오기", false, "")
	if err != nil {
		return err
	}
	for _, page := range out["pages"].([]map[string]any) {
		m.add("wiki", "imported", page["path"])
	}
	for _, path := range out["archived_1x"].([]string) {
		m.add("wiki", "archived_1x", path)
	}
	return nil
}

func decodeObject(kind, content string) (any, error) {
	v, err := DecodeJSONValue([]byte(content))
	if err != nil {
		return nil, store.InvalidField(kind, "JSON 이 아니다: "+err.Error())
	}
	return v, nil
}

func (m *migImporter) memoryIndex(path, content string) error {
	v, err := decodeObject("memory_index", content)
	if err != nil {
		return err
	}
	entry, _ := v.(map[string]any)
	current, err := m.s.MemoryEntryList(m.ctx)
	if err != nil {
		return err
	}
	for _, e := range current["entries"].([]map[string]any) {
		if entry != nil && e["id"] == entry["id"] {
			m.add("memory_index", "skipped_exists", e["id"])
			return nil
		}
	}
	out, err := m.s.MemoryEntryPut(m.ctx, v, 0)
	if err != nil {
		return err
	}
	m.add("memory_index", "imported", out["id"])
	return nil
}

func (m *migImporter) checkpoint(path, content string) error {
	v, err := decodeObject("checkpoint", content)
	if err != nil {
		return err
	}
	body, ok := v.(map[string]any)
	if !ok {
		return store.InvalidField("checkpoint", "객체")
	}
	allowed := map[string]bool{"next": true, "unverified": true, "verified": true, "rejected": true, "tasks": true, "branch": true}
	keep, dropped := map[string]any{}, map[string]bool{}
	for k, item := range body {
		if allowed[k] {
			keep[k] = item
		} else {
			dropped[k] = true
		}
	}
	if _, err := m.s.CheckpointPut(m.ctx, keep); err != nil {
		return err
	}
	m.add("checkpoint", "imported", map[string]any{"path": path, "dropped_keys": sortedSet(dropped)})
	return nil
}

func (m *migImporter) guideDraft(path, content string) error {
	body, dropped := handWritten(content)
	if judge.Strip(body) == "" {
		m.add("guide_draft", "empty", map[string]any{"path": path, "dropped_sections": dropped})
		return nil
	}
	if err := store.ScanSecrets(body, "guide_draft"); err != nil {
		return err
	}
	pid, prop := m.p.ProjectID, ""
	_, err := m.s.WriteTx(func(tx *sql.Tx) (map[string]any, error) {
		var current, n int
		if err := tx.QueryRow("SELECT COALESCE(MAX(version),0) FROM guide WHERE project_id=?", pid).Scan(&current); err != nil {
			return nil, err
		}
		if err := tx.QueryRow("SELECT COUNT(*) FROM guide_proposal WHERE project_id=?", pid).Scan(&n); err != nil {
			return nil, err
		}
		prop = fmt.Sprintf("GP-%04d", n+1)
		if _, err := tx.Exec("INSERT INTO guide_proposal (project_id,id,base_version,body_md,note,proposed_by,proposed_at,status) VALUES (?,?,?,?,?,?,?,'open')",
			pid, prop, current, body, "1.x 전환 초안 — "+path+" 의 손 문단", m.p.Callsign, db.FormatISO(m.ctx.Now)); err != nil {
			return nil, err
		}
		return nil, m.s.RecordEvent(tx, m.ctx, &pid, "guide_proposal", prop, "propose", nil, map[string]any{"base_version": current, "source": path, "draft_1x": true}, nil)
	})
	if err == nil {
		m.add("guide_draft", "proposed", map[string]any{"path": path, "proposal_id": prop, "dropped_sections": dropped})
	}
	return err
}

func (m *migImporter) planResponse(path, content string) error {
	name := path[strings.LastIndexByte(path, '/')+1:]
	taskID := ""
	if match := migResponseName.FindStringSubmatch(name); match != nil {
		taskID = match[1]
	}
	parsed := judge.ParseResponse([]byte(content), name)
	pid := m.p.ProjectID
	var key string
	var item any
	_, err := m.s.WriteTx(func(tx *sql.Tx) (map[string]any, error) {
		dup, err := exists(tx, "SELECT 1 FROM plan_response WHERE project_id=? AND body_sha256=?", pid, parsed.ContentSHA256)
		if err != nil {
			return nil, err
		}
		if dup {
			key, item = "skipped_exists", path
			return nil, nil
		}
		why := "task 가 허브에 없다"
		var planMD, rawFields string
		err = sql.ErrNoRows
		if taskID != "" {
			err = tx.QueryRow("SELECT plan_md,fields_json FROM task WHERE project_id=? AND id=?", pid, taskID).Scan(&planMD, &rawFields)
		}
		if err != nil && !errors.Is(err, sql.ErrNoRows) {
			return nil, err
		}
		if err == nil {
			fields := map[string]any{}
			if rawFields != "" {
				if err := json.Unmarshal([]byte(rawFields), &fields); err != nil {
					return nil, err
				}
			}
			lines, _ := TaskLines(planMD, fields)
			verdict := judge.Qualify(parsed, judge.ParsePlan(lines), taskID)
			if verdict.Eligible() {
				if _, err := tx.Exec("INSERT INTO plan_response (project_id,task_id,body,body_sha256,received_at,responder) VALUES (?,?,?,?,?,?)",
					pid, taskID, content, parsed.ContentSHA256, parsed.ReceivedAt(), parsed.Responder()); err != nil {
					return nil, err
				}
				key, item = "imported", map[string]any{"task_id": taskID, "path": path}
				return nil, m.s.RecordEvent(tx, m.ctx, &pid, "task", taskID, "plan_response_1x", nil, map[string]any{
					"responder": parsed.Responder(), "sha256": parsed.ContentSHA256, "path": path}, nil)
			}
			why = fmt.Sprintf("자격 %d 단계: %s", *verdict.Stage, verdict.Reason)
		}
		ns, archived := migNamespace(path)
		key, item = "archived_ineligible", map[string]any{"path": path, "why": why}
		return nil, m.note(tx, path, content, map[string]any{"branch": ns, "archived": archived, "path": path, "kind": "plan_response",
			"not_applied": why, "imported_at": db.FormatISO(m.ctx.Now)})
	})
	if err == nil {
		m.add("plan_responses", key, item)
	}
	return err
}

func (m *migImporter) projectDoc(path, content string) error {
	name := "profile"
	if path == migPurpose {
		name = "purpose"
	}
	current, err := m.s.ProjectDocGet(m.ctx, name)
	if err != nil {
		return err
	}
	item := map[string]any{"name": name, "path": path}
	if current["version"].(int) > 0 {
		m.add("project_docs", "skipped_exists", item)
		return nil
	}
	if _, err := m.s.ProjectDocImport(m.ctx, name, content); err != nil {
		return err
	}
	m.add("project_docs", "imported", item)
	return nil
}

func markerContent(publicURL, pid, mig, at string, kits any) (string, error) {
	if kits == nil {
		kits = []any{}
	}
	var out bytes.Buffer
	enc := json.NewEncoder(&out)
	enc.SetEscapeHTML(false)
	enc.SetIndent("", "  ")
	err := enc.Encode(map[string]any{"format": hubMigrationMarkerFormat, "hub": publicURL, "project_id": pid, "migration_id": mig,
		"migrated_at": at, "kit_version": KitVersion, "from_kit_versions": kits,
		"note": "이 저장소의 워크플로우 정본은 허브다 — 1.x kit 의 쓰기 도구는 이 파일을 보면 거절한다. " +
			"1.x 로 되돌리려면 이 파일만 지운다 (허브 쪽 데이터는 옮기지 않는다)."})
	return out.String(), err
}

func migrateMarker(s *store.Store, ctx store.Ctx, args map[string]any) (map[string]any, error) {
	mig, action, approvalID := strArg(args, "migration_id", ""), strArg(args, "action", ""), strArg(args, "approval_id", "")
	switch action {
	case "issue", "confirm", "revert", "confirm_revert":
	default:
		return nil, store.InvalidField("action", "issue · confirm · revert · confirm_revert")
	}
	var p *store.Principal
	var err error
	if approvalID != "" {
		scope := "issue"
		if strings.HasSuffix(action, "revert") {
			scope = "revert"
		}
		p, err = s.ApprovalAuthorize(ctx, approvalID, "migrate_marker", map[string]any{"migration_id": mig, "marker": scope})
	} else {
		p, err = migOwner(ctx)
	}
	if err != nil {
		return nil, err
	}
	row, err := loadMigration(s, p.ProjectID, mig)
	if err != nil {
		return nil, err
	}
	if row.status != "done" {
		return nil, &store.HubError{Status: 409, Code: "migration_not_done", Message: mig + " 가 아직 끝나지 않았다 — 마지막 묶음을 final=true 로 보낸 뒤에 표식을 남긴다"}
	}
	doneAt, _ := row.report["done_at"].(string)
	if doneAt == "" {
		doneAt = row.at
	}
	detected, _ := row.plan["detected"].(map[string]any)
	content, err := markerContent(ctx.PublicURL, p.ProjectID, mig, doneAt, detected["kit_versions"])
	if err != nil {
		return nil, err
	}
	expected, now := digest(content), db.FormatISO(ctx.Now)
	state, _ := row.report["marker"].(map[string]any)
	if state == nil {
		state = map[string]any{}
	}
	out := map[string]any{"migration_id": mig, "action": action, "path": hubMigrationMarkerPath}
	logged := map[string]any{}
	switch action {
	case "issue":
		if issued, _ := state["issued_at"].(string); issued == "" {
			state["issued_at"] = now
		}
		state["sha256"] = expected
		out["steps"] = []any{
			map[string]any{"id": "marker", "op": "write", "path": hubMigrationMarkerPath, "content": content, "sha256_after": expected},
			map[string]any{"id": "commit", "op": "run", "run": []string{"git", "add", "--", hubMigrationMarkerPath},
				"then": []string{"git", "commit", "-m", "chore: 워크플로우 허브로 옮김 (" + mig + ")", "--", hubMigrationMarkerPath}},
		}
		out["next"] = "파일을 쓰고 커밋한 뒤 hub_migrate_marker(action='confirm', sha256=<쓴 파일의 sha256>)"
	case "confirm":
		sha := strArg(args, "sha256", "")
		if sha == "" {
			return nil, store.InvalidField("sha256", "쓴 파일의 sha256")
		}
		reason := ""
		if sha == expected {
			state["confirmed_at"], state["reverted_at"] = now, nil
		} else {
			reason = fmt.Sprintf("sha256 이 지시와 다르다 (지시 %s…, 받음 %s…)", short12(expected), short12(sha))
		}
		out["confirmed"], out["reason"] = sha == expected, reason
		logged["confirmed"], logged["reason"] = sha == expected, reason
	case "revert":
		state["revert_issued_at"] = now
		out["steps"] = []any{
			map[string]any{"id": "marker", "op": "delete", "path": hubMigrationMarkerPath},
			map[string]any{"id": "check", "op": "run_and_report", "run": []string{"git", "ls-files", "--", hubMigrationMarkerPath}, "expect": "empty"},
		}
		out["warning"] = migRevertWarning
		out["next"] = "파일을 지우고 커밋한 뒤 확인 명령의 결과를 hub_migrate_marker(action='confirm_revert', check={rc, output})"
	case "confirm_revert":
		check, _ := args["check"].(map[string]any)
		raw, has := check["rc"]
		if !has {
			return nil, store.InvalidField("check", "{rc, output} — git ls-files 결과")
		}
		rc, err := confirmRC(raw, true)
		if err != nil {
			return nil, err
		}
		output, _ := check["output"].(string)
		reverted, reason := rc == 0 && judge.Strip(output) == "", ""
		if reverted {
			state["reverted_at"], state["confirmed_at"] = now, nil
		} else {
			reason = "표식이 아직 추적된다 (지우고 커밋했는지 본다)"
		}
		out["reverted"], out["warning"], out["reason"] = reverted, migRevertWarning, reason
		logged["reverted"], logged["reason"] = reverted, reason
	}
	row.report["marker"], out["marker"] = state, state
	encoded, err := store.EncodeJSON(row.report)
	if err != nil {
		return nil, err
	}
	return s.WriteTx(func(tx *sql.Tx) (map[string]any, error) {
		if _, err := tx.Exec("UPDATE migration_1x SET report_json=? WHERE project_id=? AND id=?", encoded, p.ProjectID, mig); err != nil {
			return nil, err
		}
		if approvalID != "" && (out["confirmed"] == true || out["reverted"] == true) {
			if err := store.ApprovalConsume(tx, ctx, p.ProjectID, approvalID); err != nil {
				return nil, err
			}
		}
		return out, s.RecordEvent(tx, ctx, &p.ProjectID, "migration_1x", mig, "marker_"+action, nil, logged, nil)
	})
}
