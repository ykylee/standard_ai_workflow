package tools

import (
	"database/sql"
	"errors"
	"fmt"
	"regexp"
	"sort"
	"strings"
	"unicode"

	"github.com/ykylee/standard_ai_workflow/hub-go/internal/db"
	"github.com/ykylee/standard_ai_workflow/hub-go/internal/judge"
	"github.com/ykylee/standard_ai_workflow/hub-go/internal/store"
)

const (
	roadmapIndexFile = "index.md"
	l5Unmeasured     = "L5 (계획 파일의 줄 수) 는 허브에 작업 트리가 없어 재지 않았다 — 미측정"
)

var (
	milestoneNameRe  = regexp.MustCompile(`^M-\d{3}-[a-z0-9][a-z0-9-]*\.md$`)
	decisionPrefixes = []string{"- 결정:", "- Decisions:"}
	doneCriteriaPref = []string{"- 완료 기준:", "- Done criteria:", "- Completion criteria:"}
	planFilesPref    = []string{"- 바뀌는 파일:", "- Files that change:"}
	blankLetters     = map[rune]bool{
		'\u3164':     true,
		'\u1160':     true,
		'\u115f':     true,
		'\uffa0':     true,
		'\U00013441': true,
		'\U00013442': true,
	}
)

// JudgeBridge connects hub store transactions with the pure judge package.
type JudgeBridge struct {
	Store *store.Store
}

func gateError(code, message string, warnings []string) *store.HubError {
	if warnings == nil {
		warnings = []string{}
	}
	return &store.HubError{
		Status:  422,
		Code:    "gate_denied",
		Message: message,
		Detail: map[string]any{
			"kit_error_code": code,
			"warnings":       warnings,
		},
	}
}

func splitLinesPy(s string) []string {
	if s == "" {
		return []string{}
	}
	norm := strings.ReplaceAll(s, "\r\n", "\n")
	norm = strings.ReplaceAll(norm, "\r", "\n")
	norm = strings.TrimSuffix(norm, "\n")
	if norm == "" {
		return []string{""}
	}
	return strings.Split(norm, "\n")
}

func extractDoneCriteria(fields map[string]any) []string {
	if fields == nil {
		return nil
	}
	raw, ok := fields["done_criteria"]
	if !ok || raw == nil {
		return nil
	}
	switch v := raw.(type) {
	case []string:
		out := make([]string, len(v))
		copy(out, v)
		return out
	case []any:
		out := make([]string, 0, len(v))
		for _, item := range v {
			out = append(out, fmt.Sprint(item))
		}
		return out
	default:
		return nil
	}
}

// TaskLines formats plan_md lines followed by synthetic done_criteria lines matching 1.x task markdown.
func TaskLines(planMD string, fields map[string]any) ([]string, int) {
	lines := splitLinesPy(planMD)
	criteria := extractDoneCriteria(fields)
	for _, c := range criteria {
		lines = append(lines, "- 완료 기준: "+c)
	}
	return lines, len(criteria)
}

func renderLintIssue(iss judge.LintIssue) string {
	head := iss.Rule
	if iss.Ref != "" {
		head += " " + iss.Ref
	}
	return fmt.Sprintf("%s: %s", head, iss.Message)
}

func isReadableNote(note *string) bool {
	if note == nil {
		return false
	}
	for _, r := range *note {
		if (unicode.IsLetter(r) || unicode.IsNumber(r)) && !blankLetters[r] {
			return true
		}
	}
	return false
}

func matchLabelPrefix(stripped string, prefixes []string) (string, bool) {
	for _, p := range prefixes {
		if strings.HasPrefix(stripped, p) {
			return strings.TrimSpace(stripped[len(p):]), true
		}
	}
	return "", false
}

func readTaskListField(lines []string, prefixes []string) []string {
	var values []string
	for idx, line := range lines {
		if _, ok := matchLabelPrefix(strings.TrimSpace(line), prefixes); !ok {
			continue
		}
		for end := idx; end < len(lines); end++ {
			v, ok := matchLabelPrefix(strings.TrimSpace(lines[end]), prefixes)
			if !ok {
				break
			}
			if v != "" {
				values = append(values, v)
			}
		}
		break
	}
	return values
}

func renderDecisionValue(d judge.Decision, state string) string {
	if len(d.Problems) > 0 {
		return d.Raw
	}
	opts := make([]string, len(d.Options))
	for i, opt := range d.Options {
		opts[i] = opt[0] + " = " + opt[1]
	}
	return strings.Join([]string{
		fmt.Sprintf("%s [%s] %s", d.ID, d.ClaimID, d.Question),
		"default: " + d.Default,
		"options: " + strings.Join(opts, "; "),
		"state: " + state,
	}, " | ")
}

type stateChange struct {
	ID  string
	Old string
	New string
}

