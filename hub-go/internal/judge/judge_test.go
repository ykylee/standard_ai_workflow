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
