package judge

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"unicode/utf8"

	"github.com/ykylee/standard_ai_workflow/hub-go/internal/pytext"
)

const (
	ClaimsKey    = "plan_claims"
	DecisionsKey = "plan_decisions"

	ClaimLabelCanonical    = "Claims"
	DecisionLabelCanonical = "Decisions"

	StateProposed = "proposed"
	StateUnopened = "unopened"
	StateDisputed = "disputed"
	StateKept     = "kept"
	StateChanged  = "changed"
	StateAnswered = "answered"

	MaxChildren   = 5
	MaxDecisions  = 5
	ClaimMaxChars = 80
)

var (
	claimPrefixes    = []string{"- 주장:", "- Claims:"}
	decisionPrefixes = []string{"- 결정:", "- Decisions:"}

	columnByAlias = map[string]string{
		"default": "default",
		"기본":      "default",
		"options": "options",
		"선택":      "options",
		"state":   "state",
		"상태":      "state",
	}

	bareStates   = map[string]bool{StateProposed: true, StateUnopened: true, StateDisputed: true, StateKept: true}
	valuedStates = map[string]bool{StateChanged: true, StateAnswered: true}
	openStates   = map[string]bool{StateProposed: true, StateUnopened: true, StateDisputed: true}
	errorRules   = map[string]bool{"L2": true, "L6": true, "L9": true}

	valueRe       = regexp.MustCompile(`^[a-z0-9_-]{1,32}$`)
	claimIDRe     = regexp.MustCompile(`^C([1-9][0-9]*)(?:\.([1-9][0-9]*))?(?:\.([1-9][0-9]*))?$`)
	claimHeadRe   = regexp.MustCompile(`^(C[0-9.]+)\s+(.*)$`)
	decisionHead  = regexp.MustCompile(`^(D[1-9][0-9]*)\s+\[(C[0-9.]+)\]\s+(.+)$`)
	locationRe    = regexp.MustCompile(`^@\s+(\S+?):([0-9]+)(?:-([0-9]+))?\s+·\s+(.+)$`)
	newLocationRe = regexp.MustCompile(`^@\s+new:\s+(\S+)\s+·\s+(.+)$`)
	citationRe    = regexp.MustCompile(`^\[(C[0-9.]+)\]`)
	percentRe     = regexp.MustCompile(`[0-9]+\s*%`)
	pathishRe     = regexp.MustCompile(`^(?:[\p{L}\p{N}_.-]+/[\p{L}\p{N}_./-]*|[\p{L}\p{N}_-]+\.[A-Za-z0-9]{1,5})$`)
	statusTails   = []string{"완료", "done", "✅"}
)

type ClaimLocation struct {
	Path   string
	Symbol string
	Start  *int
	End    *int
	New    bool
}

type Claim struct {
	ID       string
	Text     string
	Raw      string
	Parts    []int
	Location *ClaimLocation
}

func (c Claim) Depth() int    { return len(c.Parts) }
func (c Claim) ValidID() bool { return len(c.Parts) > 0 }

func (c Claim) ParentID() string {
	if len(c.Parts) <= 1 {
		return ""
	}
	parts := make([]string, len(c.Parts)-1)
	for i := 0; i < len(c.Parts)-1; i++ {
		parts[i] = strconv.Itoa(c.Parts[i])
	}
	return "C" + strings.Join(parts, ".")
}

type Decision struct {
	ID       string
	ClaimID  string
	Question string
	Default  string
	Options  [][2]string
	State    string
	Raw      string
	Problems []string
}

func (d Decision) OptionValues() []string {
	vals := make([]string, len(d.Options))
	for i, opt := range d.Options {
		vals[i] = opt[0]
	}
	return vals
}

func (d Decision) hasOption(v string) bool {
	for _, opt := range d.Options {
		if opt[0] == v {
			return true
		}
	}
	return false
}

func (d Decision) StateKind() string {
	k, _, _ := strings.Cut(d.State, ":")
	return k
}

func (d Decision) StateValue() (string, bool) {
	_, v, ok := strings.Cut(d.State, ":")
	return v, ok
}

func (d Decision) Answered() bool {
	return d.StateKind() == StateAnswered
}

type orderedValue struct {
	Key   string
	Value string
}

type Plan struct {
	Claims        []Claim
	Decisions     []Decision
	ClaimRuns     int
	DecisionRuns  int
	OrderedValues []orderedValue
}

