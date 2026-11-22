package judge

import (
	"bytes"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"strings"
	"testing"
)

func b64(s string) string {
	return base64.StdEncoding.EncodeToString([]byte(s))
}

func makeResponseMD(taskID, digest, responder, receivedAt string, decisions []string, extraHeader string) string {
	var b strings.Builder
	b.WriteString("---\n")
	b.WriteString("format: workflow-kit-plan-response/1\n")
	b.WriteString("task: " + taskID + "\n")
	b.WriteString("plan_digest: " + digest + "\n")
	b.WriteString("responder: " + responder + "\n")
	b.WriteString("role: approver\n")
	b.WriteString("received_at: " + receivedAt + "\n")
	if extraHeader != "" {
		b.WriteString(extraHeader + "\n")
	}
	b.WriteString("---\n\n## Decisions\n\n")
	for _, d := range decisions {
		b.WriteString(d + "\n")
	}
	return b.String()
}

func TestCLIProtocolErrorsAndBatch(t *testing.T) {
	cases := []struct {
		name string
		args []string
		in   string
		code string
	}{
		{"no_op", nil, "", "invalid_args"},
		{"bad_flag", []string{"--nope", "plan.lint"}, "", "invalid_args"},
		{"unknown_op", []string{"bogus.op"}, `{"protocol":"judge/1","input":{}}`, "unknown_op"},
		{"bad_json", []string{"task.status"}, "{bad", "invalid_json"},
		{"unknown_env_key", []string{"task.status"}, `{"protocol":"judge/1","input":{"operation_type":"update"},"extra":1}`, "unknown_field"},
		{"bad_proto", []string{"task.status"}, `{"protocol":"judge/0","input":{"operation_type":"update"}}`, "protocol_mismatch"},
		{"unknown_input_key", []string{"task.status"}, `{"protocol":"judge/1","input":{"operation_type":"update","foo":"bar"}}`, "unknown_field"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			var out, errBuf bytes.Buffer
			rc := Main(tc.args, strings.NewReader(tc.in), &out, &errBuf)
			if rc != 2 {
				t.Fatalf("got rc=%d, want 2 (out=%s)", rc, out.String())
			}
			var got map[string]any
			if err := json.Unmarshal(out.Bytes(), &got); err != nil {
				t.Fatalf("invalid json error output %q: %v", out.String(), err)
			}
			if got["protocol"] != Protocol || got["error_code"] != tc.code {
				t.Fatalf("got %+v, want protocol=%s code=%s", got, Protocol, tc.code)
			}
		})
	}

	// Batch mode: skips blank lines, emits JSON lines in order, preserves literal '<' and '>' (SetEscapeHTML(false))
	var out, errBuf bytes.Buffer
	batchIn := strings.Join([]string{
		`{"protocol":"judge/1","input":{"operation_type":"create_entry"}}`,
		"",
		`{"protocol":"judge/1","input":{"operation_type":"update","requested_status":"done","validation_result":""}}`,
	}, "\n")
	rc := Main([]string{"task.status", "--batch"}, strings.NewReader(batchIn), &out, &errBuf)
	if rc != 0 {
		t.Fatalf("batch rc=%d out=%s", rc, out.String())
	}
	lines := strings.Split(strings.TrimSpace(out.String()), "\n")
	if len(lines) != 2 {
		t.Fatalf("expected 2 output lines, got %d: %q", len(lines), out.String())
	}
	if strings.Contains(out.String(), `\u003c`) {
		t.Fatalf("HTML characters escaped in output: %s", out.String())
	}
}

func TestPlanLintAllRules(t *testing.T) {
	// L2, L9, L1, L3, L4, L5, L6, L7, L8, L10
	planMD := strings.Join([]string{
		"- Claims: C1 src/foo.py 를 수정 50% 완료",
		"- Claims: C1.2 빠진 1.1",
		"- Claims: C1.2.1 @ main.go:10-20 · fn",
		"- Claims: C1.2.2 @ new: x.go · helper",
		"- Claims: C1.2.3 위치 없는 3단계",
		"- Claims: C2.1 부모 없음; 세미콜론",
		"- Claims: BAD ID",
		"- Decisions: D1 [C1] <첫> 결정? | default: a | options: a = 가; b = 나 | state: proposed",
		"- Claims: C3 나뉜 묶음",
		"- Decisions: D2 [C9] 없는 주장? | default: x | options: x = 하나",
	}, "\n")
	in := fmt.Sprintf(`{"protocol":"judge/1","input":{"plan_md":%q,"criteria":["[C1.2] 확인","[C99] 누락"],"line_counts":{"main.go":15}}}`, planMD)
	env, err := Evaluate("plan.lint", []byte(in))
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	res := env.Result.(PlanLintResult)
	if !res.HasError {
		t.Fatalf("expected HasError=true")
	}
	rules := map[string]int{}
	for _, iss := range res.Issues {
		rules[iss.Rule]++
	}
	for _, wantRule := range []string{"L2", "L3", "L4", "L5", "L6", "L7", "L8", "L9", "L10"} {
		if rules[wantRule] == 0 {
			t.Fatalf("missing rule %s in %+v", wantRule, res.Issues)
		}
	}
}