func rewriteDecisionStates(lines []string, states map[string]string) ([]string, []stateChange) {
	out := make([]string, 0, len(lines))
	var changes []stateChange
	for _, line := range lines {
		val, ok := matchLabelPrefix(strings.TrimSpace(line), decisionPrefixes)
		if !ok || val == "" {
			out = append(out, line)
			continue
		}
		d := judge.ParseDecisionValue(val)
		newState, want := states[d.ID]
		if len(d.Problems) > 0 || !want || newState == d.State {
			out = append(out, line)
			continue
		}
		indentLen := len(line) - len(strings.TrimLeftFunc(line, unicode.IsSpace))
		indent := line[:indentLen]
		out = append(out, fmt.Sprintf("%s- %s: %s", indent, judge.DecisionLabelCanonical, renderDecisionValue(d, newState)))
		changes = append(changes, stateChange{ID: d.ID, Old: d.State, New: newState})
	}
	return out, changes
}

func findDecision(plan judge.Plan, id string) (judge.Decision, bool) {
	for _, d := range plan.Decisions {
		if d.ID == id {
			return d, true
		}
	}
	return judge.Decision{}, false
}

func containsString(items []string, target string) bool {
	for _, item := range items {
		if item == target {
			return true
		}
	}
	return false
}

type queryer interface {
	Query(query string, args ...any) (*sql.Rows, error)
}

func (j *JudgeBridge) loadResponsesForPlan(qe queryer, projectID, taskID string, target judge.Plan) ([]judge.Response, error) {
	rows, err := qe.Query(
		"SELECT body FROM plan_response WHERE project_id = ? AND task_id = ? ORDER BY received_at, rowid",
		projectID, taskID,
	)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var out []judge.Response
	idx := 0
	for rows.Next() {
		var body string
		if err := rows.Scan(&body); err != nil {
			return nil, err
		}
		idx++
		parsed := judge.ParseResponse([]byte(body), fmt.Sprintf("response-%d.md", idx))
		if judge.Qualify(parsed, target, taskID).Eligible() {
			out = append(out, judge.AsResponse(parsed))
		}
	}
	if err := rows.Err(); err != nil {
		return nil, err
	}
	return out, nil
}

