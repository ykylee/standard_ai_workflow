package tools

import (
	"crypto/sha256"
	"database/sql"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"sort"
	"strings"

	"github.com/ykylee/standard_ai_workflow/hub-go/internal/assets"
	"github.com/ykylee/standard_ai_workflow/hub-go/internal/db"
	"github.com/ykylee/standard_ai_workflow/hub-go/internal/store"
)

var guideEntries = map[string]string{"claude-code": "CLAUDE.md", "codex": "AGENTS.md", "minimax-code": "MiniMax.md", "antigravity": "ANTIGRAVITY.md"}

const mcpHTTPJSONProfile = "mcp-http-json-v1"

const hubMigrationMarkerPath = "ai-workflow/HUB_MIGRATED.json"
const hubMigrationMarkerFormat = "workflow-hub-migrated/1"

var legacyEntryMarkers = []string{"standard-ai-workflow-kit:", "generated-from: core/global_workflow_standard.md", "workflow_kit.server."}

const legacyReadFirstLine = "- Restore the session with `python -m workflow_kit session-start` — it reads `ai-workflow/memory/active/<branch>/` (`state.json`, handoff, backlog), `docs/PROJECT_PROFILE.md`, and `PURPOSE.md` (`<branch>` = current git branch)."
const hubReadFirstLine = "- Start each session with the Workflow Hub MCP tool `hub_session_start`. The Hub is the source of task and handoff state; do not restore state from local 1.x paths."

func hasLegacyEntryMarker(text string) bool {
	for _, marker := range legacyEntryMarkers {
		if strings.Contains(text, marker) {
			return true
		}
	}
	return false
}

func migrationMarkerReady(files map[string]any, projectID, hubURL string) bool {
	raw, ok := files[hubMigrationMarkerPath].(string)
	if !ok {
		return false
	}
	var marker struct {
		Format    string `json:"format"`
		Hub       string `json:"hub"`
		ProjectID string `json:"project_id"`
	}
	if json.Unmarshal([]byte(raw), &marker) != nil {
		return false
	}
	return marker.Format == hubMigrationMarkerFormat && marker.ProjectID == projectID && strings.TrimRight(marker.Hub, "/") == strings.TrimRight(hubURL, "/")
}

func migrateLegacyStartGuidance(text string) (string, bool) {
	if !strings.Contains(text, legacyReadFirstLine) {
		return "", false
	}
	return strings.ReplaceAll(text, legacyReadFirstLine, hubReadFirstLine), true
}

func stringList(raw any) ([]string, bool) {
	switch values := raw.(type) {
	case []string:
		return values, true
	case []any:
		out := make([]string, 0, len(values))
		for _, value := range values {
			text, ok := value.(string)
			if !ok {
				return nil, false
			}
			out = append(out, text)
		}
		return out, true
	default:
		return nil, false
	}
}

func digest(text string) string {
	sum := sha256.Sum256([]byte(text))
	return hex.EncodeToString(sum[:])
}

func guideVersion(version int) string { return fmt.Sprintf("%s+p%d", KitVersion, version) }

func renderGuide(harness, projectID, display, body string, version int) (string, error) {
	entry, ok := guideEntries[harness]
	if !ok {
		return "", &store.HubError{Status: 400, Code: "unsupported_harness", Message: "지원하지 않는 하네스: " + harness,
			Detail: map[string]any{"supported": []string{"claude-code", "codex", "minimax-code", "antigravity"}}}
	}
	return renderGuideAtEntry(harness, entry, projectID, display, body, version)
}