func (p Plan) Empty() bool { return len(p.Claims) == 0 && len(p.Decisions) == 0 }

type LintIssue struct {
	Rule     string
	Severity string
	Message  string
	Ref      string
}

type LintIssueJSON struct {
	Message  string `json:"message"`
	Ref      string `json:"ref"`
	Rule     string `json:"rule"`
	Severity string `json:"severity"`
}

type PlanLintResult struct {
	Digest        string          `json:"digest"`
	HasError      bool            `json:"has_error"`
	Issues        []LintIssueJSON `json:"issues"`
	OpenColumnIDs []string        `json:"open_column_ids"`
}

type ResponseDecision struct {
	DecisionID string
	Value      string
	Default    string
	Opened     bool
	ClaimID    string
}

func (r ResponseDecision) Stance() (string, bool) {
	if r.Value != r.Default {
		return r.Value, true
	}
	if r.Opened {
		return r.Default, true
	}
	return "", false
}

type Response struct {
	Responder     string
	ReceivedAt    string
	Decisions     []ResponseDecision
	ContentSHA256 string
	Name          string
}

func (r Response) Stance(decisionID string) (string, bool) {
	for _, d := range r.Decisions {
		if d.DecisionID == decisionID {
			return d.Stance()
		}
	}
	return "", false
}

type StateResult struct {
	States              map[string]string
	DisputedResponses   []string
	SupersededResponses []string
}

type ResponseVerdictJSON struct {
	Eligible bool   `json:"eligible"`
	Name     string `json:"name"`
	Reason   string `json:"reason"`
	Stage    *int   `json:"stage"`
}

type PlanStatesResult struct {
	Digest              string                `json:"digest"`
	DisputedResponses   []string              `json:"disputed_responses"`
	HasError            bool                  `json:"has_error"`
	Open                []string              `json:"open"`
	States              map[string]string     `json:"states"`
	SupersededResponses []string              `json:"superseded_responses"`
	Verdicts            []ResponseVerdictJSON `json:"verdicts"`
}

type LineCounter func(path string) (int, bool)

func isPySpace(r rune) bool { return pytext.IsSpace(r) }

func pyStrip(s string) string {
	return strings.TrimFunc(s, isPySpace)
}

func pyRStrip(s string) string {
	return strings.TrimRightFunc(s, isPySpace)
}

func firstRunes(s string, max int) string {
	n := 0
	for i := range s {
		if n == max {
			return s[:i]
		}
		n++
	}
	return s
}

// splitPyLines matches Python str.splitlines(keepends=False) behavior.
func splitPyLines(s string) []string {
	if s == "" {
		return nil
	}
	var lines []string
	start := 0
	i := 0
	for i < len(s) {
		r, w := utf8.DecodeRuneInString(s[i:])
		switch r {
		case '\r':
			lines = append(lines, s[start:i])
			i += w
			if i < len(s) && s[i] == '\n' {
				i++
			}
			start = i
		case '\n', '\v', '\f', '\x1c', '\x1d', '\x1e', '\u0085', '\u2028', '\u2029':
			lines = append(lines, s[start:i])
			i += w
			start = i
		default:
			i += w
		}
	}
	if start < len(s) {
		lines = append(lines, s[start:])
	}
	return lines
}

func matchLabel(stripped string, prefixes []string) (string, bool) {
	for _, p := range prefixes {
		if stripped == p {
			return "", true
		}
		if strings.HasPrefix(stripped, p+" ") {
			return pyStrip(stripped[len(p):]), true
		}
	}
	return "", false
}

func ParseClaimValue(value string) Claim {
	m := claimHeadRe.FindStringSubmatch(value)
	if m == nil {
		head, rest, _ := strings.Cut(value, " ")
		return Claim{ID: head, Text: pyStrip(rest), Raw: value}
	}
	claimID, text := m[1], pyStrip(m[2])
	idm := claimIDRe.FindStringSubmatch(claimID)
	if idm == nil {
		return Claim{ID: claimID, Text: text, Raw: value}
	}
	var parts []int
	for _, g := range idm[1:] {
		if g != "" {
			v, _ := strconv.Atoi(g)
			parts = append(parts, v)
		}
	}
	var loc *ClaimLocation
	if nm := newLocationRe.FindStringSubmatch(text); nm != nil {
		loc = &ClaimLocation{
			Path:   nm[1],
			Symbol: pyStrip(nm[2]),
			New:    true,
		}
	} else if lm := locationRe.FindStringSubmatch(text); lm != nil {
		st, _ := strconv.Atoi(lm[2])
		en := st
		if lm[3] != "" {
			en, _ = strconv.Atoi(lm[3])
		}
		loc = &ClaimLocation{
			Path:   lm[1],
			Symbol: pyStrip(lm[4]),
			Start:  &st,
			End:    &en,
		}
	}
	return Claim{ID: claimID, Text: text, Raw: value, Parts: parts, Location: loc}
}

