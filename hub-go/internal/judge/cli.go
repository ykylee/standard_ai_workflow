package judge

import (
	"bufio"
	"bytes"
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"sort"
	"strings"
)

const Protocol = "judge/1"

type cliError struct {
	Code    string
	Message string
}

func (e *cliError) Error() string { return e.Message }

type errEnvelope struct {
	ErrorCode string `json:"error_code"`
	Message   string `json:"message"`
	Protocol  string `json:"protocol"`
}

type okEnvelope struct {
	Op       string `json:"op"`
	Protocol string `json:"protocol"`
	Result   any    `json:"result"`
}

func canonicalJSON(v any) ([]byte, error) {
	var buf bytes.Buffer
	enc := json.NewEncoder(&buf)
	enc.SetEscapeHTML(false)
	if err := enc.Encode(v); err != nil {
		return nil, err
	}
	return bytes.TrimRight(buf.Bytes(), "\n"), nil
}

func writeJSONLine(w io.Writer, v any) {
	b, err := canonicalJSON(v)
	if err != nil {
		b = []byte(`{"error_code":"internal_error","message":"marshal failed","protocol":"judge/1"}`)
	}
	_, _ = w.Write(b)
	_, _ = w.Write([]byte("\n"))
}

func writeErr(w io.Writer, code, msg string) {
	writeJSONLine(w, errEnvelope{
		ErrorCode: code,
		Message:   msg,
		Protocol:  Protocol,
	})
}

func checkAllowedKeys(m map[string]any, allowed []string, where string) error {
	set := make(map[string]bool, len(allowed))
	for _, k := range allowed {
		set[k] = true
	}
	var extra []string
	for k := range m {
		if !set[k] {
			extra = append(extra, k)
		}
	}
	if len(extra) > 0 {
		sort.Strings(extra)
		return &cliError{
			Code:    "unknown_field",
			Message: fmt.Sprintf("%s 에 모르는 필드: %s", where, strings.Join(extra, ", ")),
		}
	}
	return nil
}

func reqStr(m map[string]any, key string) (string, error) {
	raw, exists := m[key]
	if !exists || raw == nil {
		return "", &cliError{Code: "invalid_input", Message: fmt.Sprintf("%s 는 문자열이어야 한다", key)}
	}
	s, ok := raw.(string)
	if !ok {
		return "", &cliError{Code: "invalid_input", Message: fmt.Sprintf("%s 는 문자열이어야 한다", key)}
	}
	return s, nil
}

func optStr(m map[string]any, key string) (*string, error) {
	raw, exists := m[key]
	if !exists || raw == nil {
		return nil, nil
	}
	s, ok := raw.(string)
	if !ok {
		return nil, &cliError{Code: "invalid_input", Message: fmt.Sprintf("%s 는 문자열 또는 null 이어야 한다", key)}
	}
	return &s, nil
}

func runPlanLint(inp map[string]any) (any, error) {
	if err := checkAllowedKeys(inp, []string{"plan_md", "criteria", "line_counts"}, "input"); err != nil {
		return nil, err
	}
	planMD, err := reqStr(inp, "plan_md")
	if err != nil {
		return nil, err
	}
	criteria := make([]string, 0)
	if rawCrit, exists := inp["criteria"]; exists && rawCrit != nil {
		arr, ok := rawCrit.([]any)
		if !ok {
			return nil, &cliError{Code: "invalid_input", Message: "criteria 는 문자열 목록이어야 한다"}
		}
		for _, item := range arr {
			s, ok := item.(string)
			if !ok {
				return nil, &cliError{Code: "invalid_input", Message: "criteria 는 문자열 목록이어야 한다"}
			}
			criteria = append(criteria, s)
		}
	}

	var counter LineCounter
	if rawCounts, exists := inp["line_counts"]; exists && rawCounts != nil {
		m, ok := rawCounts.(map[string]any)
		if !ok {
			return nil, &cliError{Code: "invalid_input", Message: "line_counts 는 객체 또는 null 이어야 한다"}
		}
		counts := make(map[string]*int, len(m))
		for k, v := range m {
			if v == nil {
				counts[k] = nil
				continue
			}
			num, ok := v.(json.Number)
			if !ok {
				return nil, &cliError{Code: "invalid_input", Message: fmt.Sprintf("line_counts[%q] 는 정수 또는 null 이어야 한다", k)}
			}
			iv, err := num.Int64()
			if err != nil {
				return nil, &cliError{Code: "invalid_input", Message: fmt.Sprintf("line_counts[%q] 는 정수 또는 null 이어야 한다", k)}
			}
			c := int(iv)
			counts[k] = &c
		}
		counter = func(path string) (int, bool) {
			p, ok := counts[path]
			if !ok || p == nil {
				return 0, false
			}
			return *p, true
		}
	}

	plan := ParsePlan(splitPyLines(planMD))
	issues := LintPlan(plan, criteria, counter)
	issueOut := make([]LintIssueJSON, 0, len(issues))
	for _, iss := range issues {
		issueOut = append(issueOut, LintIssueJSON{
			Message:  iss.Message,
			Ref:      iss.Ref,
			Rule:     iss.Rule,
			Severity: iss.Severity,
		})
	}
	return PlanLintResult{
		Digest:        PlanDigest(plan),
		HasError:      HasErrorRules(plan),
		Issues:        issueOut,
		OpenColumnIDs: ColumnOpenDecisionIDs(plan),
	}, nil
}