func renderGuideAtEntry(harness, entry, projectID, display, body string, version int) (string, error) {
	if !store.IsSafeHarnessRelativePath(entry) {
		return "", store.InvalidField("entry_file", "안전한 상대 경로만 허용")
	}
	text := fmt.Sprintf("<!-- 이 영역은 워크플로우 허브가 렌더링한다 (%s · %s). 고칠 것은 허브에 지침 제안으로. -->\n%s", entry, harness, assets.StandardBlock)
	if strings.TrimSpace(body) != "" {
		text += fmt.Sprintf("\n## 프로젝트 지침 — %s\n\n%s\n", display, strings.TrimSpace(body))
	}
	region := fmt.Sprintf("<!-- workflow-hub:begin project=%s guide=%s sha256=%s -->\n%s<!-- workflow-hub:end -->\n", projectID, guideVersion(version), digest(text), text)
	if len([]byte(region)) > 8*1024 {
		return "", &store.HubError{Status: 422, Code: "entry_budget_exceeded", Message: fmt.Sprintf("%s 렌더 영역이 8192B 예산을 넘었다", entry),
			Detail: map[string]any{"size": len([]byte(region)), "budget": 8192}}
	}
	return region, nil
}

func mergeGuide(current, region string) (string, bool) {
	begin := strings.Index(current, "<!-- workflow-hub:begin project=")
	if begin < 0 {
		if strings.Contains(current, "workflow-hub:begin") {
			return "", false
		}
		sep := "\n\n"
		if current == "" || strings.HasSuffix(current, "\n\n") {
			sep = ""
		} else if strings.HasSuffix(current, "\n") {
			sep = "\n"
		}
		return current + sep + region, true
	}
	lineEnd := strings.Index(current[begin:], "\n")
	if lineEnd < 0 {
		return "", false
	}
	bodyStart := begin + lineEnd + 1
	endRel := strings.Index(current[bodyStart:], "<!-- workflow-hub:end -->")
	if endRel < 0 {
		return "", false
	}
	bodyEnd := bodyStart + endRel
	line := current[begin : begin+lineEnd]
	marker := "sha256="
	shaAt := strings.Index(line, marker)
	if shaAt < 0 {
		return "", false
	}
	want := strings.TrimSuffix(line[shaAt+len(marker):], " -->")
	if digest(current[bodyStart:bodyEnd]) != want {
		return "", false
	}
	end := bodyEnd + len("<!-- workflow-hub:end -->")
	if end < len(current) && current[end] == '\n' {
		end++
	}
	return current[:begin] + region + current[end:], true
}

func guideRender(s *store.Store, ctx store.Ctx, harness string, current *string) (map[string]any, error) {
	p, err := store.NeedCallsign(ctx)
	if err != nil {
		return nil, err
	}
	entry, builtin := guideEntries[harness]
	if !builtin {
		profile, err := s.HarnessSetupProfile(harness)
		if err != nil {
			return nil, err
		}
		if profile == nil {
			return map[string]any{"path": nil, "blocked": true, "reason": "setup_profile_required", "next": "hub_harness_report 제보 후 허브 관리자 승인을 기다린다"}, nil
		}
		entry, _ = profile["entry_file"].(string)
	}
	var display, body string
	var version int
	err = s.DB().QueryRow("SELECT display_name FROM project WHERE id=?", p.ProjectID).Scan(&display)
	if err != nil {
		return nil, err
	}
	_ = s.DB().QueryRow("SELECT version,body_md FROM guide WHERE project_id=? ORDER BY version DESC LIMIT 1", p.ProjectID).Scan(&version, &body)
	region, err := renderGuideAtEntry(harness, entry, p.ProjectID, display, body, version)
	if err != nil {
		return nil, err
	}
	old := ""
	if current != nil {
		old = *current
	}
	merged, ok := mergeGuide(old, region)
	gv := guideVersion(version)
	if !ok {
		return map[string]any{"path": entry, "guide_version": gv, "blocked": true, "reason": "local_edit_detected"}, nil
	}
	sha := digest(merged)
	_, err = s.DB().Exec("INSERT INTO setup_step(project_id,callsign,step_id,kind,path,sha256,guide_version,status,issued_at) VALUES(?,?,?,?,?,?,?,'issued',?) ON CONFLICT(project_id,callsign,step_id) DO UPDATE SET kind=excluded.kind,path=excluded.path,guide_version=excluded.guide_version,status=CASE WHEN setup_step.status='confirmed' AND setup_step.sha256=excluded.sha256 THEN 'confirmed' ELSE 'issued' END,confirmed_at=CASE WHEN setup_step.status='confirmed' AND setup_step.sha256=excluded.sha256 THEN setup_step.confirmed_at ELSE NULL END,sha256=excluded.sha256,detail='',issued_at=excluded.issued_at", p.ProjectID, p.Callsign, "entry:"+harness, "entry", entry, sha, gv, db.FormatISO(ctx.Now))
	if err != nil {
		return nil, err
	}
	return map[string]any{"path": entry, "guide_version": gv, "blocked": false, "step": map[string]any{"id": "entry:" + harness, "op": "write", "path": entry, "content": merged, "sha256_after": sha}}, nil
}

