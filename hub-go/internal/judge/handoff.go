package judge

import (
	"fmt"
	"regexp"
	"strings"
)

const workItemIDPattern = `(?:TASK|WF)-[A-Za-z0-9._-]+`

var (
	linkRe       = regexp.MustCompile(`\[[^\]]+\]\(([^)]+)\)`)
	workStatusRe = regexp.MustCompile(`^-\s+(` + workItemIDPattern + `)\s+(.+?):\s*(planned|in_progress|blocked|done)\s*$`)
)

type HandoffParseResult struct {
	BlockedItems    []string `json:"blocked_items"`
	Constraints     *string  `json:"constraints"`
	CurrentAxis     *string  `json:"current_axis"`
	CurrentBaseline *string  `json:"current_baseline"`
	InProgressItems []string `json:"in_progress_items"`
	NextDocuments   []string `json:"next_documents"`
	RecentCoreDocs  []string `json:"recent_core_docs"`
	RecentDoneItems []string `json:"recent_done_items"`
	Warnings        []string `json:"warnings"`
}

func normalizeInlineCode(value string) string {
	n := pyStrip(value)
	for strings.HasPrefix(n, "`") {
		n = pyStrip(n[1:])
	}
	for strings.HasSuffix(n, "`") {
		n = pyStrip(n[:len(n)-1])
	}
	return n
}

func extractSectionValue(lines []string, labels ...string) *string {
	for _, label := range labels {
		prefix := "- " + label + ":"
		for idx, line := range lines {
			stripped := pyStrip(line)
			if strings.HasPrefix(stripped, prefix) {
				valuePart := pyStrip(stripped[len(prefix):])
				if valuePart != "" {
					v := normalizeInlineCode(valuePart)
					return &v
				}
				if idx+1 < len(lines) {
					nextVal := pyStrip(lines[idx+1])
					if strings.HasPrefix(nextVal, "- ") {
						nextVal = pyStrip(nextVal[2:])
					}
					if nextVal != "" {
						v := normalizeInlineCode(nextVal)
						return &v
					}
				}
			}
		}
	}
	return nil
}

func extractListAfterLabel(lines []string, label string) []string {
	prefix := "- " + label + ":"
	results := make([]string, 0)
	capture := false
	for _, line := range lines {
		stripped := pyStrip(line)
		if stripped == prefix {
			capture = true
			continue
		}
		if capture {
			if strings.HasPrefix(stripped, "## ") {
				break
			}
			if strings.HasPrefix(stripped, "- ") {
				results = append(results, normalizeInlineCode(pyStrip(stripped[2:])))
			} else if stripped != "" {
				break
			}
		}
	}
	return results
}

func extractSectionLines(lines []string, title string) []string {
	heading := "## " + title
	collecting := false
	out := make([]string, 0)
	for _, line := range lines {
		stripped := pyRStrip(line)
		if strings.HasPrefix(stripped, "## ") {
			if collecting {
				break
			}
			collecting = stripped == heading
			continue
		}
		if collecting {
			out = append(out, line)
		}
	}
	return out
}

func firstBulletOrText(lines []string) *string {
	for _, line := range lines {
		stripped := pyStrip(line)
		if stripped == "" {
			continue
		}
		if strings.HasPrefix(stripped, "- ") {
			v := normalizeInlineCode(pyStrip(stripped[2:]))
			return &v
		}
		v := normalizeInlineCode(stripped)
		return &v
	}
	return nil
}

func parseWorkStatusItems(lines []string) (inProg, blocked, done []string) {
	inProg = make([]string, 0)
	blocked = make([]string, 0)
	done = make([]string, 0)
	for _, line := range lines {
		m := workStatusRe.FindStringSubmatch(pyStrip(line))
		if m == nil {
			continue
		}
		item := m[1] + " " + m[2]
		switch m[3] {
		case "in_progress":
			inProg = append(inProg, item)
		case "blocked":
			blocked = append(blocked, item)
		case "done":
			done = append(done, item)
		}
	}
	return inProg, blocked, done
}