func runPlanStates(inp map[string]any) (any, error) {
	if err := checkAllowedKeys(inp, []string{"plan_md", "task_id", "responses"}, "input"); err != nil {
		return nil, err
	}
	planMD, err := reqStr(inp, "plan_md")
	if err != nil {
		return nil, err
	}
	taskID, err := reqStr(inp, "task_id")
	if err != nil {
		return nil, err
	}
	var rawResps []any
	if raw, exists := inp["responses"]; exists && raw != nil {
		arr, ok := raw.([]any)
		if !ok {
			return nil, &cliError{Code: "invalid_input", Message: "responses 는 목록이어야 한다"}
		}
		rawResps = arr
	}

	plan := ParsePlan(splitPyLines(planMD))
	hasErr := HasErrorRules(plan)
	verdicts := make([]ResponseVerdictJSON, 0, len(rawResps))
	qualified := make([]Response, 0, len(rawResps))

	for idx, itemRaw := range rawResps {
		item, ok := itemRaw.(map[string]any)
		if !ok || item == nil {
			return nil, &cliError{Code: "invalid_input", Message: fmt.Sprintf("responses[%d] 는 객체여야 한다", idx)}
		}
		if err := checkAllowedKeys(item, []string{"name", "bytes_b64"}, fmt.Sprintf("responses[%d]", idx)); err != nil {
			return nil, err
		}
		name := ""
		if rawName, exists := item["name"]; exists && rawName != nil {
			s, ok := rawName.(string)
			if !ok {
				return nil, &cliError{Code: "invalid_input", Message: "name 는 문자열이어야 한다"}
			}
			name = s
		}
		b64, err := reqStr(item, "bytes_b64")
		if err != nil {
			return nil, err
		}
		data, err := base64.StdEncoding.DecodeString(b64)
		if err != nil {
			return nil, &cliError{Code: "invalid_input", Message: fmt.Sprintf("responses[%d].bytes_b64 base64 오류: %v", idx, err)}
		}
		if hasErr {
			s0 := 0
			verdicts = append(verdicts, ResponseVerdictJSON{
				Eligible: false,
				Name:     name,
				Reason:   "task 계획이 오류 규칙(L2 · L6 · L9)을 어긴 상태다",
				Stage:    &s0,
			})
			continue
		}
		parsed := ParseResponse(data, name)
		v := Qualify(parsed, plan, taskID)
		verdicts = append(verdicts, ResponseVerdictJSON{
			Eligible: v.Eligible(),
			Name:     name,
			Reason:   v.Reason,
			Stage:    v.Stage,
		})
		if v.Eligible() {
			qualified = append(qualified, AsResponse(parsed))
		}
	}

	st := ComputeStates(plan, qualified)
	disputed := st.DisputedResponses
	if disputed == nil {
		disputed = make([]string, 0)
	}
	superseded := st.SupersededResponses
	if superseded == nil {
		superseded = make([]string, 0)
	}
	openIDs := OpenDecisionIDs(plan, qualified)
	return PlanStatesResult{
		Digest:              PlanDigest(plan),
		DisputedResponses:   disputed,
		HasError:            hasErr,
		Open:                openIDs,
		States:              st.States,
		SupersededResponses: superseded,
		Verdicts:            verdicts,
	}, nil
}