// Enforce runs plan linting, decision state recomputation, and state transition gates.
func (j *JudgeBridge) Enforce(
	tx *sql.Tx,
	projectID, taskID string,
	newPlanMD string,
	previousPlanMD *string,
	fields map[string]any,
	requestedStatus *string,
	status string,
	currentStatus *string,
	decisionStates []string,
	removalNote *string,
	creating bool,
) (string, []string, error) {
	lines, tail := TaskLines(newPlanMD, fields)
	var previousLines []string
	if previousPlanMD != nil {
		previousLines, _ = TaskLines(*previousPlanMD, fields)
	}
	planChanged := previousPlanMD == nil || *previousPlanMD != newPlanMD
	if planChanged && strings.TrimSpace(newPlanMD) != "" {
		issues := judge.LintPlan(judge.ParsePlan(lines), extractDoneCriteria(fields), nil)
		var rendered []string
		for _, iss := range issues {
			if iss.Severity == "error" {
				rendered = append(rendered, renderLintIssue(iss))
			}
		}
		if len(rendered) > 0 {
			return "", nil, gateError("plan_lint_error", fmt.Sprintf("주장 · 결정이 오류 규칙을 어긴다 (%d건) — %s", len(rendered), strings.Join(rendered, " / ")), rendered)
		}
	}

	reqStatus := ""
	if requestedStatus != nil {
		reqStatus = *requestedStatus
	}
	curStatus := ""
	if currentStatus != nil {
		curStatus = *currentStatus
	}
	toInProgress := status == "in_progress" && curStatus != "in_progress"
	transition := requestedStatus != nil && reqStatus != curStatus

	plan := judge.ParsePlan(lines)
	prevPlan := judge.Plan{}
	if previousLines != nil {
		prevPlan = judge.ParsePlan(previousLines)
	}

	var warnings []string
	if len(plan.Claims) == 0 && (creating || toInProgress) {
		var codeFiles []string
		for _, v := range readTaskListField(lines, planFilesPref) {
			clean := strings.Trim(strings.TrimSpace(v), "`")
			if !strings.HasPrefix(clean, "ai-workflow/") {
				codeFiles = append(codeFiles, v)
			}
		}
		if len(codeFiles) >= 3 {
			warnings = append(warnings, fmt.Sprintf("Claims 가 없다 — 바뀌는 파일 %d개 (R2.3)", len(codeFiles)))
		}
	}

	if plan.Empty() && prevPlan.Empty() && len(decisionStates) == 0 {
		if len(plan.Claims) > 0 {
			warnings = append(warnings, l5Unmeasured)
		}
		return newPlanMD, warnings, nil
	}

	touched := len(decisionStates) > 0
	requestedStates := map[string]string{}
	for _, item := range decisionStates {
		decID, rawState, hasSep := strings.Cut(item, "=")
		decID = strings.TrimSpace(decID)
		rawState = strings.TrimSpace(rawState)
		dec, foundDec := findDecision(plan, decID)
		kind, val, okState := judge.ParseState(rawState)
		reason := ""
		if !hasSep || !foundDec {
			if hasSep {
				reason = fmt.Sprintf("모르는 결정 `%s`", decID)
			} else {
				reason = "`D<n>=<state>` 꼴이 아니다"
			}
		} else if len(dec.Problems) > 0 {
			reason = fmt.Sprintf("`%s` 줄을 읽을 수 없다 (L6) — 먼저 줄을 고친다", decID)
		} else if !okState || (kind != judge.StateAnswered && kind != judge.StateProposed) {
			reason = fmt.Sprintf("`%s` 는 지정할 수 없다 — `answered:<value>` 또는 `proposed` 만 받는다 (`kept` · `changed` · `unopened` · `disputed` 는 계산만이 만든다)", rawState)
		} else if val != "" && !containsString(dec.OptionValues(), val) {
			reason = fmt.Sprintf("`%s` 은 `%s` 의 선택지(%s)에 없다", val, decID, strings.Join(dec.OptionValues(), ", "))
		}
		if reason != "" {
			return "", nil, gateError("decision_state_rejected", fmt.Sprintf("--decision-state %s: %s", item, reason), nil)
		}
		requestedStates[decID] = rawState
	}
	if len(requestedStates) > 0 {
		lines, _ = rewriteDecisionStates(lines, requestedStates)
		plan = judge.ParsePlan(lines)
	}

	carried := map[string]string{}
	for _, d := range plan.Decisions {
		earlier, ok := findDecision(prevPlan, d.ID)
		if ok && earlier.Answered() && !d.Answered() && len(d.Problems) == 0 {
			if _, explicitlyRequested := requestedStates[d.ID]; !explicitlyRequested {
				carried[d.ID] = earlier.State
			}
		}
	}
	if len(carried) > 0 {
		lines, _ = rewriteDecisionStates(lines, carried)
		plan = judge.ParsePlan(lines)
	}

	criteria := readTaskListField(lines, doneCriteriaPref)
	issues := judge.LintPlan(plan, criteria, nil)
	var renderedErrors []string
	for _, iss := range issues {
		if iss.Severity == "error" {
			renderedErrors = append(renderedErrors, renderLintIssue(iss))
		}
	}
	if len(renderedErrors) > 0 {
		if touched || reqStatus == "done" {
			prefix := ""
			if reqStatus == "done" && !touched {
				prefix = "done 거부: "
			}
			msg := fmt.Sprintf("%s주장 · 결정이 오류 규칙을 어긴다 (%d건) — %s", prefix, len(renderedErrors), strings.Join(renderedErrors, " / "))
			warns := append([]string(nil), renderedErrors...)
			if reqStatus == "done" {
				alsoOpen := judge.OpenDecisionIDs(plan, nil)
				if len(alsoOpen) > 0 {
					warns = append(warns, fmt.Sprintf("열린 결정 %d건 (%s) 도 남아 있다", len(alsoOpen), strings.Join(alsoOpen, ", ")))
				}
			}
			return "", nil, gateError("plan_lint_error", msg, warns)
		}
		warnings = append(warnings, fmt.Sprintf("주장 · 결정이 오류 규칙을 어긴 상태다 (%d건: %s) — 고치기 전에는 결정 상태 칸을 다시 적지 않고, done 전이는 거부된다", len(renderedErrors), renderedErrors[0]))
		if len(plan.Claims) > 0 {
			warnings = append(warnings, l5Unmeasured)
		}
		outLines := lines
		if tail > 0 && len(outLines) >= tail {
			outLines = outLines[:len(outLines)-tail]
		}
		joined := strings.Join(outLines, "\n")
		if strings.HasSuffix(newPlanMD, "\n") {
			joined += "\n"
		}
		return joined, warnings, nil
	}

	if previousLines != nil && !isReadableNote(removalNote) {
		prevResponses, err := j.loadResponsesForPlan(tx, projectID, taskID, prevPlan)
		if err != nil {
			return "", nil, err
		}
		prevOpen := judge.OpenDecisionIDs(prevPlan, prevResponses)
		var removed []string
		for _, id := range prevOpen {
			if _, ok := findDecision(plan, id); !ok {
				removed = append(removed, id)
			}
		}
		if len(removed) > 0 {
			return "", nil, gateError("decision_removal_needs_note", fmt.Sprintf("열린 결정 %d건(%s)을 걷는 쓰기는 같은 호출에 --progress-note 로 사유를 적어야 한다", len(removed), strings.Join(removed, ", ")), nil)
		}
	}

	if touched || transition || creating {
		for _, iss := range issues {
			if iss.Severity == "warning" || iss.Severity == "note" {
				warnings = append(warnings, renderLintIssue(iss))
			}
		}
	}

	if !prevPlan.Empty() && judge.PlanDigest(prevPlan) != judge.PlanDigest(plan) {
		var kept []string
		for _, d := range plan.Decisions {
			earlier, ok := findDecision(prevPlan, d.ID)
			if d.Answered() && ok && earlier.Answered() {
				kept = append(kept, d.ID)
			}
		}
		if len(kept) > 0 {
			warnings = append(warnings, "질문이 바뀌었다 — answered 를 유지했다: "+strings.Join(kept, ", "))
		}
	}

	responses, err := j.loadResponsesForPlan(tx, projectID, taskID, plan)
	if err != nil {
		return "", nil, err
	}
	res := judge.ComputeStates(plan, responses)
	var changes []stateChange
	lines, changes = rewriteDecisionStates(lines, res.States)
	var mismatch []string
	for _, ch := range changes {
		if _, isReq := requestedStates[ch.ID]; isReq {
			continue
		}
		if _, hadPrev := findDecision(prevPlan, ch.ID); !hadPrev {
			continue
		}
		if _, isCarried := carried[ch.ID]; isCarried {
			continue
		}
		mismatch = append(mismatch, fmt.Sprintf("뒷받침 없는 상태를 되돌렸다: %s %s → %s", ch.ID, ch.Old, ch.New))
	}
	plan = judge.ParsePlan(lines)

	openIDs := judge.OpenDecisionIDs(plan, responses)
	if reqStatus == "done" && len(openIDs) > 0 {
		msg := fmt.Sprintf("done 거부: 열린 결정 %d건 (%s). --decision-state %s=answered:<value> 로 답을 기록하거나, --replace-field plan_decisions 로 결정을 걷고 사유를 Progress 에 남긴다.", len(openIDs), strings.Join(openIDs, ", "), openIDs[0])
		return "", nil, gateError("open_decisions", msg, mismatch)
	}
	warnings = append(warnings, mismatch...)
	if toInProgress && len(openIDs) > 0 {
		described := make([]string, len(openIDs))
		for i, id := range openIDs {
			st := res.States[id]
			if st == "" {
				st = judge.StateProposed
			}
			described[i] = fmt.Sprintf("%s %s", id, st)
		}
		warnings = append(warnings, fmt.Sprintf("열린 결정 %d건 (%s) — 묻지 않았거나, 열리지 않았거나, 답이 갈렸다. 기본값은 동의가 아니다.", len(openIDs), strings.Join(described, ", ")))
	}

	outLines := lines
	if tail > 0 && len(outLines) >= tail {
		outLines = outLines[:len(outLines)-tail]
	}
	if len(plan.Claims) > 0 {
		warnings = append(warnings, l5Unmeasured)
	}
	joined := strings.Join(outLines, "\n")
	if strings.HasSuffix(newPlanMD, "\n") && !strings.HasSuffix(joined, "\n") {
		joined += "\n"
	}
	return joined, warnings, nil
}