func TestPlanStatesAndQualify(t *testing.T) {
	planMD := strings.Join([]string{
		"- Claims: C1 설계",
		"- Decisions: D1 [C1] 저장소? | default: sqlite | options: sqlite = 파일; pg = 서버 | state: proposed",
		"- Decisions: D2 [C1] 캐시? | default: none | options: none = 없음; mem = 메모리 | state: answered:mem",
	}, "\n")
	plan := ParsePlan(splitPyLines(planMD))
	digest := PlanDigest(plan)
	taskID := "TASK-2026-11-22-main-001"

	rOld := makeResponseMD(taskID, digest, "yklee", "2026-11-22T09:00:00+09:00", []string{
		"- D1 [C1] value: sqlite | default: sqlite | opened: no",
		"- D2 [C1] value: mem | default: none | opened: yes",
	}, "")
	rNew := makeResponseMD(taskID, digest, "yklee", "2026-11-22T10:00:00+09:00", []string{
		"- D1 [C1] value: sqlite | default: sqlite | opened: yes",
		"- D2 [C1] value: mem | default: none | opened: yes",
	}, "")
	rBad := makeResponseMD("TASK-OTHER", digest, "alice", "2026-11-22T10:00:00+09:00", nil, "")

	payload := map[string]any{
		"protocol": Protocol,
		"input": map[string]any{
			"plan_md": planMD,
			"task_id": taskID,
			"responses": []any{
				map[string]any{"name": "r1.md", "bytes_b64": b64(rOld)},
				map[string]any{"name": "r2.md", "bytes_b64": b64(rNew)},
				map[string]any{"name": "r3.md", "bytes_b64": b64(rBad)},
			},
		},
	}
	raw, _ := json.Marshal(payload)
	env, err := Evaluate("plan.states", raw)
	if err != nil {
		t.Fatalf("Evaluate failed: %v", err)
	}
	res := env.Result.(PlanStatesResult)
	if res.States["D1"] != StateKept || res.States["D2"] != "answered:mem" {
		t.Fatalf("unexpected states: %+v", res.States)
	}
	if len(res.Open) != 0 {
		t.Fatalf("expected 0 open decisions, got %v", res.Open)
	}
	if len(res.SupersededResponses) != 1 || res.SupersededResponses[0] != "r1.md" {
		t.Fatalf("expected r1.md superseded, got %v", res.SupersededResponses)
	}
	if res.Verdicts[2].Eligible || *res.Verdicts[2].Stage != 3 {
		t.Fatalf("expected r3.md rejected at stage 3, got %+v", res.Verdicts[2])
	}
}