func normalizeLinkTarget(raw string) string {
	t := pyStrip(raw)
	if strings.HasPrefix(t, "<") && strings.HasSuffix(t, ">") {
		t = pyStrip(t[1 : len(t)-1])
	}
	if i := strings.IndexByte(t, '#'); i != -1 {
		t = t[:i]
	}
	return t
}

func iterMarkdownLinkTargets(text string) []string {
	matches := linkRe.FindAllStringSubmatch(text, -1)
	out := make([]string, 0, len(matches))
	for _, m := range matches {
		t := normalizeLinkTarget(m[1])
		if t == "" || strings.Contains(t, "://") || strings.HasPrefix(t, "#") {
			continue
		}
		out = append(out, t)
	}
	return out
}

// purePosixAsPosix matches Python pathlib.PurePosixPath(raw).as_posix().
func purePosixAsPosix(raw string) string {
	if raw == "" {
		return "."
	}
	leading := ""
	rest := raw
	if strings.HasPrefix(raw, "/") {
		// POSIX preserves exact double leading "//" (anchor "//"), collapses 1 or >=3 to "/".
		slashCount := 0
		for slashCount < len(raw) && raw[slashCount] == '/' {
			slashCount++
		}
		if slashCount == 2 {
			leading = "//"
		} else {
			leading = "/"
		}
		rest = raw[slashCount:]
	}
	var kept []string
	for _, seg := range strings.Split(rest, "/") {
		if seg == "" || seg == "." {
			continue
		}
		kept = append(kept, seg)
	}
	if leading != "" {
		return leading + strings.Join(kept, "/")
	}
	if len(kept) == 0 {
		return "."
	}
	return strings.Join(kept, "/")
}

func normalizeUniversalNewlines(s string) string {
	return strings.NewReplacer("\r\n", "\n", "\r", "\n").Replace(s)
}

func parseHandoffInternal(text, docName string) (HandoffParseResult, []string) {
	lines := splitPyLines(text)
	warnings := make([]string, 0)

	getVal := func(label string, required bool) *string {
		val := extractSectionValue(lines, label)
		if val == nil && required {
			warnings = append(warnings, fmt.Sprintf("필수 섹션 누락: `%s` (%s)", label, docName))
		}
		return val
	}

	currentFocus := firstBulletOrText(extractSectionLines(lines, "Current Focus"))
	wsInProg, wsBlocked, wsDone := parseWorkStatusItems(extractSectionLines(lines, "Work Status"))

	strOr := func(v, fallback *string) *string {
		if v != nil && *v != "" {
			return v
		}
		return fallback
	}

	baseline := strOr(getVal("현재 기준선", currentFocus == nil), currentFocus)
	axis := strOr(getVal("현재 주 작업 축", currentFocus == nil), currentFocus)
	coreDocs := extractListAfterLabel(lines, "최근 핵심 기준 문서")
	inProg := extractListAfterLabel(lines, "현재 `in_progress` 작업")
	if len(inProg) == 0 {
		inProg = wsInProg
	}
	blocked := extractListAfterLabel(lines, "현재 `blocked` 작업")
	if len(blocked) == 0 {
		blocked = wsBlocked
	}
	recentDone := extractListAfterLabel(lines, "최근 완료 작업 목록")
	if len(recentDone) == 0 {
		recentDone = wsDone
	}
	constraints := getVal("주요 제약", false)

	rawTargets := iterMarkdownLinkTargets(text)
	nextDocs := make([]string, len(rawTargets))
	for i, t := range rawTargets {
		nextDocs[i] = purePosixAsPosix(t)
	}

	res := HandoffParseResult{
		BlockedItems:    blocked,
		Constraints:     constraints,
		CurrentAxis:     axis,
		CurrentBaseline: baseline,
		InProgressItems: inProg,
		NextDocuments:   nextDocs,
		RecentCoreDocs:  coreDocs,
		RecentDoneItems: recentDone,
		Warnings:        warnings,
	}
	return res, rawTargets
}

func ParseHandoffText(text, docName string) HandoffParseResult {
	res, _ := parseHandoffInternal(normalizeUniversalNewlines(text), docName)
	return res
}