// LoadRoadmap reads roadmap_doc rows for projectID and assembles the Roadmap.
func (j *JudgeBridge) LoadRoadmap(qe queryer, projectID string) (*judge.Roadmap, bool, []judge.RoadmapIssue, error) {
	rows, err := qe.Query("SELECT path, body_md FROM roadmap_doc WHERE project_id = ?", projectID)
	if err != nil {
		return nil, false, nil, err
	}
	defer rows.Close()
	docs := map[string]string{}
	for rows.Next() {
		var p, body string
		if err := rows.Scan(&p, &body); err != nil {
			return nil, false, nil, err
		}
		docs[p] = body
	}
	if err := rows.Err(); err != nil {
		return nil, false, nil, err
	}
	indexText, ok := docs[roadmapIndexFile]
	if !ok {
		return nil, false, nil, nil
	}
	texts := make(map[string]string, len(docs))
	for k, v := range docs {
		if k != roadmapIndexFile {
			texts[k] = v
		}
	}
	rm, issues := judge.AssembleRoadmap(indexText, texts)
	return rm, judge.IndexTextIsDraft(indexText), issues, nil
}

// WbsGate validates wbs and wbs_exempt_reason against the project's roadmap.
func (j *JudgeBridge) WbsGate(tx *sql.Tx, projectID string, wbs *string, exemptReason *string) (string, error) {
	rm, draft, _, err := j.LoadRoadmap(tx, projectID)
	if err != nil {
		return "", err
	}
	verdict := judge.JudgeWbs(rm, draft, wbs, exemptReason)
	if !verdict.Allowed {
		hint := ` 허브 도구에서는 wbs="M-NNN/WBS-N.N", 로드맵 밖이면 wbs="exempt" 와 wbs_exempt_reason 을 함께 준다.`
		if exemptReason != nil && *exemptReason != "" && (wbs == nil || *wbs == "") {
			hint += ` (wbs_exempt_reason 만 왔다 — wbs="exempt" 가 함께 있어야 로드맵 밖 선언이다)`
		}
		return "", gateError("wbs_gate_denied", fmt.Sprintf("WBS 게이트 거부 (%s): %s%s", verdict.Code, verdict.Detail, hint), []string{verdict.Code})
	}
	return verdict.Code, nil
}