func TestWbsGateAllCodes(t *testing.T) {
	indexActive := `# Roadmap
## Milestones
- **M-001** [concept] 컨셉 — status: done
  - path: [` + "`./M-001-concept.md`" + `](./M-001-concept.md)
- **M-002** [design] 설계 — status: in_progress
  - path: [` + "`./M-002-design.md`" + `](./M-002-design.md)
- **M-003** [implementation] 구현 — status: planned
  - path: [` + "`./M-003-impl.md`" + `](./M-003-impl.md)
`
	m1 := "---\nid: M-001\ntitle: 컨셉\nsdlc_phase: concept\nstatus: done\norder: 1\nparallel_allowed: []\ndeliverables: []\n---\n\n## WBS\n\n- **WBS-1.1** 노트\n"
	m2 := "---\nid: M-002\ntitle: 설계\nsdlc_phase: design\nstatus: in_progress\norder: 2\nparallel_allowed: []\ndeliverables: []\n---\n\n## WBS\n\n- **WBS-2.1** 설계\n  - **WBS-2.1.1** ADR\n- **WBS-2.2** 리뷰\n"
	m3 := "---\nid: M-003\ntitle: 구현\nsdlc_phase: implementation\nstatus: planned\norder: 3\nparallel_allowed: [M-002]\ndeliverables: []\n---\n\n## WBS\n\n- **WBS-3.1** 코드\n"

	docs := map[string]any{"index.md": indexActive, "M-001-concept.md": m1, "M-002-design.md": m2, "M-003-impl.md": m3}
	evalGate := func(in map[string]any) WbsGateVerdict {
		raw, _ := json.Marshal(map[string]any{"protocol": Protocol, "input": in})
		env, err := Evaluate("wbs.gate", raw)
		if err != nil {
			t.Fatalf("Evaluate wbs.gate error: %v", err)
		}
		return env.Result.(WbsGateVerdict)
	}

	if v := evalGate(map[string]any{"roadmap_docs": nil}); !v.Allowed || v.Code != "not_applicable" {
		t.Fatalf("got %+v", v)
	}
	draftDocs := map[string]any{"index.md": "- 상태: draft\n" + indexActive, "M-001-concept.md": m1}
	if v := evalGate(map[string]any{"roadmap_docs": draftDocs}); !v.Allowed || v.Code != "draft_roadmap" {
		t.Fatalf("got %+v", v)
	}
	if v := evalGate(map[string]any{"roadmap_docs": docs}); v.Allowed || v.Code != "wbs_required" {
		t.Fatalf("got %+v", v)
	}
	if v := evalGate(map[string]any{"roadmap_docs": docs, "wbs": "exempt", "exempt_reason": " "}); v.Allowed || v.Code != "exempt_reason_required" {
		t.Fatalf("got %+v", v)
	}
	if v := evalGate(map[string]any{"roadmap_docs": docs, "wbs": "exempt", "exempt_reason": "긴급"}); !v.Allowed || v.Code != "exempt_declared" {
		t.Fatalf("got %+v", v)
	}
	if v := evalGate(map[string]any{"roadmap_docs": docs, "wbs": "bad"}); v.Allowed || v.Code != "wbs_ref_format" {
		t.Fatalf("got %+v", v)
	}
	if v := evalGate(map[string]any{"roadmap_docs": docs, "wbs": "M-002/WBS-2.1"}); v.Allowed || v.Code != "wbs_not_leaf" {
		t.Fatalf("got %+v", v)
	}
	if v := evalGate(map[string]any{"roadmap_docs": docs, "wbs": "M-002/WBS-2.9"}); v.Allowed || v.Code != "wbs_dangling" {
		t.Fatalf("got %+v", v)
	}
	if v := evalGate(map[string]any{"roadmap_docs": docs, "wbs": "M-001/WBS-1.1"}); v.Allowed || v.Code != "milestone_done" {
		t.Fatalf("got %+v", v)
	}
	if v := evalGate(map[string]any{"roadmap_docs": docs, "wbs": "M-002/WBS-2.1.1"}); !v.Allowed || v.Code != "linked" {
		t.Fatalf("got %+v", v)
	}
	if v := evalGate(map[string]any{"roadmap_docs": docs, "wbs": "M-003/WBS-3.1"}); !v.Allowed || v.Code != "linked" {
		t.Fatalf("expected parallel_allowed M-003 -> linked, got %+v", v)
	}
	m3NoParallel := strings.ReplaceAll(m3, "parallel_allowed: [M-002]", "parallel_allowed: []")
	docsBlock := map[string]any{"index.md": indexActive, "M-001-concept.md": m1, "M-002-design.md": m2, "M-003-impl.md": m3NoParallel}
	if v := evalGate(map[string]any{"roadmap_docs": docsBlock, "wbs": "M-003/WBS-3.1"}); v.Allowed || v.Code != "sdlc_order" {
		t.Fatalf("got %+v", v)
	}
}