func guideGet(s *store.Store, ctx store.Ctx) (map[string]any, error) {
	p, err := store.NeedReader(ctx)
	if err != nil {
		return nil, err
	}
	pid := p.ProjectID
	version := 0
	body := ""
	_ = s.DB().QueryRow("SELECT version,body_md FROM guide WHERE project_id=? ORDER BY version DESC LIMIT 1", pid).Scan(&version, &body)
	history := []map[string]any{}
	rows, err := s.DB().Query("SELECT version,updated_by,updated_at,length(body_md) AS size FROM guide WHERE project_id=? ORDER BY version DESC", pid)
	if err != nil {
		return nil, err
	}
	for rows.Next() {
		var v, size int
		var by, at string
		if err := rows.Scan(&v, &by, &at, &size); err != nil {
			rows.Close()
			return nil, err
		}
		history = append(history, map[string]any{"version": v, "updated_by": by, "updated_at": at, "size": size})
	}
	if err := rows.Close(); err != nil {
		return nil, err
	}
	guideBodies := map[int]string{}
	rows, err = s.DB().Query("SELECT version,body_md FROM guide WHERE project_id=?", pid)
	if err != nil {
		return nil, err
	}
	for rows.Next() {
		var v int
		var text string
		if err := rows.Scan(&v, &text); err != nil {
			rows.Close()
			return nil, err
		}
		guideBodies[v] = text
	}
	if err := rows.Close(); err != nil {
		return nil, err
	}
	proposals := []map[string]any{}
	rows, err = s.DB().Query("SELECT id,base_version,body_md,note,proposed_by,proposed_at,status,decided_by,decided_at,applied_version FROM guide_proposal WHERE project_id=? ORDER BY proposed_at DESC,id DESC LIMIT 100", pid)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	for rows.Next() {
		var id, proposalBody, note, by, at, status string
		var base int
		var decidedBy, decidedAt sql.NullString
		var applied sql.NullInt64
		if err := rows.Scan(&id, &base, &proposalBody, &note, &by, &at, &status, &decidedBy, &decidedAt, &applied); err != nil {
			return nil, err
		}
		baseBody := guideBodies[base]
		proposals = append(proposals, map[string]any{"id": id, "base_version": base, "body_md": proposalBody, "note": note, "proposed_by": by, "proposed_at": at, "status": status, "decided_by": nullable(decidedBy), "decided_at": nullable(decidedAt), "applied_version": nullableInt(applied), "diff": unifiedDiff(baseBody, proposalBody, fmt.Sprintf("v%d", base), id), "stale": status == "open" && base != version})
	}
	if err := rows.Err(); err != nil {
		return nil, err
	}
	return map[string]any{"version": version, "guide_version": guideVersion(version), "body": body, "history": history, "proposals": proposals}, nil
}

func nullable(v sql.NullString) any {
	if !v.Valid {
		return nil
	}
	return v.String
}
func nullableInt(v sql.NullInt64) any {
	if !v.Valid {
		return nil
	}
	return v.Int64
}
func unifiedDiff(old, next, from, to string) string {
	if old == next {
		return ""
	}
	oldLines, nextLines := diffLines(old), diffLines(next)
	var b strings.Builder
	oldStart, nextStart := 1, 1
	if len(oldLines) == 0 {
		oldStart = 0
	}
	if len(nextLines) == 0 {
		nextStart = 0
	}
	fmt.Fprintf(&b, "--- %s\n+++ %s\n@@ -%d,%d +%d,%d @@\n", from, to, oldStart, len(oldLines), nextStart, len(nextLines))
	for _, line := range oldLines {
		b.WriteByte('-')
		b.WriteString(line)
		if !strings.HasSuffix(line, "\n") {
			b.WriteByte('\n')
		}
	}
	for _, line := range nextLines {
		b.WriteByte('+')
		b.WriteString(line)
		if !strings.HasSuffix(line, "\n") {
			b.WriteByte('\n')
		}
	}
	return b.String()
}