func splitColumns(value string) (string, map[string]string, []string) {
	var problems []string
	segs := strings.Split(value, " | ")
	head := pyStrip(segs[0])
	cols := map[string]string{}
	for _, seg := range segs[1:] {
		name, body, hasSep := strings.Cut(seg, ":")
		canonical, known := columnByAlias[pyStrip(name)]
		if !hasSep || !known {
			problems = append(problems, fmt.Sprintf("모르는 칸 `%s` — 질문 · 설명에 ` | ` 가 있거나 칸 이름이 틀렸다", firstRunes(pyStrip(seg), 40)))
			continue
		}
		if _, dup := cols[canonical]; dup {
			problems = append(problems, fmt.Sprintf("칸 `%s` 이 두 번 나온다", canonical))
			continue
		}
		cols[canonical] = pyStrip(body)
	}
	return head, cols, problems
}

func ParseState(raw string) (string, string, bool) {
	if bareStates[raw] {
		return raw, "", true
	}
	kind, val, sep := strings.Cut(raw, ":")
	if sep && valuedStates[kind] && valueRe.MatchString(val) {
		return kind, val, true
	}
	return "", "", false
}

func ParseDecisionValue(value string) Decision {
	head, cols, problems := splitColumns(value)
	var decisionID, claimID, question string
	m := decisionHead.FindStringSubmatch(head)
	if m == nil {
		problems = append(problems, "머리 `D<n> [C<id>] <질문>` 을 읽을 수 없다")
		if head != "" {
			decisionID, _, _ = strings.Cut(head, " ")
		}
		question = head
	} else {
		decisionID, claimID, question = m[1], m[2], pyStrip(m[3])
	}

	defVal, hasDef := cols["default"]
	if !hasDef {
		problems = append(problems, "`default` 칸이 없다")
	} else if !valueRe.MatchString(defVal) {
		problems = append(problems, fmt.Sprintf("`default` 값 `%s` 이 값 문법(`[a-z0-9_-]{1,32}`)에 안 맞는다", defVal))
	}

	var options [][2]string
	rawOpts, hasOpts := cols["options"]
	if !hasOpts {
		problems = append(problems, "`options` 칸이 없다")
	} else {
		seenVals := map[string]bool{}
		hasDup := false
		for _, item := range strings.Split(rawOpts, "; ") {
			opt, desc, hasEq := strings.Cut(item, "=")
			opt = pyStrip(opt)
			if !hasEq || !valueRe.MatchString(opt) {
				problems = append(problems, fmt.Sprintf("선택지 `%s` 를 `<value> = <설명>` 으로 읽을 수 없다", firstRunes(pyStrip(item), 40)))
				continue
			}
			options = append(options, [2]string{opt, pyStrip(desc)})
			if seenVals[opt] {
				hasDup = true
			}
			seenVals[opt] = true
		}
		if hasDup {
			problems = append(problems, "선택지 값이 겹친다")
		}
	}

	state, hasState := cols["state"]
	if !hasState {
		state = StateProposed
	}
	if _, _, ok := ParseState(state); !ok {
		problems = append(problems, fmt.Sprintf("상태 `%s` 를 읽을 수 없다", state))
	}

	return Decision{
		ID:       decisionID,
		ClaimID:  claimID,
		Question: question,
		Default:  defVal,
		Options:  options,
		State:    state,
		Raw:      value,
		Problems: problems,
	}
}