func optStringFromMap(m map[string]any, key string) *string {
	if m == nil {
		return nil
	}
	raw, ok := m[key]
	if !ok || raw == nil {
		return nil
	}
	s, ok := raw.(string)
	if !ok {
		return nil
	}
	if s == "" {
		return nil
	}
	return &s
}

func optStringPreserveEmpty(m map[string]any, key string) *string {
	if m == nil {
		return nil
	}
	raw, ok := m[key]
	if !ok || raw == nil {
		return nil
	}
	s, ok := raw.(string)
	if !ok {
		return nil
	}
	return &s
}

// PrepareCreate enforces WBS gate and plan contract before creating a task.
func (j *JudgeBridge) PrepareCreate(tx *sql.Tx, projectID, taskID string, values map[string]any) (map[string]any, error) {
	if _, err := j.WbsGate(tx, projectID, optStringFromMap(values, "wbs"), optStringPreserveEmpty(values, "wbs_exempt_reason")); err != nil {
		return nil, err
	}
	out := make(map[string]any, len(values))
	for k, v := range values {
		out[k] = v
	}
	planMD, _ := values["plan_md"].(string)
	if strings.TrimSpace(planMD) != "" {
		status := "planned"
		if st, ok := values["status"].(string); ok && st != "" {
			status = st
		}
		fields, _ := values["fields"].(map[string]any)
		if fields == nil {
			fields = map[string]any{}
		}
		stCopy := status
		enforced, _, err := j.Enforce(tx, projectID, taskID, planMD, nil, fields, &stCopy, status, nil, nil, nil, true)
		if err != nil {
			return nil, err
		}
		out["plan_md"] = enforced
	}
	return out, nil
}

