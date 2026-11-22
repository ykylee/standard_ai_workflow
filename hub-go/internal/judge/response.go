package judge

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"unicode/utf8"
)

const (
	ResponseFormat    = "workflow-kit-plan-response/1"
	RoleApprover      = "approver"
	MaxBytes          = 65536
	MaxComments       = 20
	MaxCommentChars   = 1000
	MaxResponderChars = 32
	commentPrefix     = "  > "
)

var (
	frontmatterKeys = map[string]bool{
		"format":      true,
		"task":        true,
		"plan_digest": true,
		"responder":   true,
		"role":        true,
		"received_at": true,
		"client":      true,
	}
	receivedAtRe   = regexp.MustCompile(`^([0-9]{4})-([0-9]{2})-([0-9]{2})T([0-9]{2}):([0-9]{2}):([0-9]{2})(?:\.([0-9]{1,6}))?([+-])([0-9]{2}):([0-9]{2})$`)
	decisionLineRe = regexp.MustCompile(`^- (D[1-9][0-9]*) \[(C[0-9.]+)\] value: (\S+) \| default: (\S+) \| opened: (\S+)$`)
	commentHeadRe  = regexp.MustCompile(`^- \[([^\]]+)\]$`)
)

type ParsedResponse struct {
	Name             string
	ContentSHA256    string
	Fields           map[string]string
	Decisions        []ResponseDecision
	OpenedRaw        []string
	Comments         [][2]string
	LimitProblems    []string
	HeaderProblems   []string
	DecisionProblems []string
}

func (p ParsedResponse) Responder() string  { return p.Fields["responder"] }
func (p ParsedResponse) ReceivedAt() string { return p.Fields["received_at"] }

type Verdict struct {
	Stage  *int
	Reason string
}

func (v Verdict) Eligible() bool { return v.Stage == nil }

func intPtr(n int) *int { return &n }

func fmtComma(n int) string {
	s := strconv.Itoa(n)
	if len(s) <= 3 {
		return s
	}
	var out []byte
	rem := len(s) % 3
	if rem > 0 {
		out = append(out, s[:rem]...)
	}
	for i := rem; i < len(s); i += 3 {
		if len(out) > 0 {
			out = append(out, ',')
		}
		out = append(out, s[i:i+3]...)
	}
	return string(out)
}

func isLeapYear(y int) bool {
	return y%4 == 0 && (y%100 != 0 || y%400 == 0)
}

func daysInMonth(y, m int) int {
	switch m {
	case 1, 3, 5, 7, 8, 10, 12:
		return 31
	case 4, 6, 9, 11:
		return 30
	case 2:
		if isLeapYear(y) {
			return 29
		}
		return 28
	default:
		return 0
	}
}

// daysFromCivil returns days since 1970-01-01 using Howard Hinnant's civil algorithm (works for all 0001..9999 years).
func daysFromCivil(y, m, d int) int64 {
	y64 := int64(y)
	m64 := int64(m)
	d64 := int64(d)
	if m64 <= 2 {
		y64--
	}
	era := y64 / 400
	if y64 < 0 {
		era = (y64 - 399) / 400
	}
	yoe := y64 - era*400
	mp := m64 - 3
	if m64 <= 2 {
		mp = m64 + 9
	}
	doy := (153*mp+2)/5 + d64 - 1
	doe := yoe*365 + yoe/4 - yoe/100 + doy
	return era*146097 + doe - 719468
}

func ParseReceivedAt(value string) (int64, bool) {
	m := receivedAtRe.FindStringSubmatch(value)
	if m == nil {
		return 0, false
	}
	year, _ := strconv.Atoi(m[1])
	month, _ := strconv.Atoi(m[2])
	day, _ := strconv.Atoi(m[3])
	hour, _ := strconv.Atoi(m[4])
	minute, _ := strconv.Atoi(m[5])
	second, _ := strconv.Atoi(m[6])
	offH, _ := strconv.Atoi(m[9])
	offM, _ := strconv.Atoi(m[10])
	if hour > 23 || minute > 59 || second > 59 || offH > 23 || offM > 59 {
		return 0, false
	}
	if year < 1 || year > 9999 || month < 1 || month > 12 || day < 1 || day > daysInMonth(year, month) {
		return 0, false
	}
	days := daysFromCivil(year, month, day)
	offSec := int64(offH*3600 + offM*60)
	if m[8] == "-" {
		offSec = -offSec
	}
	frac := m[7]
	for len(frac) < 6 {
		frac += "0"
	}
	micros, _ := strconv.ParseInt(frac, 10, 64)
	totalSec := days*86400 + int64(hour)*3600 + int64(minute)*60 + int64(second) - offSec
	return totalSec*1_000_000 + micros, true
}