func ParsePlan(lines []string) Plan {
	var claims []Claim
	var decisions []Decision
	var ordered []orderedValue
	runs := map[string]int{ClaimsKey: 0, DecisionsKey: 0}
	prev := ""
	for _, line := range lines {
		stripped := pyStrip(line)
		cur := ""
		cv, hasC := matchLabel(stripped, claimPrefixes)
		dv, hasD := "", false
		if !hasC {
			dv, hasD = matchLabel(stripped, decisionPrefixes)
		}
		if (hasC && cv == "") || (hasD && dv == "") {
			continue
		}
		if hasC {
			cur = ClaimsKey
			claims = append(claims, ParseClaimValue(cv))
			ordered = append(ordered, orderedValue{Key: ClaimsKey, Value: cv})
		} else if hasD {
			cur = DecisionsKey
			decisions = append(decisions, ParseDecisionValue(dv))
			ordered = append(ordered, orderedValue{Key: DecisionsKey, Value: dv})
		}
		if cur != "" && cur != prev {
			runs[cur]++
		}
		prev = cur
	}
	return Plan{
		Claims:        claims,
		Decisions:     decisions,
		ClaimRuns:     runs[ClaimsKey],
		DecisionRuns:  runs[DecisionsKey],
		OrderedValues: ordered,
	}
}

func digestValue(key, value string) string {
	if key == ClaimsKey {
		return pyRStrip(value)
	}
	if len(ParseDecisionValue(value).Problems) > 0 {
		return pyRStrip(value)
	}
	head, cols, _ := splitColumns(value)
	parts := []string{head}
	for _, name := range []string{"default", "options"} {
		if body, ok := cols[name]; ok {
			parts = append(parts, fmt.Sprintf("%s: %s", name, body))
		}
	}
	return pyRStrip(strings.Join(parts, " | "))
}

func PlanDigest(plan Plan) string {
	lines := make([]string, len(plan.OrderedValues))
	for i, ov := range plan.OrderedValues {
		label := ClaimLabelCanonical
		if ov.Key == DecisionsKey {
			label = DecisionLabelCanonical
		}
		lines[i] = fmt.Sprintf("- %s: %s", label, digestValue(ov.Key, ov.Value))
	}
	sum := sha256.Sum256([]byte(strings.Join(lines, "\n")))
	return "sha256:" + hex.EncodeToString(sum[:])
}

func criterionCitation(criterion string) (string, bool) {
	m := citationRe.FindStringSubmatch(pyStrip(criterion))
	if m == nil {
		return "", false
	}
	return m[1], true
}

func endsWithStatus(text string) bool {
	tail := pyRStrip(text)
	tail = strings.TrimRight(tail, ".")
	tail = pyRStrip(tail)
	for _, m := range statusTails {
		if strings.HasSuffix(tail, m) {
			return true
		}
	}
	return false
}

func formatIntList(vals []int) string {
	parts := make([]string, len(vals))
	for i, v := range vals {
		parts[i] = strconv.Itoa(v)
	}
	return "[" + strings.Join(parts, ", ") + "]"
}

