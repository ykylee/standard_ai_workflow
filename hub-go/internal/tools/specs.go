package tools

// ToolSpec describes a single MCP/HTTP tool exposed by workflow-hub.
type ToolSpec struct {
	Name        string
	Bundle      string
	Description string
	Properties  map[string]map[string]any
	Required    []string
}

// SessionArg is the shared optional session argument added to every token-bundle tool schema.
var SessionArg = map[string]any{"type": "string", "description": "세션 시작이 준 세션 ID (S-…) — 실으면 이 세션의 받은편지함이 응답의 hub_inbox 칸에 실린다"}

// AllProperties returns Properties plus the shared session argument for token-bundle tools.
func (s *ToolSpec) AllProperties() map[string]map[string]any {
	out := make(map[string]map[string]any, len(s.Properties)+1)
	for k, v := range s.Properties {
		out[k] = v
	}
	if s.Bundle == "token" {
		if _, ok := out["session"]; !ok {
			out["session"] = SessionArg
		}
	}
	return out
}

// Schema returns the JSON Schema object for the tool input.
func (s *ToolSpec) Schema() map[string]any {
	all := s.AllProperties()
	props := make(map[string]any, len(all)+1)
	props["contract"] = map[string]any{"type": "string"}
	for k, v := range all {
		props[k] = v
	}
	req := make([]string, len(s.Required))
	copy(req, s.Required)
	return map[string]any{
		"type":                 "object",
		"properties":           props,
		"required":             req,
		"additionalProperties": false,
	}
}