func ParseResponse(data []byte, name string) ParsedResponse {
	var limits, header, decProblems []string
	sum := sha256.Sum256(data)
	digest := hex.EncodeToString(sum[:])

	if len(data) > MaxBytes {
		limits = append(limits, fmt.Sprintf("파일이 %s 바이트다 (한도 %s)", fmtComma(len(data)), fmtComma(MaxBytes)))
	}
	if bytes.HasPrefix(data, []byte{0xEF, 0xBB, 0xBF}) {
		limits = append(limits, "BOM 이 있다")
	}
	if !utf8.Valid(data) {
		limits = append(limits, "UTF-8 이 아니다")
		return ParsedResponse{
			Name:          name,
			ContentSHA256: digest,
			Fields:        map[string]string{},
			LimitProblems: limits,
			HeaderProblems: []string{
				"머리말을 읽지 못했다",
			},
		}
	}
	text := string(data)

	ctrlSet := map[rune]bool{}
	for _, r := range text {
		if (r < 0x20 && r != '\n' && r != '\t') || r == 0x7F {
			ctrlSet[r] = true
		}
	}
	if len(ctrlSet) > 0 {
		ctrls := make([]rune, 0, len(ctrlSet))
		for r := range ctrlSet {
			ctrls = append(ctrls, r)
		}
		sort.Slice(ctrls, func(i, j int) bool { return ctrls[i] < ctrls[j] })
		parts := make([]string, len(ctrls))
		for i, r := range ctrls {
			parts[i] = fmt.Sprintf("U+%04X", r)
		}
		limits = append(limits, "제어 문자가 있다: "+strings.Join(parts, ", "))
	}

	lines := strings.Split(text, "\n")
	fields := map[string]string{}
	bodyStart := 0
	endIdx := -1
	if len(lines) > 0 && lines[0] == "---" {
		for idx := 1; idx < len(lines); idx++ {
			if lines[idx] == "---" {
				endIdx = idx
				break
			}
		}
	}
	if endIdx != -1 {
		for _, line := range lines[1:endIdx] {
			key, val, sep := strings.Cut(line, ":")
			k := pyStrip(key)
			_, dup := fields[k]
			if !sep || !frontmatterKeys[k] || dup {
				header = append(header, fmt.Sprintf("머리말 줄을 읽지 못했다: %s", firstRunes(line, 40)))
				continue
			}
			fields[k] = pyStrip(val)
		}
		bodyStart = endIdx + 1
	} else {
		header = append(header, "머리말(`---` 두 줄)이 없다")
	}

	responder := fields["responder"]
	if responder == "" {
		limits = append(limits, "responder 가 없다")
	} else if rl := utf8.RuneCountInString(responder); rl > MaxResponderChars {
		limits = append(limits, fmt.Sprintf("responder 가 %d자다 (한도 %d)", rl, MaxResponderChars))
	}
	if _, ok := ParseReceivedAt(fields["received_at"]); !ok {
		limits = append(limits, "received_at 이 `YYYY-MM-DDTHH:MM:SS[.ffffff]±HH:MM` 꼴이 아니다")
	}

	var decisions []ResponseDecision
	var openedRaw []string
	var comments [][2]string
	section := ""
	hasCurrent := false
	curTarget := ""
	var curLines []string

	flushComment := func() {
		if hasCurrent {
			comments = append(comments, [2]string{curTarget, strings.Join(curLines, "\n")})
			hasCurrent = false
			curTarget = ""
			curLines = nil
		}
	}

	for _, line := range lines[bodyStart:] {
		if strings.HasPrefix(line, "## ") {
			flushComment()
			section = pyStrip(line[3:])
			continue
		}
		if section == "Decisions" {
			if pyStrip(line) == "" {
				continue
			}
			m := decisionLineRe.FindStringSubmatch(line)
			if m == nil {
				decProblems = append(decProblems, fmt.Sprintf("결정 줄을 읽지 못했다: %s", firstRunes(line, 40)))
				continue
			}
			decisions = append(decisions, ResponseDecision{
				DecisionID: m[1],
				ClaimID:    m[2],
				Value:      m[3],
				Default:    m[4],
				Opened:     m[5] == "yes",
			})
			openedRaw = append(openedRaw, m[5])
		} else if section == "Comments" {
			if hm := commentHeadRe.FindStringSubmatch(line); hm != nil {
				flushComment()
				hasCurrent = true
				curTarget = hm[1]
				curLines = nil
			} else if hasCurrent && strings.HasPrefix(line, commentPrefix) {
				curLines = append(curLines, line[len(commentPrefix):])
			}
		}
	}
	flushComment()

	if len(comments) > MaxComments {
		limits = append(limits, fmt.Sprintf("주석이 %d건이다 (한도 %d)", len(comments), MaxComments))
	}
	for _, c := range comments {
		if cl := utf8.RuneCountInString(c[1]); cl > MaxCommentChars {
			limits = append(limits, fmt.Sprintf("주석 [%s] 이 %s code point 다 (한도 %s)", c[0], fmtComma(cl), fmtComma(MaxCommentChars)))
		}
	}

	return ParsedResponse{
		Name:             name,
		ContentSHA256:    digest,
		Fields:           fields,
		Decisions:        decisions,
		OpenedRaw:        openedRaw,
		Comments:         comments,
		LimitProblems:    limits,
		HeaderProblems:   header,
		DecisionProblems: decProblems,
	}
}