func LintPlan(plan Plan, criteria []string, counter LineCounter) []LintIssue {
	var issues []LintIssue
	if plan.Empty() {
		return issues
	}

	// L9 — 묶음이 나뉘었다.
	for _, item := range []struct {
		label string
		runs  int
	}{{ClaimLabelCanonical, plan.ClaimRuns}, {DecisionLabelCanonical, plan.DecisionRuns}} {
		if item.runs > 1 {
			issues = append(issues, LintIssue{
				Rule:     "L9",
				Severity: "error",
				Message:  fmt.Sprintf("`%s` 묶음이 %d개로 나뉘어 있다 — 한 묶음으로 모은다", item.label, item.runs),
			})
		}
	}

	// L2 — ID.
	seen := map[string]bool{}
	var valid []Claim
	ids := map[string]bool{}
	for _, c := range plan.Claims {
		if !c.ValidID() {
			issues = append(issues, LintIssue{
				Rule:     "L2",
				Severity: "error",
				Message:  "주장 ID 를 읽을 수 없다 (`C<n>[.<n>[.<n>]]`)",
				Ref:      c.ID,
			})
			continue
		}
		valid = append(valid, c)
		ids[c.ID] = true
		if seen[c.ID] {
			issues = append(issues, LintIssue{
				Rule:     "L2",
				Severity: "error",
				Message:  "주장 ID 가 겹친다",
				Ref:      c.ID,
			})
		}
		seen[c.ID] = true
	}

	children := map[string][]int{}
	var parentOrder []string
	for _, c := range valid {
		p := c.ParentID()
		if p != "" && !ids[p] {
			issues = append(issues, LintIssue{
				Rule:     "L2",
				Severity: "error",
				Message:  fmt.Sprintf("부모 `%s` 가 없다", p),
				Ref:      c.ID,
			})
		}
		if _, exists := children[p]; !exists {
			parentOrder = append(parentOrder, p)
		}
		children[p] = append(children[p], c.Parts[len(c.Parts)-1])
	}
	for _, p := range parentOrder {
		nums := uniqueSortedInts(children[p])
		contiguous := true
		for i, n := range nums {
			if n != i+1 {
				contiguous = false
				break
			}
		}
		if !contiguous {
			where := p
			if where == "" {
				where = "1단계"
			}
			issues = append(issues, LintIssue{
				Rule:     "L2",
				Severity: "error",
				Message:  fmt.Sprintf("형제 번호가 1 부터 연속이 아니다 (%s)", formatIntList(nums)),
				Ref:      where,
			})
		}
	}

	// L1 — 폭.
	for _, p := range parentOrder {
		nums := uniqueSortedInts(children[p])
		if len(nums) > MaxChildren {
			where := p
			if where == "" {
				where = "1단계"
			}
			issues = append(issues, LintIssue{
				Rule:     "L1",
				Severity: "warning",
				Message:  fmt.Sprintf("주장이 %d개다 (≤ %d)", len(nums), MaxChildren),
				Ref:      where,
			})
		}
	}

	// L3 · L4 · L8 — 문장.
	for _, c := range valid {
		if c.Depth() <= 2 {
			if strings.Contains(c.Text, ";") {
				issues = append(issues, LintIssue{
					Rule:     "L3",
					Severity: "warning",
					Message:  "한 주장에 두 사실이 `;` 로 이어져 있다",
					Ref:      c.ID,
				})
			}
			if n := utf8.RuneCountInString(c.Text); n > ClaimMaxChars {
				issues = append(issues, LintIssue{
					Rule:     "L3",
					Severity: "warning",
					Message:  fmt.Sprintf("%d자다 (≤ %d자)", n, ClaimMaxChars),
					Ref:      c.ID,
				})
			}
		}
		if c.Depth() == 1 {
			first, _, _ := strings.Cut(c.Text, " ")
			first = strings.Trim(first, "`")
			if first != "" && pathishRe.MatchString(first) {
				issues = append(issues, LintIssue{
					Rule:     "L4",
					Severity: "warning",
					Message:  "1단계 주장이 경로 · 파일명으로 시작한다 — 동작 단위로 나눈다",
					Ref:      c.ID,
				})
			}
		}
		if percentRe.MatchString(c.Text) || endsWithStatus(c.Text) {
			issues = append(issues, LintIssue{
				Rule:     "L8",
				Severity: "warning",
				Message:  "주장에 진척률 · 상태 표현이 있다",
				Ref:      c.ID,
			})
		}
	}

	// L5 — 위치.
	var located []Claim
	for _, c := range valid {
		if c.Location != nil && !c.Location.New {
			located = append(located, c)
		}
	}
	if len(located) > 0 && counter == nil {
		issues = append(issues, LintIssue{
			Rule:     "L5",
			Severity: "note",
			Message:  fmt.Sprintf("git 밖이라 위치 %d건을 확인하지 못했다 (건너뜀)", len(located)),
		})
	} else if counter != nil {
		for _, c := range located {
			loc := c.Location
			cnt, ok := counter(loc.Path)
			if !ok {
				issues = append(issues, LintIssue{
					Rule:     "L5",
					Severity: "warning",
					Message:  fmt.Sprintf("`%s` 가 HEAD 에 없다", loc.Path),
					Ref:      c.ID,
				})
			} else if *loc.Start < 1 || *loc.End < *loc.Start || *loc.End > cnt {
				issues = append(issues, LintIssue{
					Rule:     "L5",
					Severity: "warning",
					Message:  fmt.Sprintf("`%s` 는 %d줄인데 %d-%d 를 가리킨다", loc.Path, cnt, *loc.Start, *loc.End),
					Ref:      c.ID,
				})
			}
		}
	}
	for _, c := range valid {
		if c.Depth() == 3 && c.Location == nil {
			issues = append(issues, LintIssue{
				Rule:     "L5",
				Severity: "warning",
				Message:  "3단계 주장은 위치(`@ path:line · symbol` 또는 `@ new: …`)다",
				Ref:      c.ID,
			})
		}
	}

	// L6 — 결정.
	if len(plan.Decisions) > MaxDecisions {
		issues = append(issues, LintIssue{
			Rule:     "L6",
			Severity: "error",
			Message:  fmt.Sprintf("결정이 %d개다 (≤ %d)", len(plan.Decisions), MaxDecisions),
		})
	}
	dIDs := map[string]bool{}
	for _, d := range plan.Decisions {
		ref := d.ID
		if ref == "" {
			ref = "(ID 없음)"
		}
		for _, p := range d.Problems {
			issues = append(issues, LintIssue{Rule: "L6", Severity: "error", Message: p, Ref: ref})
		}
		if dIDs[d.ID] {
			issues = append(issues, LintIssue{Rule: "L6", Severity: "error", Message: "결정 ID 가 겹친다", Ref: ref})
		}
		dIDs[d.ID] = true
		if len(d.Problems) > 0 {
			continue
		}
		if !ids[d.ClaimID] {
			issues = append(issues, LintIssue{Rule: "L6", Severity: "error", Message: fmt.Sprintf("가리키는 주장 `%s` 가 없다", d.ClaimID), Ref: ref})
		}
		if len(d.Options) < 2 {
			issues = append(issues, LintIssue{Rule: "L6", Severity: "error", Message: "선택지가 둘 미만이다", Ref: ref})
		}
		if !d.hasOption(d.Default) {
			issues = append(issues, LintIssue{Rule: "L6", Severity: "error", Message: fmt.Sprintf("`default` 값 `%s` 이 선택지에 없다", d.Default), Ref: ref})
		}
		if val, ok := d.StateValue(); ok && !d.hasOption(val) {
			issues = append(issues, LintIssue{Rule: "L6", Severity: "error", Message: fmt.Sprintf("상태의 값 `%s` 이 선택지에 없다", val), Ref: ref})
		}
	}

	// L7 · L10 — 인용.
	citedRoot := map[string]bool{}
	for idx, crit := range criteria {
		cit, hasCit := criterionCitation(crit)
		if !hasCit {
			continue
		}
		if !ids[cit] {
			issues = append(issues, LintIssue{
				Rule:     "L10",
				Severity: "warning",
				Message:  fmt.Sprintf("완료 기준 #%d 가 없는 주장 `%s` 을 인용한다", idx+1, cit),
			})
			continue
		}
		root, _, _ := strings.Cut(cit, ".")
		citedRoot[root] = true
	}
	for _, c := range valid {
		if c.Depth() == 1 && !citedRoot[c.ID] {
			issues = append(issues, LintIssue{
				Rule:     "L7",
				Severity: "warning",
				Message:  "이 주장(과 후손)을 인용한 완료 기준이 없다 — 재지 않는 주장",
				Ref:      c.ID,
			})
		}
	}
	return issues
}