// PrepareUpdate returns a callback enforcing WBS gate and plan contract before updating a task.
func (j *JudgeBridge) PrepareUpdate(projectID string, decisionStates map[string]string, note *string) store.PrepareUpdateFn {
	dsArgs := make([]string, 0, len(decisionStates))
	keys := make([]string, 0, len(decisionStates))
	for k := range decisionStates {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	for _, k := range keys {
		dsArgs = append(dsArgs, fmt.Sprintf("%s=%s", k, decisionStates[k]))
	}
	return func(tx *sql.Tx, before, values map[string]any) (map[string]any, error) {
		out := make(map[string]any, len(values))
		for k, v := range values {
			out[k] = v
		}
		_, hasWbs := values["wbs"]
		_, hasEx := values["wbs_exempt_reason"]
		if hasWbs || hasEx {
			var wbsPtr *string
			if hasWbs {
				wbsPtr = optStringFromMap(values, "wbs")
			} else {
				wbsPtr = optStringFromMap(before, "wbs")
			}
			var exPtr *string
			if hasEx {
				exPtr = optStringPreserveEmpty(values, "wbs_exempt_reason")
			} else {
				exPtr = optStringPreserveEmpty(before, "wbs_exempt_reason")
			}
			if _, err := j.WbsGate(tx, projectID, wbsPtr, exPtr); err != nil {
				return nil, err
			}
		}

		beforePlan, _ := before["plan_md"].(string)
		newPlan := beforePlan
		_, hasNewPlan := values["plan_md"]
		if hasNewPlan {
			newPlan, _ = values["plan_md"].(string)
		}
		beforeStatus, _ := before["status"].(string)
		reqStatusPtr := optStringPreserveEmpty(values, "status")
		status := beforeStatus
		if reqStatusPtr != nil {
			status = *reqStatusPtr
		}
		statusChange := hasNewStatus(values, beforeStatus)
		if (strings.TrimSpace(newPlan) != "" || strings.TrimSpace(beforePlan) != "") && (hasNewPlan || len(dsArgs) > 0 || statusChange) {
			bf, _ := before["fields"].(map[string]any)
			vf, _ := values["fields"].(map[string]any)
			merged := make(map[string]any, len(bf)+len(vf))
			for k, v := range bf {
				merged[k] = v
			}
			for k, v := range vf {
				merged[k] = v
			}
			beforeID, _ := before["id"].(string)
			prevCopy := beforePlan
			curStatusCopy := beforeStatus
			enforced, _, err := j.Enforce(tx, projectID, beforeID, newPlan, &prevCopy, merged, reqStatusPtr, status, &curStatusCopy, dsArgs, note, false)
			if err != nil {
				return nil, err
			}
			out["plan_md"] = enforced
		}
		return out, nil
	}
}

func hasNewStatus(values map[string]any, beforeStatus string) bool {
	s, ok := values["status"].(string)
	return ok && s != beforeStatus
}

// TaskClose verifies conservative status gate and plan contract before marking a task done.
func (j *JudgeBridge) TaskClose(ctx store.Ctx, taskID string, expectedVersion int, validationResult, requestID string) (map[string]any, error) {
	p, err := store.NeedCallsign(ctx)
	if err != nil {
		return nil, err
	}
	if err := store.ScanSecrets(validationResult, "validation_result"); err != nil {
		return nil, err
	}
	pid := p.ProjectID
	return j.Store.Idempotent(ctx, requestID, func(tx *sql.Tx) (map[string]any, error) {
		before, err := j.Store.GetTask(tx, pid, taskID)
		if err != nil {
			return nil, err
		}
		curVer := before["version"].(int)
		if curVer != expectedVersion {
			return nil, store.VersionConflict(curVer, before)
		}
		beforeStatus, _ := before["status"].(string)
		reqDone := "done"
		valRes := validationResult
		status, warns := judge.DetermineConservativeTaskStatus(&reqDone, &valRes, "update", &beforeStatus, nil)
		if status != "done" {
			return nil, gateError("validation_result_required", "done 은 검증 결과가 있어야 닫힌다 — 검증하지 않은 결과를 done 으로 두지 않는다", warns)
		}
		bf, _ := before["fields"].(map[string]any)
		if rawTests, ok := bf["tests"].([]any); ok {
			var pending []string
			for _, rawTest := range rawTests {
				test, ok := rawTest.(map[string]any)
				if !ok || test["required"] != true {
					continue
				}
				runs, _ := test["runs"].([]any)
				lastStatus := ""
				if len(runs) > 0 {
					if lastRun, ok := runs[len(runs)-1].(map[string]any); ok {
						lastStatus, _ = lastRun["status"].(string)
					}
				}
				if lastStatus != "passed" {
					id, _ := test["id"].(string)
					pending = append(pending, id)
				}
			}
			if len(pending) > 0 {
				return nil, gateError("required_tests_not_passed", "필수 테스트의 최신 실행 결과가 passed 여야 닫힌다", []string{"미통과 필수 테스트: " + strings.Join(pending, ", ")})
			}
		}
		fields := make(map[string]any, len(bf)+1)
		for k, v := range bf {
			fields[k] = v
		}
		fields["validation_result"] = validationResult
		planMD, _ := before["plan_md"].(string)
		prevPlan := planMD
		curStatus := beforeStatus
		newPlan, warnings, err := j.Enforce(tx, pid, taskID, planMD, &prevPlan, fields, &reqDone, "done", &curStatus, nil, nil, false)
		if err != nil {
			return nil, err
		}
		if _, err := tx.Exec(
			"UPDATE task SET status = 'done', plan_md = ?, fields_json = ?, version = version + 1, updated_at = ? WHERE project_id = ? AND id = ? AND version = ?",
			newPlan, store.MustJSON(fields), db.FormatISO(ctx.Now), pid, taskID, curVer,
		); err != nil {
			return nil, err
		}
		after, err := j.Store.GetTask(tx, pid, taskID)
		if err != nil {
			return nil, err
		}
		if err := j.Store.RecordEvent(tx, ctx, &pid, "task", taskID, "close",
			map[string]any{"status": beforeStatus},
			map[string]any{"status": "done", "validation_result": validationResult},
			nil,
		); err != nil {
			return nil, err
		}
		if warnings == nil {
			warnings = []string{}
		}
		return map[string]any{"task": after, "warnings": warnings}, nil
	})
}

// RoadmapGet returns all roadmap documents for the caller's project.
func (j *JudgeBridge) RoadmapGet(ctx store.Ctx) (map[string]any, error) {
	p, err := store.NeedCallsign(ctx)
	if err != nil {
		return nil, err
	}
	rows, err := j.Store.DB().Query(
		"SELECT path, body_md, version, updated_by, updated_at FROM roadmap_doc WHERE project_id = ? ORDER BY path",
		p.ProjectID,
	)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	docs := make([]map[string]any, 0)
	for rows.Next() {
		var path, body, updatedBy, updatedAt string
		var version int
		if err := rows.Scan(&path, &body, &version, &updatedBy, &updatedAt); err != nil {
			return nil, err
		}
		docs = append(docs, map[string]any{
			"path":       path,
			"body_md":    body,
			"version":    version,
			"updated_by": updatedBy,
			"updated_at": updatedAt,
		})
	}
	if err := rows.Err(); err != nil {
		return nil, err
	}
	return map[string]any{"docs": docs}, nil
}

// RoadmapPut validates and writes a single roadmap document with optimistic locking.
func (j *JudgeBridge) RoadmapPut(ctx store.Ctx, path string, expectedVersion *int, body string) (map[string]any, error) {
	p, err := store.NeedCallsign(ctx)
	if err != nil {
		return nil, err
	}
	if err := store.ScanSecrets(body, "body"); err != nil {
		return nil, err
	}
	if path != roadmapIndexFile && !milestoneNameRe.MatchString(path) {
		return nil, store.InvalidField("path", "index.md 또는 M-NNN-<slug>.md")
	}
	var issues []judge.RoadmapIssue
	if path == roadmapIndexFile {
		_, issues = judge.ParseIndexText(body)
	} else {
		ms, mIssues := judge.ParseMilestoneText(body, path)
		issues = mIssues
		if ms == nil {
			detail := make([]string, len(issues))
			for i, iss := range issues {
				detail[i] = fmt.Sprintf("%s: %s", iss.Code, iss.Detail)
			}
			return nil, &store.HubError{
				Status:  400,
				Code:    "invalid_field",
				Message: "마일스톤을 읽을 수 없다 — " + strings.Join(detail, " / "),
				Detail:  map[string]any{"field": "body", "issues": detail},
			}
		}
	}
	pid := p.ProjectID
	return j.Store.WriteTx(func(tx *sql.Tx) (map[string]any, error) {
		var curBody sql.NullString
		var curVer int
		err := tx.QueryRow("SELECT body_md, version FROM roadmap_doc WHERE project_id = ? AND path = ?", pid, path).Scan(&curBody, &curVer)
		if errors.Is(err, sql.ErrNoRows) {
			curVer = 0
		} else if err != nil {
			return nil, err
		}
		if expectedVersion != nil && *expectedVersion != curVer {
			var bodyVal any
			if curBody.Valid {
				bodyVal = curBody.String
			}
			return nil, &store.HubError{
				Status:  409,
				Code:    "version_conflict",
				Message: fmt.Sprintf("version 이 다르다 — 지금 %d", curVer),
				Detail:  map[string]any{"current_version": curVer, "current": map[string]any{"path": path, "body": bodyVal}},
			}
		}
		if _, err := tx.Exec(
			"INSERT INTO roadmap_doc (project_id, path, body_md, version, updated_by, updated_at) VALUES (?, ?, ?, 1, ?, ?) "+
				"ON CONFLICT(project_id, path) DO UPDATE SET body_md = excluded.body_md, version = roadmap_doc.version + 1, "+
				"updated_by = excluded.updated_by, updated_at = excluded.updated_at",
			pid, path, body, p.Callsign, db.FormatISO(ctx.Now),
		); err != nil {
			return nil, err
		}
		if err := j.Store.RecordEvent(tx, ctx, &pid, "roadmap", path, "put",
			map[string]any{"version": curVer}, map[string]any{"version": curVer + 1}, nil); err != nil {
			return nil, err
		}
		rendered := make([]string, len(issues))
		for i, iss := range issues {
			rendered[i] = fmt.Sprintf("%s: %s", iss.Code, iss.Detail)
		}
		return map[string]any{"path": path, "version": curVer + 1, "issues": rendered}, nil
	})
}

// RoadmapState derives roadmap_state v1 without filesystem deliverable checks.
func (j *JudgeBridge) RoadmapState(ctx store.Ctx) (map[string]any, error) {
	p, err := store.NeedReader(ctx)
	if err != nil {
		return nil, err
	}
	rm, _, issues, err := j.LoadRoadmap(j.Store.DB(), p.ProjectID)
	if err != nil {
		return nil, err
	}
	if rm == nil {
		return map[string]any{"roadmap_state": nil, "reason": "로드맵이 없다 (index.md 없음)"}, nil
	}
	rows, err := j.Store.DB().Query(
		"SELECT id, status, wbs, wbs_exempt_reason FROM task WHERE project_id = ? AND wbs != ''",
		p.ProjectID,
	)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var links []judge.TaskWbsLink
	for rows.Next() {
		var id, st, wbs, ex string
		if err := rows.Scan(&id, &st, &wbs, &ex); err != nil {
			return nil, err
		}
		links = append(links, judge.TaskWbsLink{
			TaskID:       id,
			TaskStatus:   st,
			WbsRef:       wbs,
			ExemptReason: ex,
			SourcePath:   id,
		})
	}
	if err := rows.Err(); err != nil {
		return nil, err
	}
	declared := map[string]bool{}
	for _, m := range rm.Milestones {
		for _, d := range m.Deliverables {
			declared[d] = true
		}
	}
	if len(declared) > 0 {
		issues = append(issues, judge.RoadmapIssue{
			Code:   "deliverables_unmeasured",
			Detail: fmt.Sprintf("허브는 저장소를 보지 않아 산출물 %d개의 존재를 재지 않았다 — 미측정", len(declared)),
			Where:  roadmapIndexFile,
		})
	}
	state := judge.DeriveRoadmapState(rm, links, issues, func(string) bool { return true }, ctx.Now.Format("2006-01-02"))
	return map[string]any{"roadmap_state": state}, nil
}

// PlanRespond ingests a workflow-kit-plan-response/1 body from an approved human responder.
func (j *JudgeBridge) PlanRespond(ctx store.Ctx, taskID, body string) (map[string]any, error) {
	p, err := store.NeedCallsign(ctx)
	if err != nil {
		return nil, err
	}
	if p.CallsignKind != "human" || !p.HumanApproved {
		return nil, store.Forbidden("결정 응답은 승인된 human 콜사인만 보낸다")
	}
	parsed := judge.ParseResponse([]byte(body), "hub-response.md")
	if parsed.Responder() != p.Callsign {
		return nil, &store.HubError{
			Status:  403,
			Code:    "forbidden",
			Message: fmt.Sprintf("responder 가 이 콜사인(%s)이 아니다: %q", p.Callsign, parsed.Responder()),
			Detail:  map[string]any{"field": "responder"},
		}
	}
	pid := p.ProjectID
	return j.Store.WriteTx(func(tx *sql.Tx) (map[string]any, error) {
		task, err := j.Store.GetTask(tx, pid, taskID)
		if err != nil {
			return nil, err
		}
		var dup int
		err = tx.QueryRow("SELECT 1 FROM plan_response WHERE project_id = ? AND body_sha256 = ?", pid, parsed.ContentSHA256).Scan(&dup)
		if err == nil {
			return map[string]any{"task_id": taskID, "accepted": true, "duplicate": true}, nil
		}
		if !errors.Is(err, sql.ErrNoRows) {
			return nil, err
		}
		planMD, _ := task["plan_md"].(string)
		fields, _ := task["fields"].(map[string]any)
		lines, _ := TaskLines(planMD, fields)
		plan := judge.ParsePlan(lines)
		if judge.HasErrorRules(plan) {
			return nil, gateError("plan_lint_error", "task 계획이 오류 규칙을 어긴 상태라 응답을 받을 수 없다 (자격 0 단계)", nil)
		}
		verdict := judge.Qualify(parsed, plan, taskID)
		if !verdict.Eligible() {
			stage := 0
			if verdict.Stage != nil {
				stage = *verdict.Stage
			}
			return nil, &store.HubError{
				Status:  422,
				Code:    "response_ineligible",
				Message: fmt.Sprintf("자격 %d 단계에서 거부: %s", stage, verdict.Reason),
				Detail:  map[string]any{"stage": verdict.Stage, "reason": verdict.Reason},
			}
		}
		if _, err := tx.Exec(
			"INSERT INTO plan_response (project_id, task_id, body, body_sha256, received_at, responder) VALUES (?, ?, ?, ?, ?, ?)",
			pid, taskID, body, parsed.ContentSHA256, parsed.ReceivedAt(), parsed.Responder(),
		); err != nil {
			return nil, err
		}
		status, _ := task["status"].(string)
		prevPlan := planMD
		curStatus := status
		newPlan, warnings, err := j.Enforce(tx, pid, taskID, planMD, &prevPlan, fields, nil, status, &curStatus, nil, nil, false)
		if err != nil {
			return nil, err
		}
		if newPlan != planMD {
			if _, err := tx.Exec(
				"UPDATE task SET plan_md = ?, version = version + 1, updated_at = ? WHERE project_id = ? AND id = ?",
				newPlan, db.FormatISO(ctx.Now), pid, taskID,
			); err != nil {
				return nil, err
			}
		}
		if err := j.Store.RecordEvent(tx, ctx, &pid, "task", taskID, "plan_response", nil,
			map[string]any{"responder": parsed.Responder(), "sha256": parsed.ContentSHA256}, nil); err != nil {
			return nil, err
		}
		after, err := j.Store.GetTask(tx, pid, taskID)
		if err != nil {
			return nil, err
		}
		if warnings == nil {
			warnings = []string{}
		}
		return map[string]any{"task_id": taskID, "accepted": true, "duplicate": false, "task": after, "warnings": warnings}, nil
	})
}

// PlanStatus computes decision states and open decision IDs for a task.
func (j *JudgeBridge) PlanStatus(ctx store.Ctx, taskID string) (map[string]any, error) {
	p, err := store.NeedReader(ctx)
	if err != nil {
		return nil, err
	}
	task, err := j.Store.GetTask(j.Store.DB(), p.ProjectID, taskID)
	if err != nil {
		return nil, err
	}
	planMD, _ := task["plan_md"].(string)
	fields, _ := task["fields"].(map[string]any)
	lines, _ := TaskLines(planMD, fields)
	plan := judge.ParsePlan(lines)
	responses, err := j.loadResponsesForPlan(j.Store.DB(), p.ProjectID, taskID, plan)
	if err != nil {
		return nil, err
	}
	res := judge.ComputeStates(plan, responses)
	open := judge.OpenDecisionIDs(plan, responses)
	return map[string]any{
		"task_id":        taskID,
		"plan_digest":    judge.PlanDigest(plan),
		"states":         res.States,
		"open_decisions": open,
		"responses":      len(responses),
	}, nil
}