func runTaskStatus(inp map[string]any) (any, error) {
	if err := checkAllowedKeys(
		inp,
		[]string{"requested_status", "validation_result", "operation_type", "current_status", "recorded_validation"},
		"input",
	); err != nil {
		return nil, err
	}
	opType, err := reqStr(inp, "operation_type")
	if err != nil {
		return nil, err
	}
	reqStatus, err := optStr(inp, "requested_status")
	if err != nil {
		return nil, err
	}
	valRes, err := optStr(inp, "validation_result")
	if err != nil {
		return nil, err
	}
	curStatus, err := optStr(inp, "current_status")
	if err != nil {
		return nil, err
	}
	recVal, err := optStr(inp, "recorded_validation")
	if err != nil {
		return nil, err
	}
	status, warnings := DetermineConservativeTaskStatus(reqStatus, valRes, opType, curStatus, recVal)
	return TaskStatusResult{
		Status:   status,
		Warnings: warnings,
	}, nil
}

var ops = map[string]func(map[string]any) (any, error){
	"plan.lint":   runPlanLint,
	"plan.states": runPlanStates,
	"task.status": runTaskStatus,
}

func Evaluate(op string, raw []byte) (okEnvelope, error) {
	handler, ok := ops[op]
	if !ok {
		return okEnvelope{}, &cliError{Code: "unknown_op", Message: "모르는 op: " + op}
	}
	dec := json.NewDecoder(bytes.NewReader(raw))
	dec.UseNumber()
	var env map[string]any
	if err := dec.Decode(&env); err != nil {
		return okEnvelope{}, &cliError{Code: "invalid_json", Message: fmt.Sprintf("입력이 JSON 이 아니다: %v", err)}
	}
	var trailing any
	if err := dec.Decode(&trailing); !errors.Is(err, io.EOF) {
		return okEnvelope{}, &cliError{Code: "invalid_json", Message: "입력 JSON 뒤에 남은 내용이 있다"}
	}
	if env == nil {
		return okEnvelope{}, &cliError{Code: "invalid_input", Message: "최상위 입력은 JSON 객체여야 한다"}
	}
	if err := checkAllowedKeys(env, []string{"protocol", "input"}, "요청"); err != nil {
		return okEnvelope{}, err
	}
	if proto, _ := env["protocol"].(string); proto != Protocol {
		return okEnvelope{}, &cliError{Code: "protocol_mismatch", Message: fmt.Sprintf("protocol 은 %s 이어야 한다", Protocol)}
	}
	inp, ok := env["input"].(map[string]any)
	if !ok || inp == nil {
		return okEnvelope{}, &cliError{Code: "invalid_input", Message: "input 은 JSON 객체여야 한다"}
	}
	res, err := handler(inp)
	if err != nil {
		return okEnvelope{}, err
	}
	return okEnvelope{
		Op:       op,
		Protocol: Protocol,
		Result:   res,
	}, nil
}

func Main(args []string, stdin io.Reader, stdout, _stderr io.Writer) int {
	batch := false
	var pos []string
	for _, a := range args {
		if a == "--batch" {
			batch = true
		} else if strings.HasPrefix(a, "-") {
			writeErr(stdout, "invalid_args", "알 수 없는 옵션: "+a)
			return 2
		} else {
			pos = append(pos, a)
		}
	}
	if len(pos) != 1 {
		writeErr(stdout, "invalid_args", "사용법: workflow-hub judge <op> [--batch]")
		return 2
	}
	op := pos[0]
	if _, ok := ops[op]; !ok {
		writeErr(stdout, "unknown_op", "모르는 op: "+op)
		return 2
	}

	if !batch {
		raw, err := io.ReadAll(stdin)
		if err != nil {
			writeErr(stdout, "io_error", err.Error())
			return 2
		}
		out, err := Evaluate(op, raw)
		if err != nil {
			var ce *cliError
			if errors.As(err, &ce) {
				writeErr(stdout, ce.Code, ce.Message)
			} else {
				writeErr(stdout, "internal_error", err.Error())
			}
			return 2
		}
		writeJSONLine(stdout, out)
		return 0
	}

	sc := bufio.NewScanner(stdin)
	sc.Buffer(make([]byte, 0, 64*1024), 16*1024*1024)
	for sc.Scan() {
		line := strings.TrimSpace(sc.Text())
		if line == "" {
			continue
		}
		out, err := Evaluate(op, []byte(line))
		if err != nil {
			var ce *cliError
			if errors.As(err, &ce) {
				writeErr(stdout, ce.Code, ce.Message)
			} else {
				writeErr(stdout, "internal_error", err.Error())
			}
			return 2
		}
		writeJSONLine(stdout, out)
	}
	if err := sc.Err(); err != nil {
		writeErr(stdout, "io_error", err.Error())
		return 2
	}
	return 0
}