func uniqueSortedInts(xs []int) []int {
	seen := map[int]bool{}
	out := make([]int, 0, len(xs))
	for _, x := range xs {
		if !seen[x] {
			seen[x] = true
			out = append(out, x)
		}
	}
	sort.Ints(out)
	return out
}

func HasErrorRules(plan Plan) bool {
	for _, iss := range LintPlan(plan, nil, nil) {
		if iss.Severity == "error" || errorRules[iss.Rule] && iss.Severity == "error" {
			return true
		}
	}
	return false
}

func StateIsOpen(state string) bool {
	kind, _, _ := strings.Cut(state, ":")
	return openStates[kind]
}

type receivedKey struct {
	parsed  int
	micros  int64
	rawTime string
	sha256  string
}

func receivedKeyOf(r Response) receivedKey {
	micros, ok := ParseReceivedAt(r.ReceivedAt)
	if !ok {
		return receivedKey{parsed: 0, micros: 0, rawTime: r.ReceivedAt, sha256: r.ContentSHA256}
	}
	return receivedKey{parsed: 1, micros: micros, rawTime: "", sha256: r.ContentSHA256}
}

func keyGTE(a, b receivedKey) bool {
	if a.parsed != b.parsed {
		return a.parsed > b.parsed
	}
	if a.micros != b.micros {
		return a.micros > b.micros
	}
	if a.rawTime != b.rawTime {
		return a.rawTime > b.rawTime
	}
	return a.sha256 >= b.sha256
}

type indexedResponse struct {
	idx  int
	resp Response
}