// ToolOrder preserves canonical declaration order across all 74 hub tools.
var ToolOrder = []*ToolSpec{
	{
		Name:        "hub_project_lookup",
		Bundle:      "bootstrap",
		Description: "git 원격 주소로 허브의 프로젝트를 찾는다 (없으면 project_id=null).",
		Properties: map[string]map[string]any{
			"remote_url": map[string]any{"type": "string"},
		},
		Required: []string{"remote_url"},
	},
	{
		Name:        "hub_project_register",
		Bundle:      "bootstrap",
		Description: "프로젝트를 등록한다 — 등록자가 소유자 콜사인이 되고 토큰을 이 응답에서 한 번만 받는다. git 원격이 없으면 remote_url 을 빼거나 비운다 — 로컬 키로 등록하고, 원격이 생기면 hub_project_bind_remote.",
		Properties: map[string]map[string]any{
			"remote_url":   map[string]any{"type": "string"},
			"display_name": map[string]any{"type": "string"},
			"callsign":     map[string]any{"type": "string"},
			"kind":         map[string]any{"type": "string"},
			"label":        map[string]any{"type": "string"},
			"host":         map[string]any{"type": "string"},
		},
		Required: []string{"display_name", "callsign", "kind"},
	},
	{
		Name:        "hub_callsign_register",
		Bundle:      "bootstrap",
		Description: "등록된 프로젝트에 콜사인으로 합류한다 — 토큰을 이 응답에서 한 번만 받는다. human 은 소유자 승인 전 agent 권한.",
		Properties: map[string]map[string]any{
			"project_id": map[string]any{"type": "string"},
			"callsign":   map[string]any{"type": "string"},
			"kind":       map[string]any{"type": "string"},
			"label":      map[string]any{"type": "string"},
			"host":       map[string]any{"type": "string"},
		},
		Required: []string{"project_id", "callsign", "kind"},
	},
	{
		Name:        "hub_setup_plan",
		Bundle:      "bootstrap",
		Description: "셋업 쓰기 지시 — .gitignore 확인 전에는 토큰 파일 지시가 나오지 않는다. token 은 등록 응답의 것 (DS4). harnesses: claude-code · codex · minimax-code · antigravity. scan.files: 경로 → 지금 내용(없으면 null), scan.relay: {required, config_present, status}.",
		Properties: map[string]map[string]any{
			"project_id": map[string]any{"type": "string"},
			"token":      map[string]any{"type": "string"},
			"harnesses":  map[string]any{"type": "array"},
			"scan":       map[string]any{"type": "object"},
		},
		Required: []string{"project_id", "token", "harnesses"},
	},
	{
		Name:        "hub_setup_confirm",
		Bundle:      "bootstrap",
		Description: "쓴 파일의 sha256 · 명령 결과를 대조해 셋업 단계를 확인한다. files: [{path, sha256}], checks: [{name, rc, output}].",
		Properties: map[string]map[string]any{
			"project_id": map[string]any{"type": "string"},
			"token":      map[string]any{"type": "string"},
			"files":      map[string]any{"type": "array"},
			"checks":     map[string]any{"type": "array"},
		},
		Required: []string{"project_id", "token"},
	},
	{
		Name:        "hub_session_start",
		Bundle:      "token",
		Description: "세션 시작 확인 — 인자 없이 부르면 허브 쪽 결과와 저장소에서 돌릴 명령, repo_results 를 실어 다시 부르면 판정. repo_results 는 {name: {rc, output}} 객체 또는 [{name, rc, output}] 목록 (이름에 : · . 가 든 키를 못 싣는 하네스는 목록으로).",
		Properties: map[string]map[string]any{
			"repo_results": map[string]any{"type": []string{"object", "array"}},
			"client":       map[string]any{"type": "object"},
			"session":      map[string]any{"type": []string{"object", "string"}, "description": "2.1 — 첫 호출은 {harness, harness_session_id?, kind?, delivery?, resume?} 로 세션 등록, 이후(두 번째 호출 포함)는 받은 세션 ID 문자열"},
		},
		Required: []string{},
	},
	{
		Name: "hub_harness_report", Bundle: "token", Description: "미지원 하네스의 비밀 없는 프로필과 셋업 후보를 제보한다. 허브 관리자가 승인하면 검증된 mcp-http-json-v1 셋업 프로필도 등록한다.",
		Properties: map[string]map[string]any{"report": {"type": "object"}}, Required: []string{"report"},
	},
	{
		Name: "hub_harness_report_list", Bundle: "token", Description: "이 프로젝트가 제출한 하네스 제보 상태 목록.",
		Properties: map[string]map[string]any{"status": {"type": "string"}}, Required: []string{},
	},
	{
		Name: "hub_harness_registry_list", Bundle: "token", Description: "승인된 허브 전역 하네스 프로필과 셋업 지원 상태 목록.",
		Properties: map[string]map[string]any{}, Required: []string{},
	},
	{
		Name:        "hub_guide_render",
		Bundle:      "token",
		Description: "하네스 진입 파일의 새 내용 (렌더 영역 갱신). current = 지금 파일 내용 (없으면 생략). 로컬에서 고친 영역이면 blocked.",
		Properties: map[string]map[string]any{
			"harness": map[string]any{"type": "string"},
			"current": map[string]any{"type": "string"},
		},
		Required: []string{"harness"},
	},
	{
		Name:        "hub_callsign_approve",
		Bundle:      "token",
		Description: "사람(human) 콜사인을 승인한다 — 승인된 human 소유자만. 승인 전 human 은 agent 권한이라 결정에 답할 수 없다.",
		Properties: map[string]map[string]any{
			"callsign": map[string]any{"type": "string"},
		},
		Required: []string{"callsign"},
	},
	{
		Name:        "hub_project_bind_remote",
		Bundle:      "token",
		Description: "프로젝트에 git 원격 주소를 묶는다 — 원격 없이(로컬 키로) 등록한 뒤 원격을 만들었을 때. 승인된 human 소유자만. 다른 프로젝트가 쓰는 주소면 409 alias_taken.",
		Properties: map[string]map[string]any{
			"remote_url": map[string]any{"type": "string"},
		},
		Required: []string{"remote_url"},
	},
	{
		Name:        "hub_guide_get",
		Bundle:      "token",
		Description: "프로젝트 지침 — 지금 판 · 판 이력 · 제안(열린 제안은 diff).",
		Properties:  map[string]map[string]any{},
		Required:    []string{},
	},
	{
		Name:        "hub_guide_propose",
		Bundle:      "token",
		Description: "프로젝트 지침 변경 — base_version 은 지금 판(다르면 409). 승인된 human 이면 바로 판 +1, agent · 승인 전 human 은 제안으로 남는다 (D11). 렌더 예산(8KB)을 넘으면 422.",
		Properties: map[string]map[string]any{
			"base_version": map[string]any{"type": "integer"},
			"body":         map[string]any{"type": "string"},
			"note":         map[string]any{"type": "string"},
		},
		Required: []string{"base_version", "body"},
	},
	{
		Name:        "hub_guide_decide",
		Bundle:      "token",
		Description: "열린 지침 제안을 승인(approve=true) · 거절한다 — 승인된 human 만.",
		Properties: map[string]map[string]any{
			"proposal_id": map[string]any{"type": "string"},
			"approve":     map[string]any{"type": "boolean"},
		},
		Required: []string{"proposal_id", "approve"},
	},
	{
		Name:        "hub_migrate_plan",
		Bundle:      "token",
		Description: "1.x 전환 계획 (소유자만) — 인자 없이 부르면 저장소에서 돌릴 명령, scan={name:{rc,output}} 을 실어 다시 부르면 감지 보고 · 전환 표 · 같은 ID 정본 · 하네스 안내와 migration_id. 원본은 건드리지 않는다.",
		Properties: map[string]map[string]any{
			"scan": map[string]any{"type": "object"},
		},
		Required: []string{},
	},
	{
		Name:        "hub_migrate_import",
		Bundle:      "token",
		Description: "1.x 들여오기 묶음 (소유자만) — kinds: tasks · archive · handoff · roadmap · wiki · memory_index · checkpoint · guide_draft 가운데 소유자가 고른 것. files=[{path, content}] 는 계획에 있는 경로만. 요청 상한(256KB) 안으로 나눠 보내고 마지막에 final=true. 다시 보내도 있는 것은 건너뛴다.",
		Properties: map[string]map[string]any{
			"migration_id": map[string]any{"type": "string"},
			"kinds":        map[string]any{"type": "array"},
			"files":        map[string]any{"type": "array"},
			"final":        map[string]any{"type": "boolean"},
		},
		Required: []string{"migration_id", "kinds"},
	},
	{
		Name:        "hub_migrate_marker",
		Bundle:      "token",
		Description: "'허브로 옮김' 표식 (소유자만, 끝난 전환만) — action=issue: ai-workflow/HUB_MIGRATED.json 쓰기 지시 · 커밋 명령, confirm(sha256): 쓴 파일 대조, revert: 삭제 지시 · 확인 명령, confirm_revert(check={rc, output}). 되돌려도 허브 데이터는 옮기지 않는다.",
		Properties: map[string]map[string]any{
			"migration_id": map[string]any{"type": "string"},
			"action":       map[string]any{"type": "string"},
			"sha256":       map[string]any{"type": "string"},
			"check":        map[string]any{"type": "object"},
		},
		Required: []string{"migration_id", "action"},
	},
	{
		Name:        "hub_migrate_report",
		Bundle:      "token",
		Description: "1.x 전환 기록 — 계획 · 종류별 들인 것 · 건너뛴 것 · 실패.",
		Properties: map[string]map[string]any{
			"migration_id": map[string]any{"type": "string"},
		},
		Required: []string{"migration_id"},
	},
	{
		Name:        "hub_project_doc_get",
		Bundle:      "token",
		Description: "프로젝트 문서 (name=purpose · profile — 1.x 의 PURPOSE.md · PROJECT_PROFILE.md).",
		Properties: map[string]map[string]any{
			"name": map[string]any{"type": "string"},
		},
		Required: []string{"name"},
	},
	{
		Name:        "hub_project_doc_put",
		Bundle:      "token",
		Description: "프로젝트 문서를 쓴다 — 승인된 human 만. expected_version 이 다르면 409 (새 문서는 0). 상태 요약의 목적 · 프로젝트 칸이 여기서 나온다.",
		Properties: map[string]map[string]any{
			"name":             map[string]any{"type": "string"},
			"body":             map[string]any{"type": "string"},
			"expected_version": map[string]any{"type": "integer"},
		},
		Required: []string{"name", "body"},
	},
	{
		Name:        "hub_project_export",
		Bundle:      "token",
		Description: "허브 간 이전 — 소유자가 자기 프로젝트 묶음을 뜬다. seal_to(새 허브 주소)를 주면 먼저 봉인한다 (그 뒤 410). 묶음은 크다 — 선택 클라이언트(hub_client.py move)가 나른다.",
		Properties: map[string]map[string]any{
			"seal_to": map[string]any{"type": "string"},
		},
		Required: []string{},
	},
	{
		Name:        "hub_project_unseal",
		Bundle:      "token",
		Description: "허브 간 이전이 실패했을 때 — 소유자가 봉인을 푼다.",
		Properties:  map[string]map[string]any{},
		Required:    []string{},
	},
	{
		Name:        "hub_project_import",
		Bundle:      "bootstrap",
		Description: "허브 간 이전 — 대상 허브 관리자가 준 일회용 초대 코드로 묶음을 들인다 (토큰 없이, 코드가 권한).",
		Properties: map[string]map[string]any{
			"invite": map[string]any{"type": "string"},
			"bundle": map[string]any{"type": "object"},
		},
		Required: []string{"invite", "bundle"},
	},
	{
		Name:        "hub_whoami",
		Bundle:      "token",
		Description: "이 토큰의 프로젝트 · 콜사인 · 권한.",
		Properties:  map[string]map[string]any{},
		Required:    []string{},
	},
	{
		Name:        "hub_task_list",
		Bundle:      "token",
		Description: "task 목록 (status · assignee 로 거른다, assignee='' 는 맡은 이 없음).",
		Properties: map[string]map[string]any{
			"status":   map[string]any{"type": "string"},
			"assignee": map[string]any{"type": "string"},
			"limit":    map[string]any{"type": "integer"},
		},
		Required: []string{},
	},
	{
		Name:        "hub_task_get",
		Bundle:      "token",
		Description: "task 하나 (묶인 커밋 포함).",
		Properties: map[string]map[string]any{
			"id": map[string]any{"type": "string"},
		},
		Required: []string{"id"},
	},
	{
		Name:        "hub_task_create",
		Bundle:      "token",
		Description: "task 를 만든다 — ID 는 TASK-<날짜>-<콜사인>-<NNN> (DS3). done 으로 만들 수 없다.",
		Properties: map[string]map[string]any{
			"title":             map[string]any{"type": "string"},
			"status":            map[string]any{"type": "string"},
			"priority":          map[string]any{"type": "string"},
			"branch":            map[string]any{"type": "string"},
			"wbs":               map[string]any{"type": "string"},
			"wbs_exempt_reason": map[string]any{"type": "string"},
			"description":       map[string]any{"type": "string"},
			"plan_md":           map[string]any{"type": "string", "description": "1.x task 파일의 Plan 절 원문 (DS2)"},
			"fields":            map[string]any{"type": "object", "description": "표준 task 필드 외 category={level_1,level_2,level_3}, tests=[{id,name,required,runs:[{status:passed|failed|skipped,summary,run_at,commit_sha}]}]. 실행은 세션이 하고 결과를 기록한다."},
			"request_id":        map[string]any{"type": "string", "description": "멱등 키 — 같은 값으로 다시 보내면 처음 결과를 돌려준다"},
		},
		Required: []string{"title"},
	},
	{
		Name:        "hub_task_update",
		Bundle:      "token",
		Description: "task 칸을 고친다 — expected_version 이 다르면 409. 계획(plan_md)은 1.x 계약으로 린트 · 결정 상태 재계산. decision_states: {D<n>: answered:<value>|proposed}. 열린 결정을 걷으면 note 필수. done 은 hub_task_close.",
		Properties: map[string]map[string]any{
			"id":               map[string]any{"type": "string"},
			"expected_version": map[string]any{"type": "integer"},
			"values":           map[string]any{"type": "object"},
			"decision_states":  map[string]any{"type": "object"},
			"note":             map[string]any{"type": "string"},
			"request_id":       map[string]any{"type": "string", "description": "멱등 키 — 같은 값으로 다시 보내면 처음 결과를 돌려준다"},
		},
		Required: []string{"id", "expected_version"},
	},
	{
		Name:        "hub_task_close",
		Bundle:      "token",
		Description: "task 를 done 으로 닫는다 — done 게이트(검증 결과 필수 · 열린 결정 · 계획 오류 규칙)를 1.x 와 같은 함수로 판정.",
		Properties: map[string]map[string]any{
			"id":                map[string]any{"type": "string"},
			"expected_version":  map[string]any{"type": "integer"},
			"validation_result": map[string]any{"type": "string"},
			"request_id":        map[string]any{"type": "string", "description": "멱등 키 — 같은 값으로 다시 보내면 처음 결과를 돌려준다"},
		},
		Required: []string{"id", "expected_version", "validation_result"},
	},
	{
		Name:        "hub_plan_respond",
		Bundle:      "token",
		Description: "결정 응답(workflow-kit-plan-response/1 본문 그대로)을 받는다 — 자격 판정 뒤에만 결정 상태에 반영한다.",
		Properties: map[string]map[string]any{
			"task_id": map[string]any{"type": "string"},
			"body":    map[string]any{"type": "string"},
		},
		Required: []string{"task_id", "body"},
	},
	{
		Name:        "hub_plan_status",
		Bundle:      "token",
		Description: "task 계획의 결정 상태 · 열린 결정 · 반영된 응답 수.",
		Properties: map[string]map[string]any{
			"task_id": map[string]any{"type": "string"},
		},
		Required: []string{"task_id"},
	},
	{
		Name:        "hub_handoff_get",
		Bundle:      "token",
		Description: "콜사인의 handoff (기본: 나). 다른 콜사인 것도 읽을 수 있다 (G3).",
		Properties: map[string]map[string]any{
			"callsign": map[string]any{"type": "string"},
		},
		Required: []string{},
	},
	{
		Name:        "hub_handoff_put",
		Bundle:      "token",
		Description: "내 handoff 를 쓴다 — 칸: baseline · focus · in_progress · blocked · recent_done(10건 넘치면 옮긴다) · next · risks.",
		Properties: map[string]map[string]any{
			"handoff":          map[string]any{"type": "object"},
			"expected_version": map[string]any{"type": "integer"},
		},
		Required: []string{"handoff"},
	},
	{
		Name:        "hub_session_end",
		Bundle:      "token",
		Description: "세션 끝 — handoff 와 진행 한 줄들을 한 트랜잭션으로 쓴다. 다음은 커밋 → push.",
		Properties: map[string]map[string]any{
			"handoff":          map[string]any{"type": "object"},
			"expected_version": map[string]any{"type": "integer"},
			"progress":         map[string]any{"type": "array"},
		},
		Required: []string{"handoff"},
	},
	{
		Name:        "hub_checkpoint_put",
		Bundle:      "token",
		Description: "compact 직전 체크포인트 — next · unverified · verified · rejected · tasks · branch.",
		Properties: map[string]map[string]any{
			"body": map[string]any{"type": "object"},
		},
		Required: []string{"body"},
	},
	{
		Name:        "hub_compact_resume",
		Bundle:      "token",
		Description: "compact 직후 — 체크포인트 · 내 task · 그 사이 다른 콜사인의 변경 · 요약에서 빠진 식별자 (summary_ids 없으면 대조 불가).",
		Properties: map[string]map[string]any{
			"summary_ids": map[string]any{"type": "array"},
		},
		Required: []string{},
	},
	{
		Name:        "hub_state",
		Bundle:      "token",
		Description: "상태 요약 (state.json v1 — 1.x 생성기로 만든다). callsign 기본: 나.",
		Properties: map[string]map[string]any{
			"callsign": map[string]any{"type": "string"},
		},
		Required: []string{},
	},
	{
		Name:        "hub_roadmap_get",
		Bundle:      "token",
		Description: "로드맵 원문 (index.md · M-NNN-*.md).",
		Properties:  map[string]map[string]any{},
		Required:    []string{},
	},
	{
		Name:        "hub_roadmap_put",
		Bundle:      "token",
		Description: "로드맵 문서 하나를 쓴다 — 스키마 오류는 필드 · 제약과 함께 거절, expected_version 이 다르면 409 (새 문서는 0).",
		Properties: map[string]map[string]any{
			"path":             map[string]any{"type": "string"},
			"expected_version": map[string]any{"type": "integer"},
			"body":             map[string]any{"type": "string"},
		},
		Required: []string{"path", "body"},
	},
	{
		Name:        "hub_roadmap_state",
		Bundle:      "token",
		Description: "로드맵 진척 (roadmap_state v1 형식) — 산출물 존재는 미측정.",
		Properties:  map[string]map[string]any{},
		Required:    []string{},
	},
	{
		Name:        "hub_wiki_ingest",
		Bundle:      "token",
		Description: "위키 ingest — 페이지 묶음 [{path, body | delete:true, expected_version(새 페이지 0), source?:{repo_key, sha}}] 을 한 번에 쓴다. 한 페이지라도 version 이 다르면 묶음 전체 409 (부분 반영 0). log 항목은 허브가 만든다. index.md · log.md 는 생성물이라 쓸 수 없다.",
		Properties: map[string]map[string]any{
			"pages":      map[string]any{"type": "array"},
			"summary":    map[string]any{"type": "string"},
			"request_id": map[string]any{"type": "string", "description": "멱등 키 — 같은 값으로 다시 보내면 처음 결과를 돌려준다"},
		},
		Required: []string{"pages", "summary"},
	},
	{
		Name:        "hub_wiki_get",
		Bundle:      "token",
		Description: "위키 페이지 하나 (index.md · log.md 는 생성해서 돌려준다).",
		Properties: map[string]map[string]any{
			"path": map[string]any{"type": "string"},
		},
		Required: []string{"path"},
	},
	{
		Name:        "hub_wiki_list",
		Bundle:      "token",
		Description: "위키 페이지 목록 (경로 · 제목 · version). prefix 로 좁힌다.",
		Properties: map[string]map[string]any{
			"prefix": map[string]any{"type": "string"},
		},
		Required: []string{},
	},
	{
		Name:        "hub_wiki_search",
		Bundle:      "token",
		Description: "위키 검색 — 낱말이 모두 들어간 페이지 (경로 · 제목 · 본문).",
		Properties: map[string]map[string]any{
			"query": map[string]any{"type": "string"},
			"limit": map[string]any{"type": "integer"},
		},
		Required: []string{"query"},
	},
	{
		Name: "hub_knowledge_source_register", Bundle: "token", Description: "프로젝트 Git 문서 원본을 등록한다. 허용 경로만 스냅샷으로 수신하며 허브는 Git 원격을 실행하지 않는다.",
		Properties: map[string]map[string]any{"source_id": {"type": "string"}, "repo_key": {"type": "string"}, "allowlist": {"type": "array"}}, Required: []string{"source_id", "repo_key", "allowlist"},
	},
	{
		Name: "hub_knowledge_sync", Bundle: "token", Description: "등록된 Git 지식 원본에 커밋 고정 문서 스냅샷을 동기화한다.",
		Properties: map[string]map[string]any{"source_id": {"type": "string"}, "commit_sha": {"type": "string"}, "documents": {"type": "array"}}, Required: []string{"source_id", "commit_sha", "documents"},
	},
	{
		Name: "hub_knowledge_search", Bundle: "token", Description: "프로젝트 범위 지식 검색. 결과에 정본·커밋·판 provenance를 포함한다.",
		Properties: map[string]map[string]any{"query": {"type": "string"}, "limit": {"type": "integer"}}, Required: []string{"query"},
	},
	{
		Name: "hub_knowledge_get", Bundle: "token", Description: "provenance ref로 고정된 문서 판 또는 Wiki revision을 조회한다.",
		Properties: map[string]map[string]any{"ref": {"type": "string"}}, Required: []string{"ref"},
	},
	{
		Name: "hub_dcr_create", Bundle: "token", Description: "프로젝트 결정 변경 제안(DCR)을 생성한다. 수락은 승인된 human owner만 할 수 있다.",
		Properties: map[string]map[string]any{"title": {"type": "string"}, "rationale": {"type": "string"}, "proposal": {"type": "string"}, "target_refs": {"type": "array"}}, Required: []string{"title", "rationale", "proposal"},
	},
	{
		Name: "hub_dcr_decide", Bundle: "token", Description: "DCR 승인/거절. 승인 시 Git ADR 커밋·동기화 전까지 approved_pending_export 상태로 둔다.",
		Properties: map[string]map[string]any{"id": {"type": "string"}, "expected_version": {"type": "integer"}, "outcome": {"type": "string"}, "rationale": {"type": "string"}}, Required: []string{"id", "expected_version", "outcome", "rationale"},
	},
	{
		Name: "hub_dcr_list", Bundle: "token", Description: "프로젝트 DCR 목록과 현재 상태.",
		Properties: map[string]map[string]any{"status": {"type": "string"}}, Required: []string{},
	},
	{
		Name: "hub_dcr_get", Bundle: "token", Description: "DCR 제안, 승인/거절 근거, 감사 timeline 및 ADR 연결을 조회한다.",
		Properties: map[string]map[string]any{"id": {"type": "string"}}, Required: []string{"id"},
	},
	{
		Name:        "hub_wiki_lint",
		Bundle:      "token",
		Description: "위키 lint — 1.x 와 같은 함수로 정위치(V-1) · index 구조(V-4) · 양방향 링크(bidir), 깨진 위키 링크. 저장소 참조 · 출처 sha · freshness 는 원격 읽기를 켰을 때만 측정, 아니면 미측정.",
		Properties:  map[string]map[string]any{},
		Required:    []string{},
	},
	{
		Name:        "hub_wiki_remote_set",
		Bundle:      "token",
		Description: "위키 원격 읽기를 켜고 끈다 (소유자만) — fetch_url 을 주면 lint 가 그 저장소를 읽기 전용으로 받아 저장소 참조 · 출처 sha · freshness 를 잰다. 빈 값이면 끈다 (그 셋은 미측정).",
		Properties: map[string]map[string]any{
			"fetch_url": map[string]any{"type": "string"},
		},
		Required: []string{"fetch_url"},
	},
	{
		Name:        "hub_memory_entry_put",
		Bundle:      "token",
		Description: "memory_index entry 하나를 쓴다 — 1.x 스키마(MemoryEntry)로 검증, expected_version 이 다르면 409 (새 entry 는 0).",
		Properties: map[string]map[string]any{
			"entry":            map[string]any{"type": "object"},
			"expected_version": map[string]any{"type": "integer"},
		},
		Required: []string{"entry"},
	},
	{
		Name:        "hub_memory_entry_get",
		Bundle:      "token",
		Description: "memory_index entry 하나.",
		Properties: map[string]map[string]any{
			"id": map[string]any{"type": "string"},
		},
		Required: []string{"id"},
	},
	{
		Name:        "hub_memory_entry_list",
		Bundle:      "token",
		Description: "memory_index entry 목록 (id · version · primary_abstraction).",
		Properties:  map[string]map[string]any{},
		Required:    []string{},
	},
	{
		Name:        "hub_wiki_import_dir",
		Bundle:      "token",
		Description: "1.x 위키 디렉터리를 무손실로 들인다 — files [{path(위키 뿌리 상대), content}]. 페이지는 바이트 그대로, index.md · log.md 원문은 보관 기록으로, .md 아닌 파일은 건너뛴다. overwrite 가 아니면 있는 페이지는 409. 요청 상한(256KB)을 넘으면 여러 번 나눠 부른다.",
		Properties: map[string]map[string]any{
			"files":      map[string]any{"type": "array"},
			"summary":    map[string]any{"type": "string"},
			"overwrite":  map[string]any{"type": "boolean"},
			"request_id": map[string]any{"type": "string", "description": "멱등 키 — 같은 값으로 다시 보내면 처음 결과를 돌려준다"},
		},
		Required: []string{"files", "summary"},
	},
	{
		Name:        "hub_wiki_export",
		Bundle:      "token",
		Description: "위키 내보내기를 쓰기 지시로 돌려준다 (허브는 저장소에 쓰지 않는다). format=dir: 1.x 위키 배치 그대로(무손실) + 내보내기 표식. format=okf: OKF 출판(손실 — 빠진 페이지를 목록으로). 크면 next_cursor 로 이어 부른다.",
		Properties: map[string]map[string]any{
			"format":  map[string]any{"type": "string"},
			"out_dir": map[string]any{"type": "string"},
			"cursor":  map[string]any{"type": "integer"},
		},
		Required: []string{"format"},
	},
	{
		Name:        "hub_wiki_import_okf",
		Bundle:      "token",
		Description: "남의 OKF 묶음을 들인다 — files [{path(묶음 뿌리 상대), content}], loose 한 방향 (OKF 형태 그대로 페이지가 된다).",
		Properties: map[string]map[string]any{
			"files":      map[string]any{"type": "array"},
			"summary":    map[string]any{"type": "string"},
			"request_id": map[string]any{"type": "string", "description": "멱등 키 — 같은 값으로 다시 보내면 처음 결과를 돌려준다"},
		},
		Required: []string{"files", "summary"},
	},
	{
		Name:        "hub_task_claim",
		Bundle:      "token",
		Description: "task 를 맡는다 — 다른 콜사인이 맡고 있으면 409. planned 면 in_progress 로 바꾼다 (놓아도 되돌리지 않는다).",
		Properties: map[string]map[string]any{
			"id":         map[string]any{"type": "string"},
			"request_id": map[string]any{"type": "string", "description": "멱등 키 — 같은 값으로 다시 보내면 처음 결과를 돌려준다"},
		},
		Required: []string{"id"},
	},
	{
		Name:        "hub_task_release",
		Bundle:      "token",
		Description: "맡은 task 를 놓는다 (맡은 이 · 소유자).",
		Properties: map[string]map[string]any{
			"id":         map[string]any{"type": "string"},
			"request_id": map[string]any{"type": "string", "description": "멱등 키 — 같은 값으로 다시 보내면 처음 결과를 돌려준다"},
		},
		Required: []string{"id"},
	},
	{
		Name:        "hub_task_progress",
		Bundle:      "token",
		Description: "진행 한 줄을 남긴다 — 허브가 시각을 붙인다.",
		Properties: map[string]map[string]any{
			"id":         map[string]any{"type": "string"},
			"note":       map[string]any{"type": "string"},
			"request_id": map[string]any{"type": "string", "description": "멱등 키 — 같은 값으로 다시 보내면 처음 결과를 돌려준다"},
		},
		Required: []string{"id", "note"},
	},
	{
		Name:        "hub_task_link_commit",
		Bundle:      "token",
		Description: "task 에 커밋 sha 를 묶는다 — 허브는 그 커밋을 읽지 않는다.",
		Properties: map[string]map[string]any{
			"id":         map[string]any{"type": "string"},
			"sha":        map[string]any{"type": "string"},
			"branch":     map[string]any{"type": "string"},
			"request_id": map[string]any{"type": "string", "description": "멱등 키 — 같은 값으로 다시 보내면 처음 결과를 돌려준다"},
		},
		Required: []string{"id", "sha"},
	},
	{
		Name:        "hub_session_update",
		Bundle:      "token",
		Description: "세션 칸 고침 — kind(interactive/worker) · allow_wait(켜기는 승인된 human 만) · delivery · harness_session_id.",
		Properties: map[string]map[string]any{
			"session":            map[string]any{"type": "string"},
			"kind":               map[string]any{"type": "string"},
			"allow_wait":         map[string]any{"type": "boolean"},
			"delivery":           map[string]any{"type": "array"},
			"harness_session_id": map[string]any{"type": "string"},
		},
		Required: []string{"session"},
	},
	{
		Name:        "hub_session_list",
		Bundle:      "token",
		Description: "프로젝트의 세션 · 상태(idle/working/waiting/ended/unknown — unknown 수는 따로) · 마지막 신호 · 열린 배정.",
		Properties: map[string]map[string]any{
			"status":   map[string]any{"type": "string"},
			"callsign": map[string]any{"type": "string"},
		},
		Required: []string{},
	},
	{
		Name:        "hub_wait",
		Bundle:      "token",
		Description: "일 없는 세션이 기다린다 — 이 세션 앞 메시지가 오면 바로 돌려주고, 없으면 최대 50초 뒤 빈 응답 (call_again=true 면 다시 부른다). kind=worker 세션만 (사람이 보는 세션은 꺼짐).",
		Properties: map[string]map[string]any{
			"session":   map[string]any{"type": "string"},
			"timeout_s": map[string]any{"type": "integer"},
		},
		Required: []string{"session"},
	},
	{
		Name:        "hub_inbox_ack",
		Bundle:      "token",
		Description: "받은편지함 메시지 확인 — accept(배정 수락) · decline(거절 + reason) · seen(읽음). 같은 메시지에 다시 보내도 한 번.",
		Properties: map[string]map[string]any{
			"session":    map[string]any{"type": "string"},
			"message_id": map[string]any{"type": "string"},
			"decision":   map[string]any{"type": "string"},
			"reason":     map[string]any{"type": "string"},
			"request_id": map[string]any{"type": "string", "description": "멱등 키 — 같은 값으로 다시 보내면 처음 결과를 돌려준다"},
		},
		Required: []string{"session", "message_id", "decision"},
	},
	{
		Name:        "hub_inbox_list",
		Bundle:      "token",
		Description: "받은편지함 읽기 (상태를 바꾸지 않는다) — session 을 주면 그 세션 앞까지.",
		Properties: map[string]map[string]any{
			"session": map[string]any{"type": "string"},
			"state":   map[string]any{"type": "string"},
		},
		Required: []string{},
	},
	{
		Name:        "hub_report",
		Bundle:      "token",
		Description: "배정받은 일의 보고 — 결과 요약 · 검증. 오케스트레이터 받은편지함에 간다. done 은 바꾸지 않는다 (hub_task_close 가 판정).",
		Properties: map[string]map[string]any{
			"session":      map[string]any{"type": "string"},
			"task_id":      map[string]any{"type": "string"},
			"summary":      map[string]any{"type": "string"},
			"verification": map[string]any{"type": "string"},
			"request_id":   map[string]any{"type": "string", "description": "멱등 키 — 같은 값으로 다시 보내면 처음 결과를 돌려준다"},
		},
		Required: []string{"session", "task_id", "summary"},
	},
	{
		Name:        "hub_orch_declare",
		Bundle:      "token",
		Description: "오케스트레이터 지정 — 승인된 human 소유자만. session = 대상 세션 ID.",
		Properties: map[string]map[string]any{
			"session": map[string]any{"type": "string"},
		},
		Required: []string{"session"},
	},
	{
		Name:        "hub_orch_transfer",
		Bundle:      "token",
		Description: "오케스트레이터 인계 — 승인된 human 소유자만. session = 새 대상.",
		Properties: map[string]map[string]any{
			"session": map[string]any{"type": "string"},
		},
		Required: []string{"session"},
	},
	{
		Name:        "hub_orch_release",
		Bundle:      "token",
		Description: "오케스트레이터 lease 해제 — 소유자 또는 오케스트레이터 세션 자신(session).",
		Properties: map[string]map[string]any{
			"session": map[string]any{"type": "string"},
		},
		Required: []string{},
	},
	{
		Name:        "hub_orch_halt",
		Bundle:      "token",
		Description: "정지 스위치 — 승인된 human 소유자만. on=true 면 새 배정 · 메시지 멈춤, 대기 중 세션에 release.",
		Properties: map[string]map[string]any{
			"on": map[string]any{"type": "boolean"},
		},
		Required: []string{"on"},
	},
	{
		Name:        "hub_orch_assign",
		Bundle:      "token",
		Description: "task 를 세션에 배정 — 오케스트레이터 세션만 (session = 자기 세션 ID). 받은 세션이 hub_inbox_ack(accept) 하면 맡는다.",
		Properties: map[string]map[string]any{
			"session":    map[string]any{"type": "string"},
			"task_id":    map[string]any{"type": "string"},
			"to_session": map[string]any{"type": "string"},
			"note":       map[string]any{"type": "string"},
			"request_id": map[string]any{"type": "string", "description": "멱등 키 — 같은 값으로 다시 보내면 처음 결과를 돌려준다"},
		},
		Required: []string{"session", "task_id", "to_session"},
	},
	{
		Name:        "hub_orch_recall",
		Bundle:      "token",
		Description: "열린 배정 회수 — 오케스트레이터 세션만. 받은 세션에 release.",
		Properties: map[string]map[string]any{
			"session": map[string]any{"type": "string"},
			"task_id": map[string]any{"type": "string"},
			"reason":  map[string]any{"type": "string"},
		},
		Required: []string{"session", "task_id"},
	},
	{
		Name:        "hub_orch_message",
		Bundle:      "token",
		Description: "메시지 — 오케스트레이터 세션만. to = 세션 ID(S-…) 또는 콜사인, kind = note · release.",
		Properties: map[string]map[string]any{
			"session":    map[string]any{"type": "string"},
			"to":         map[string]any{"type": "string"},
			"body":       map[string]any{"type": []string{"string", "object"}},
			"kind":       map[string]any{"type": "string"},
			"request_id": map[string]any{"type": "string", "description": "멱등 키 — 같은 값으로 다시 보내면 처음 결과를 돌려준다"},
		},
		Required: []string{"session", "to", "body"},
	},
	{
		Name:        "hub_relay_invite",
		Bundle:      "token",
		Description: "PC 중계 초대 코드 — 승인된 human 소유자만. 코드는 응답에만 있고 한 번 · 24시간.",
		Properties:  map[string]map[string]any{},
		Required:    []string{},
	},
	{
		Name:        "hub_relay_list",
		Bundle:      "token",
		Description: "이 프로젝트의 PC 중계 — host_id · 이름 · 어댑터 · 마지막 연결.",
		Properties:  map[string]map[string]any{},
		Required:    []string{},
	},
	{
		Name:        "hub_relay_revoke",
		Bundle:      "token",
		Description: "PC 중계 거두기 — 그 중계를 초대한 owner 만.",
		Properties: map[string]map[string]any{
			"host_id": map[string]any{"type": "string"},
		},
		Required: []string{"host_id"},
	},
	{
		Name:        "hub_orch_request_session",
		Bundle:      "token",
		Description: "PC 중계에 새 세션 요청 — 오케스트레이터 세션만, owner 승인 뒤 실행. dir_alias 는 그 PC 허용 목록의 별칭.",
		Properties: map[string]map[string]any{
			"session":         map[string]any{"type": "string"},
			"host_id":         map[string]any{"type": "string"},
			"dir_alias":       map[string]any{"type": "string"},
			"harness":         map[string]any{"type": "string"},
			"permission_mode": map[string]any{"type": "string"},
			"prompt":          map[string]any{"type": "string"},
			"request_id":      map[string]any{"type": "string", "description": "멱등 키 — 같은 값으로 다시 보내면 처음 결과를 돌려준다"},
		},
		Required: []string{"session", "host_id", "dir_alias", "harness"},
	},
	{
		Name:        "hub_orch_request_stop",
		Bundle:      "token",
		Description: "중계가 띄운 세션의 멈춤 요청 — 오케스트레이터 세션만, owner 승인 뒤 실행.",
		Properties: map[string]map[string]any{
			"session":        map[string]any{"type": "string"},
			"target_session": map[string]any{"type": "string"},
			"reason":         map[string]any{"type": "string"},
		},
		Required: []string{"session", "target_session"},
	},
	{
		Name:        "hub_approval_decide",
		Bundle:      "token",
		Description: "세션 · 멈춤 요청 승인 — 승인된 human 소유자만. decision = approve · reject.",
		Properties: map[string]map[string]any{
			"request_id": map[string]any{"type": "string"},
			"decision":   map[string]any{"type": "string"},
			"note":       map[string]any{"type": "string"},
		},
		Required: []string{"request_id", "decision"},
	},
	{
		Name:        "hub_events",
		Bundle:      "token",
		Description: "이력 (누가 · 언제 · 무엇 · 이전 값 · 새 값).",
		Properties: map[string]map[string]any{
			"target_kind": map[string]any{"type": "string"},
			"target_id":   map[string]any{"type": "string"},
			"after_seq":   map[string]any{"type": "integer"},
			"limit":       map[string]any{"type": "integer"},
		},
		Required: []string{},
	},
}

// Tools maps tool names to their specifications.
var Tools = func() map[string]*ToolSpec {
	m := make(map[string]*ToolSpec, len(ToolOrder))
	for _, t := range ToolOrder {
		m[t.Name] = t
	}
	return m
}()