func TestRoadmapDeriveAndPyFloat(t *testing.T) {
	indexMD := `# Roadmap
## Milestones
- **M-001** [concept] 컨셉 — status: done
  - path: [` + "`./M-001-concept.md`" + `](./M-001-concept.md)
- **M-002** [design] 설계 — status: in_progress
  - path: [` + "`./M-002-design.md`" + `](./M-002-design.md)
`
	m1 := "---\nid: M-001\ntitle: 컨셉\nsdlc_phase: concept\nstatus: done\norder: 1\nparallel_allowed: []\ndeliverables: [docs/a.md]\n---\n\n## WBS\n\n- **WBS-1.1** 노트\n"
	m2 := "---\nid: M-002\ntitle: 설계\nsdlc_phase: design\nstatus: in_progress\norder: 2\nparallel_allowed: []\ndeliverables: []\n---\n\n## WBS\n\n- **WBS-2.1** 설계\n- **WBS-2.2** 리뷰\n"
	links := []any{
		map[string]any{"task_id": "T1", "task_status": "done", "wbs_ref": "M-001/WBS-1.1", "source_path": "T1.md"},
		map[string]any{"task_id": "T2", "task_status": "done", "wbs_ref": "M-002/WBS-2.1", "source_path": "T2.md"},
		map[string]any{"task_id": "T3", "task_status": "exempt", "wbs_ref": "exempt", "exempt_reason": "", "source_path": "T3.md"},
	}
	payload := map[string]any{
		"protocol": Protocol,
		"input": map[string]any{
			"roadmap_docs": map[string]any{"index.md": indexMD, "M-001-concept.md": m1, "M-002-design.md": m2},
			"links":        links,
			"deliverables": map[string]any{"docs/a.md": true},
			"generated_at": "2026-11-22",
		},
	}
	raw, _ := json.Marshal(payload)
	env, err := Evaluate("roadmap.derive", raw)
	if err != nil {
		t.Fatalf("Evaluate roadmap.derive error: %v", err)
	}
	outBytes, err := canonicalJSON(env)
	if err != nil {
		t.Fatalf("canonicalJSON error: %v", err)
	}
	outStr := string(outBytes)
	if !strings.Contains(outStr, `"progress":1.0`) || !strings.Contains(outStr, `"progress":0.5`) {
		t.Fatalf("expected Python float format 1.0 and 0.5 in %s", outStr)
	}
	if !strings.Contains(outStr, `"current_milestone_id":"M-002"`) {
		t.Fatalf("expected current_milestone_id=M-002 in %s", outStr)
	}
	if !strings.Contains(outStr, `"code":"exempt_without_reason"`) {
		t.Fatalf("expected exempt_without_reason in %s", outStr)
	}
}

func TestHandoffParseAndStateBuild(t *testing.T) {
	handoffText := `# Session Handoff
- 관련 문서: [state.json](./state.json), [profile](../../../../docs/PROJECT_PROFILE.md)
## 1. 현재 작업 요약
- 현재 기준선: 기준선 텍스트
- 현재 주 작업 축: 축 텍스트
- 주요 제약: ` + "`제약1`" + `
## 2. 진행 중 작업
- 현재 ` + "`in_progress`" + ` 작업:
- TASK-2026-11-22-main-001 진행 작업
## 4. 최근 완료 작업
- 최근 완료 작업 목록:
-
`
	res := ParseHandoffText(handoffText, "session_handoff.md")
	if res.CurrentBaseline == nil || *res.CurrentBaseline != "기준선 텍스트" {
		t.Fatalf("unexpected baseline: %v", res.CurrentBaseline)
	}
	if len(res.NextDocuments) != 2 || res.NextDocuments[0] != "state.json" {
		t.Fatalf("unexpected next_documents: %+v", res.NextDocuments)
	}

	task1 := "---\nid: TASK-2026-11-22-main-001\nstatus: in_progress\ncreated_at: 2026-11-22\n---\n\n# TASK-2026-11-22-main-001 — 진행 작업\n\n## 🧭 Plan\n\n- Claims: C1 주장\n- Decisions: D1 [C1] 질문? | default: a | options: a = 가; b = 나 | state: proposed\n"
	task2 := "---\nid: TASK-2026-11-22-main-002\nstatus: done\ncreated_at: 2026-11-22\n---\n\n# TASK-2026-11-22-main-002 — 완료 작업\n"
	daily := "# Backlog Index\n\n- **TASK-2026-11-22-main-001** [generic] 진행 작업\n  - path: [`./tasks/TASK-2026-11-22-main-001.md`](./tasks/TASK-2026-11-22-main-001.md)\n  - status: in_progress\n- **TASK-2026-11-22-main-002** [generic] 완료 작업\n  - path: [`./tasks/TASK-2026-11-22-main-002.md`](./tasks/TASK-2026-11-22-main-002.md)\n  - status: done\n"
	files := map[string]string{
		"docs/PROJECT_PROFILE.md": "# Profile\n- 프로젝트명: TestProj\n- 문서 위키 홈: docs/index.md\n",
		"ai-workflow/memory/active/PURPOSE.md": "---\nlast_purpose_review: 2026-11-21\n---\n## 1. Goals\n- **G1**: 목표 1\n",
		"ai-workflow/memory/active/main/session_handoff.md":                        handoffText,
		"ai-workflow/memory/active/main/backlog/2026-11-22.md":                     daily,
		"ai-workflow/memory/active/main/backlog/tasks/TASK-2026-11-22-main-001.md": task1,
		"ai-workflow/memory/active/main/backlog/tasks/TASK-2026-11-22-main-002.md": task2,
	}
	st, err := BuildWorkflowStatePayload(files, "2026-11-22")
	if err != nil {
		t.Fatalf("BuildWorkflowStatePayload error: %v", err)
	}
	od, ok := st["open_decisions"].(map[string]int)
	if !ok || od["TASK-2026-11-22-main-001"] != 1 {
		t.Fatalf("unexpected open_decisions: %+v", st["open_decisions"])
	}
}