func diffLines(text string) []string {
	if text == "" {
		return nil
	}
	lines := strings.SplitAfter(text, "\n")
	if lines[len(lines)-1] == "" {
		lines = lines[:len(lines)-1]
	}
	return lines
}

func setupMCPJSON(existing, url string) (string, error) {
	return setupMCPJSONAtPath(existing, url, ".mcp.json")
}

func setupMCPJSONAtPath(existing, url, configPath string) (string, error) {
	data := map[string]any{}
	if strings.TrimSpace(existing) != "" {
		if err := json.Unmarshal([]byte(existing), &data); err != nil {
			return "", &store.HubError{Status: 409, Code: "invalid_existing_file", Message: configPath + " 이 JSON 이 아니다 — 손으로 고친 뒤 다시"}
		}
	}
	servers, ok := data["mcpServers"].(map[string]any)
	if !ok {
		if _, exists := data["mcpServers"]; exists {
			return "", &store.HubError{Status: 409, Code: "invalid_existing_file", Message: configPath + " 의 mcpServers 가 객체가 아니다"}
		}
		servers = map[string]any{}
		data["mcpServers"] = servers
	}
	servers["workflow-hub"] = map[string]any{"type": "http", "url": url, "headers": map[string]any{"Authorization": "Bearer ${WORKFLOW_HUB_TOKEN}"}}
	var output strings.Builder
	encoder := json.NewEncoder(&output)
	encoder.SetEscapeHTML(false)
	encoder.SetIndent("", "  ")
	err := encoder.Encode(data)
	if err != nil {
		return "", err
	}
	return output.String(), nil
}