func Qualify(parsed ParsedResponse, plan Plan, taskID string) Verdict {
	if len(parsed.LimitProblems) > 0 {
		return Verdict{Stage: intPtr(1), Reason: parsed.LimitProblems[0]}
	}
	if len(parsed.HeaderProblems) > 0 {
		return Verdict{Stage: intPtr(2), Reason: parsed.HeaderProblems[0]}
	}
	if f := parsed.Fields["format"]; f != ResponseFormat {
		if f == "" {
			f = "(없음)"
		}
		return Verdict{Stage: intPtr(2), Reason: fmt.Sprintf("format 이 %s 이 아니다: %s", ResponseFormat, f)}
	}
	if t := parsed.Fields["task"]; t != taskID {
		if t == "" {
			t = "(없음)"
		}
		return Verdict{Stage: intPtr(3), Reason: fmt.Sprintf("task 가 %s 가 아니다: %s", taskID, t)}
	}
	if parsed.Fields["plan_digest"] != PlanDigest(plan) {
		return Verdict{Stage: intPtr(4), Reason: "plan_digest 가 지금의 계획과 다르다 — 옛 계획에 대한 응답이다"}
	}
	if r := parsed.Fields["role"]; r != RoleApprover {
		if r == "" {
			r = "(없음)"
		}
		return Verdict{Stage: intPtr(5), Reason: fmt.Sprintf("role 이 %s 가 아니다: %s", RoleApprover, r)}
	}
	if len(parsed.DecisionProblems) > 0 {
		return Verdict{Stage: intPtr(6), Reason: parsed.DecisionProblems[0]}
	}
	expected := make(map[string]Decision, len(plan.Decisions))
	for _, d := range plan.Decisions {
		expected[d.ID] = d
	}
	seen := make(map[string]bool, len(parsed.Decisions))
	for _, line := range parsed.Decisions {
		if seen[line.DecisionID] {
			return Verdict{Stage: intPtr(6), Reason: "결정 ID 집합이 task 의 것과 다르다"}
		}
		seen[line.DecisionID] = true
	}
	if len(seen) != len(expected) {
		return Verdict{Stage: intPtr(6), Reason: "결정 ID 집합이 task 의 것과 다르다"}
	}
	for id := range expected {
		if !seen[id] {
			return Verdict{Stage: intPtr(6), Reason: "결정 ID 집합이 task 의 것과 다르다"}
		}
	}
	for i, line := range parsed.Decisions {
		opened := parsed.OpenedRaw[i]
		dec := expected[line.DecisionID]
		if line.ClaimID != dec.ClaimID {
			return Verdict{Stage: intPtr(6), Reason: fmt.Sprintf("%s 의 주장 ID 가 다르다: %s", line.DecisionID, line.ClaimID)}
		}
		if line.Default != dec.Default {
			return Verdict{Stage: intPtr(6), Reason: fmt.Sprintf("%s 의 default 가 다르다: %s", line.DecisionID, line.Default)}
		}
		if !dec.hasOption(line.Value) {
			return Verdict{Stage: intPtr(6), Reason: fmt.Sprintf("%s 의 value 가 선택지에 없다: %s", line.DecisionID, line.Value)}
		}
		if opened != "yes" && opened != "no" {
			return Verdict{Stage: intPtr(6), Reason: fmt.Sprintf("%s 의 opened 가 yes · no 가 아니다: %s", line.DecisionID, opened)}
		}
	}
	return Verdict{}
}

func AsResponse(parsed ParsedResponse) Response {
	return Response{
		Responder:     parsed.Responder(),
		ReceivedAt:    parsed.ReceivedAt(),
		Decisions:     parsed.Decisions,
		ContentSHA256: parsed.ContentSHA256,
		Name:          parsed.Name,
	}
}