func effectiveResponses(responses []Response) ([]indexedResponse, []indexedResponse) {
	latest := map[string]indexedResponse{}
	for idx, r := range responses {
		cur, exists := latest[r.Responder]
		if !exists || keyGTE(receivedKeyOf(r), receivedKeyOf(cur.resp)) {
			latest[r.Responder] = indexedResponse{idx: idx, resp: r}
		}
	}
	names := make([]string, 0, len(latest))
	for name := range latest {
		names = append(names, name)
	}
	sort.Strings(names)
	effective := make([]indexedResponse, 0, len(names))
	chosen := map[int]bool{}
	for _, name := range names {
		ir := latest[name]
		effective = append(effective, ir)
		chosen[ir.idx] = true
	}
	var superseded []indexedResponse
	for idx, r := range responses {
		if !chosen[idx] {
			superseded = append(superseded, indexedResponse{idx: idx, resp: r})
		}
	}
	return effective, superseded
}

func responseLabel(r Response) string {
	if r.Name != "" {
		return r.Name
	}
	return r.Responder
}

func ComputeStates(plan Plan, responses []Response) StateResult {
	effective, superseded := effectiveResponses(responses)
	answered := map[string]string{}
	for _, d := range plan.Decisions {
		if d.Answered() {
			if val, ok := d.StateValue(); ok {
				answered[d.ID] = val
			}
		}
	}

	disputedIdx := map[int]bool{}
	disputedDec := map[string]bool{}
	for _, d := range plan.Decisions {
		type rs struct {
			idx    int
			stance string
		}
		var stated []rs
		distinct := map[string]bool{}
		for _, ir := range effective {
			if s, ok := ir.resp.Stance(d.ID); ok {
				stated = append(stated, rs{idx: ir.idx, stance: s})
				distinct[s] = true
			}
		}
		if ans, isAns := answered[d.ID]; isAns {
			for _, item := range stated {
				if item.stance != ans {
					disputedIdx[item.idx] = true
				}
			}
			continue
		}
		if len(distinct) > 1 {
			disputedDec[d.ID] = true
			for _, item := range stated {
				disputedIdx[item.idx] = true
			}
		}
	}

	var adopted []Response
	for _, ir := range effective {
		if !disputedIdx[ir.idx] {
			adopted = append(adopted, ir.resp)
		}
	}

	states := map[string]string{}
	for _, d := range plan.Decisions {
		if d.Answered() {
			states[d.ID] = d.State
		} else if disputedDec[d.ID] {
			states[d.ID] = StateDisputed
		} else {
			gatheredMap := map[string]bool{}
			for _, r := range adopted {
				if s, ok := r.Stance(d.ID); ok {
					gatheredMap[s] = true
				}
			}
			if len(gatheredMap) > 0 {
				var vals []string
				for v := range gatheredMap {
					vals = append(vals, v)
				}
				sort.Strings(vals)
				v := vals[0]
				if v == d.Default {
					states[d.ID] = StateKept
				} else {
					states[d.ID] = StateChanged + ":" + v
				}
			} else if len(effective) > 0 {
				states[d.ID] = StateUnopened
			} else {
				states[d.ID] = StateProposed
			}
		}
	}

	disputedNames := make([]string, 0)
	for _, ir := range effective {
		if disputedIdx[ir.idx] {
			disputedNames = append(disputedNames, responseLabel(ir.resp))
		}
	}
	supersededNames := make([]string, 0, len(superseded))
	for _, ir := range superseded {
		supersededNames = append(supersededNames, responseLabel(ir.resp))
	}

	return StateResult{
		States:              states,
		DisputedResponses:   disputedNames,
		SupersededResponses: supersededNames,
	}
}

func OpenDecisionIDs(plan Plan, responses []Response) []string {
	res := ComputeStates(plan, responses)
	opened := make([]string, 0)
	for _, d := range plan.Decisions {
		st, ok := res.States[d.ID]
		if !ok {
			st = StateProposed
		}
		if len(d.Problems) > 0 || StateIsOpen(st) {
			id := d.ID
			if id == "" {
				id = "(ID 없음)"
			}
			opened = append(opened, id)
		}
	}
	return opened
}

func ColumnOpenDecisionIDs(plan Plan) []string {
	out := make([]string, 0)
	for _, d := range plan.Decisions {
		if len(d.Problems) > 0 || StateIsOpen(d.State) {
			id := d.ID
			if id == "" {
				id = "(ID 없음)"
			}
			out = append(out, id)
		}
	}
	return out
}