func setupPlan(s *store.Store, ctx store.Ctx, args map[string]any) (map[string]any, error) {
	pid := strArg(args, "project_id", "")
	token := strArg(args, "token", "")
	p, err := s.Authenticate(token, &ctx.Now, "")
	if err != nil {
		return nil, err
	}
	if p == nil || p.Kind != "callsign" {
		return nil, store.Unauthorized("토큰이 없거나 틀렸거나 거둔 토큰이다")
	}
	if p.ProjectID != pid {
		return nil, store.Forbidden("이 토큰은 다른 프로젝트의 것이다")
	}
	harnesses, ok := stringList(args["harnesses"])
	if !ok || len(harnesses) == 0 {
		return nil, store.InvalidField("harnesses", "하나 이상 — claude-code · codex · minimax-code · antigravity")
	}
	setupProfiles := map[string]map[string]any{}
	entryPaths := map[string]string{}
	for _, h := range harnesses {
		if entry, builtin := guideEntries[h]; builtin {
			setupProfiles[h] = map[string]any{"kind": "builtin"}
			entryPaths[h] = entry
			continue
		}
		profile, err := s.HarnessSetupProfile(h)
		if err != nil {
			return nil, err
		}
		if profile == nil {
			return map[string]any{"stage": "harness_support", "steps": []any{}, "blocked": []any{map[string]any{
				"id": "harness:" + h, "reason": "setup_profile_required",
				"message":                h + " 는 셋업 프로필이 없다. hub_harness_report 로 지원 정보와 설정 후보를 제보하고 웹 허브 관리자 승인을 기다린다.",
				"report_tool":            "hub_harness_report",
				"required_report_fields": []string{"entry_file_candidates", "mcp_config_candidates", "config_formats: mcp-http-json-v1", "mcp_transports: streamable-http"},
			}}, "next": "hub_harness_report 제보 후 관리자 승인까지 프로젝트 파일을 수정하지 않는다"}, nil
		}
		setupProfiles[h] = profile
		entryPaths[h], _ = profile["entry_file"].(string)
	}
	scan, _ := args["scan"].(map[string]any)
	var unknownScan []string
	for key := range scan {
		if key != "files" && key != "relay" {
			unknownScan = append(unknownScan, key)
		}
	}
	if len(unknownScan) > 0 {
		sort.Strings(unknownScan)
		return nil, &store.HubError{Status: 400, Code: "unknown_field", Message: "scan 의 모르는 칸: " + strings.Join(unknownScan, ", "), Detail: map[string]any{"fields": unknownScan}}
	}
	files, _ := scan["files"].(map[string]any)
	if rawFiles, exists := scan["files"]; exists && rawFiles != nil {
		if _, ok := rawFiles.(map[string]any); !ok {
			return nil, store.InvalidField("scan.files", "경로 → 내용(없으면 null) 객체")
		}
	}
	migrationComplete := migrationMarkerReady(files, pid, ctx.PublicURL)
	var relayScan map[string]any
	if rawRelay, exists := scan["relay"]; exists && rawRelay != nil {
		var ok bool
		relayScan, ok = rawRelay.(map[string]any)
		if !ok {
			return nil, store.InvalidField("scan.relay", "{required, config_present, status} 객체")
		}
		for key := range relayScan {
			if key != "required" && key != "config_present" && key != "status" {
				return nil, store.InvalidField("scan.relay", "{required, config_present, status} 객체")
			}
		}
		if raw, ok := relayScan["required"]; ok {
			if _, ok := raw.(bool); !ok {
				return nil, store.InvalidField("scan.relay.required", "boolean")
			}
		}
	}
	var status sql.NullString
	_ = s.DB().QueryRow("SELECT status FROM setup_step WHERE project_id=? AND callsign=? AND step_id='gitignore'", pid, p.Callsign).Scan(&status)
	if !status.Valid || status.String != "confirmed" {
		_, err = s.DB().Exec("INSERT INTO setup_step(project_id,callsign,step_id,kind,path,status,issued_at) VALUES(?,?, 'gitignore','gitignore','.gitignore','issued',?) ON CONFLICT(project_id,callsign,step_id) DO UPDATE SET status='issued',issued_at=excluded.issued_at", pid, p.Callsign, db.FormatISO(ctx.Now))
		if err != nil {
			return nil, err
		}
		gi, _ := files[".gitignore"].(string)
		already := false
		for _, line := range strings.Split(gi, "\n") {
			if strings.TrimSpace(line) == "/.workflow-hub/" {
				already = true
			}
		}
		return map[string]any{"stage": "gitignore", "steps": []any{map[string]any{"id": "gitignore", "op": "append_line", "path": ".gitignore", "content": "/.workflow-hub/\n", "already_present": already}, map[string]any{"id": "check_ignore", "op": "run_and_report", "run": []string{"git", "check-ignore", "-v", ".workflow-hub/env"}, "note": "출력과 종료 코드를 hub_setup_confirm 의 checks 로 보낸다"}}, "next": "hub_setup_confirm — 이 단계가 확인되기 전에는 토큰 파일 지시를 내지 않는다 (요구 R4.2)", "legacy_1x": nil, "relay": map[string]any{"required": false, "config_present": false, "status": nil, "next": "선택 사항 — 현재 셋업에서는 로컬 중계가 필요하지 않음"}}, nil
	}
	publicURL := strings.TrimRight(ctx.PublicURL, "/")
	env := fmt.Sprintf("WORKFLOW_HUB_URL=%s\nWORKFLOW_HUB_PROJECT=%s\nWORKFLOW_HUB_CALLSIGN=%s\nWORKFLOW_HUB_TOKEN=%s\n", publicURL, pid, p.Callsign, token)
	steps := []any{}
	issue := func(id, kind, path, sha, gv string) error {
		_, e := s.DB().Exec("INSERT INTO setup_step(project_id,callsign,step_id,kind,path,sha256,guide_version,status,issued_at) VALUES(?,?,?,?,?,?,?,'issued',?) ON CONFLICT(project_id,callsign,step_id) DO UPDATE SET kind=excluded.kind,path=excluded.path,sha256=excluded.sha256,guide_version=excluded.guide_version,status=CASE WHEN setup_step.status='confirmed' AND setup_step.sha256=excluded.sha256 THEN 'confirmed' ELSE 'issued' END,confirmed_at=CASE WHEN setup_step.status='confirmed' AND setup_step.sha256=excluded.sha256 THEN setup_step.confirmed_at ELSE NULL END,detail='',issued_at=excluded.issued_at", pid, p.Callsign, id, kind, path, sha, gv, db.FormatISO(ctx.Now))
		return e
	}
	if err := issue("env", "env", ".workflow-hub/env", digest(env), ""); err != nil {
		return nil, err
	}
	steps = append(steps, map[string]any{"id": "env", "op": "write", "path": ".workflow-hub/env", "content": env, "mode": "600", "sha256_after": digest(env), "note": "POSIX 는 권한 600. Windows 는 사용자 프로필 ACL 을 따른다 — 적용 결과를 사실대로 보고 (요구 R4.3)"})
	var display, guideBody string
	_ = s.DB().QueryRow("SELECT display_name FROM project WHERE id=?", pid).Scan(&display)
	var guideVer int
	_ = s.DB().QueryRow("SELECT version,body_md FROM guide WHERE project_id=? ORDER BY version DESC LIMIT 1", pid).Scan(&guideVer, &guideBody)
	blocked := []any{}
	mcpJSONWritten := false
	dynamicConfigsWritten := map[string]bool{}
	for _, h := range harnesses {
		setupProfile := setupProfiles[h]
		path := entryPaths[h]
		var region string
		var e error
		if setupProfile["kind"] == "builtin" {
			region, e = renderGuide(h, pid, display, guideBody, guideVer)
		} else {
			region, e = renderGuideAtEntry(h, path, pid, display, guideBody, guideVer)
		}
		if e != nil {
			return nil, e
		}
		current, _ := files[path].(string)
		if hasLegacyEntryMarker(current) && !migrationComplete {
			blocked = append(blocked, map[string]any{"id": "entry:" + h, "path": path, "reason": "legacy_1x_requires_migration", "message": "1.x 작업 정본을 Hub로 가져오고 ai-workflow/HUB_MIGRATED.json 을 커밋한 뒤 다시 셋업한다"})
			continue
		}
		if hasLegacyEntryMarker(current) {
			var migrated bool
			current, migrated = migrateLegacyStartGuidance(current)
			if !migrated {
				blocked = append(blocked, map[string]any{"id": "entry:" + h, "path": path, "reason": "legacy_entry_needs_review", "message": "진입 파일의 1.x 시작 안내가 표준 생성 문안과 다르다 — 사람이 Hub 경로로 고친 뒤 다시 셋업한다"})
				continue
			}
		}
		merged, ok := mergeGuide(current, region)
		if !ok {
			blocked = append(blocked, map[string]any{"id": "entry:" + h, "path": path, "reason": "local_edit_detected", "message": "렌더 영역이 허브가 낸 판과 다르다 — 덮어쓰지 않는다. 고칠 것은 허브에 지침 제안으로 (요구 R7.5)"})
		} else {
			gv := guideVersion(guideVer)
			if err := issue("entry:"+h, "entry", path, digest(merged), gv); err != nil {
				return nil, err
			}
			steps = append(steps, map[string]any{"id": "entry:" + h, "op": "write", "path": path, "content": merged, "sha256_after": digest(merged), "guide_version": gv, "note": "이 파일은 커밋한다 (D10)"})
		}
		if h == "codex" {
			if err := issue("harness:codex", "harness", "", "", ""); err != nil {
				return nil, err
			}
			steps = append(steps, map[string]any{"id": "harness:codex", "op": "run_and_report", "run": []string{"codex", "mcp", "add", "workflow-hub", "--url", publicURL + "/mcp", "--bearer-token-env-var", "WORKFLOW_HUB_TOKEN"}, "note": "이 명령은 서버 항목을 다시 쓴다. 자동 승인 정책은 별도로 사람이 선택한다"})
		}
		if (h == "claude-code" || h == "minimax-code") && !mcpJSONWritten {
			content, err := setupMCPJSON(strArg(files, ".mcp.json", ""), publicURL+"/mcp")
			if err != nil {
				return nil, err
			}
			if err := issue("harness:mcp-json", "harness", ".mcp.json", digest(content), ""); err != nil {
				return nil, err
			}
			steps = append(steps, map[string]any{"id": "harness:mcp-json", "op": "write", "path": ".mcp.json", "content": content, "sha256_after": digest(content), "note": "토큰은 환경 변수 참조만 저장한다"})
			mcpJSONWritten = true
		}
		if h == "antigravity" {
			if err := issue("harness:antigravity", "harness", "", "", ""); err != nil {
				return nil, err
			}
			steps = append(steps, map[string]any{"id": "harness:antigravity", "op": "user_scope_write", "run": []string{"agy", "mcp", "add", "--header", "Authorization: Bearer " + token, "workflow-hub", publicURL + "/mcp"}, "path": "~/.gemini/config/mcp_config.json", "warning": "Antigravity 설정은 토큰 값을 사용자 범위 파일에 저장할 수 있으므로 공유하지 않는다"})
		}
		if kind, _ := setupProfile["kind"].(string); kind == mcpHTTPJSONProfile {
			configPath, _ := setupProfile["mcp_config_path"].(string)
			if !(configPath == ".mcp.json" && mcpJSONWritten) && !dynamicConfigsWritten[configPath] {
				content, err := setupMCPJSONAtPath(strArg(files, configPath, ""), publicURL+"/mcp", configPath)
				if err != nil {
					return nil, err
				}
				stepID := "harness:mcp-json:" + h
				if err := issue(stepID, "harness", configPath, digest(content), ""); err != nil {
					return nil, err
				}
				steps = append(steps, map[string]any{"id": stepID, "op": "write", "path": configPath, "content": content, "sha256_after": digest(content), "note": "관리자가 승인한 MCP Streamable HTTP JSON 프로필. 토큰은 환경 변수 참조만 저장한다."})
				dynamicConfigsWritten[configPath] = true
			}
		}
	}
	legacy := []string{}
	for path, text := range files {
		if content, ok := text.(string); ok {
			if hasLegacyEntryMarker(content) {
				legacy = append(legacy, path)
			}
		}
	}
	sort.Strings(legacy)
	var legacyOut any
	if len(legacy) > 0 {
		entryUpdateAllowed := migrationComplete
		if !entryUpdateAllowed {
			entryUpdateAllowed = true
			for _, path := range legacy {
				for _, entry := range entryPaths {
					if path == entry {
						entryUpdateAllowed = false
					}
				}
			}
		}
		legacyOut = map[string]any{"files": legacy, "migration_complete": migrationComplete, "entry_update_allowed": entryUpdateAllowed,
			"next": "1.x kit 흔적이 있다 — 전환은 사람이 선택 클라이언트로 한다: python .workflow-hub/hub_client.py migrate plan → (표를 보이고 고른 종류로) migrate import (hub_spec §6.6). 가져오기와 ai-workflow/HUB_MIGRATED.json 표식 커밋 뒤 셋업을 다시 실행하면 진입 안내를 갱신한다"}
	}
	relay := map[string]any{"required": false, "config_present": false, "status": nil, "next": "선택 사항 — 현재 셋업에서는 로컬 중계가 필요하지 않음"}
	if raw := relayScan; raw != nil {
		required, _ := raw["required"].(bool)
		config, _ := raw["config_present"].(bool)
		relay = map[string]any{"required": required, "config_present": config, "status": raw["status"], "next": "선택 사항 — 현재 셋업에서는 로컬 중계가 필요하지 않음"}
		if required {
			relay["next"] = "Python 우선: python -m workflow_kit hub relay status → 필요하면 init → allow add → serve"
		}
	}
	return map[string]any{"stage": "files", "steps": steps, "blocked": blocked, "legacy_1x": legacyOut, "relay": relay, "next": "hub_setup_confirm — 쓴 파일의 sha256 과 명령 결과를 보낸다. 끝나면 WORKFLOW_HUB_TOKEN 을 .workflow-hub/env 에서 환경에 올리고 하네스를 다시 연결한다"}, nil
}
