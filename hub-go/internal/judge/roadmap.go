package judge

import (
	"fmt"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"unicode/utf8"
)

const (
	RoadmapIndexFile  = "index.md"
	WbsExemptValue    = "exempt"
	RoadmapSchemaVer  = 1
	RoadmapGenBy      = "workflow_kit.common.state.roadmap.generate_roadmap_state"
	DeliverableUnmeas = "deliverables_unmeasured"
)

var (
	milestoneFileRe = regexp.MustCompile(`^(M-\d{3})-[a-z0-9-]+\.md$`)
	milestoneIDRe   = regexp.MustCompile(`^M-(\d{3})$`)
	goalIDRe        = regexp.MustCompile(`^G\d+$`)
	wbsIDRe         = regexp.MustCompile(`^WBS-(\d+)(?:\.(\d+))+$`)
	wbsRefRe        = regexp.MustCompile(`^(M-\d{3})/(WBS-[\d.]+)$`)

	indexEntryRe = regexp.MustCompile(`^-\s+\*\*(M-\d{3})\*\*\s+\[([a-z_]+)\]\s+(.+?)\s+—\s+status:\s*([a-z_]+)\s*$`)
	indexPathRe  = regexp.MustCompile(`^\s+-\s+path:\s+\[[^\]]*\]\(([^)]+)\)\s*$`)
	indexDraftRe = regexp.MustCompile(`(?m)^-\s*상태:\s*draft\b`)

	wbsLineRe      = regexp.MustCompile(`^(\s*)-\s+\*\*(WBS-[\d.]+)\*\*\s+(.+?)(?:\s+—\s+산출물:\s*(.+))?\s*$`)
	wbsGoalsLineRe = regexp.MustCompile(`^(\S+)\s*->\s*(.+)$`)
	rmFrontmatter  = regexp.MustCompile(`(?s)\A---\s*\n(.*?)\n---\s*\n`)

	validSdlcPhases = map[string]bool{
		"concept":        true,
		"requirements":   true,
		"design":         true,
		"implementation": true,
		"stabilization":  true,
		"release":        true,
	}
	validRoadmapStatuses = map[string]bool{
		"planned":     true,
		"in_progress": true,
		"blocked":     true,
		"done":        true,
	}
)

// PyFloat formats floating point values to match Python json.dumps(float):
// shortest round-trip representation, appending ".0" for integral values.
type PyFloat float64

func (f PyFloat) MarshalJSON() ([]byte, error) {
	v := float64(f)
	s := strconv.FormatFloat(v, 'g', -1, 64)
	if !strings.ContainsAny(s, ".eE") {
		s += ".0"
	}
	return []byte(s), nil
}

// pyReprStr formats a string using Python 3's repr(str) quoting/escaping rules.
func pyReprStr(s string) string {
	quote := '\''
	if strings.ContainsRune(s, '\'') && !strings.ContainsRune(s, '"') {
		quote = '"'
	}
	var b strings.Builder
	b.Grow(len(s) + 2)
	b.WriteRune(quote)
	for _, r := range s {
		switch r {
		case '\\':
			b.WriteString(`\\`)
		case '\n':
			b.WriteString(`\n`)
		case '\r':
			b.WriteString(`\r`)
		case '\t':
			b.WriteString(`\t`)
		case quote:
			b.WriteByte('\\')
			b.WriteRune(quote)
		default:
			if r < 0x20 || r == 0x7f {
				b.WriteString(fmt.Sprintf(`\x%02x`, r))
			} else {
				b.WriteRune(r)
			}
		}
	}
	b.WriteRune(quote)
	return b.String()
}

func pyListReprStr(items []string) string {
	parts := make([]string, len(items))
	for i, it := range items {
		parts[i] = pyReprStr(it)
	}
	return "[" + strings.Join(parts, ", ") + "]"
}

func IndexTextIsDraft(text string) bool {
	return indexDraftRe.MatchString(text)
}

type WbsNode struct {
	ID              string
	Title           string
	DeliverableNote string
	Children        []*WbsNode
}

type Milestone struct {
	ID              string
	Title           string
	SdlcPhase       string
	Status          string
	Order           int
	ParallelAllowed []string
	Deliverables    []string
	Goals           []string
	WbsGoals        map[string][]string
	Wbs             []*WbsNode
	SourcePath      string
	Number          int
}

type RoadmapIndexEntry struct {
	ID       string
	Status   string
	Path     string
	Position int
}

type Roadmap struct {
	IndexEntries []RoadmapIndexEntry
	Milestones   []Milestone
}

type RoadmapIssue struct {
	Code   string `json:"code"`
	Detail string `json:"detail"`
	Where  string `json:"where"`
}

type TaskWbsLink struct {
	ExemptReason string `json:"exempt_reason"`
	SourcePath   string `json:"source_path"`
	TaskID       string `json:"task_id"`
	TaskStatus   string `json:"task_status"`
	WbsRef       string `json:"wbs_ref"`
}

type WbsNodeState struct {
	Children      []WbsNodeState `json:"children"`
	DerivedStatus string         `json:"derived_status"`
	DoneLeaves    int            `json:"done_leaves"`
	ID            string         `json:"id"`
	LinkedTaskIDs []string       `json:"linked_task_ids"`
	Title         string         `json:"title"`
	TotalLeaves   int            `json:"total_leaves"`
}

type MilestoneState struct {
	DeclaredStatus      string         `json:"declared_status"`
	DeliverablesMissing []string       `json:"deliverables_missing"`
	DerivedStatus       string         `json:"derived_status"`
	DoneLeaves          int            `json:"done_leaves"`
	ID                  string         `json:"id"`
	Progress            PyFloat        `json:"progress"`
	SdlcPhase           string         `json:"sdlc_phase"`
	Title               string         `json:"title"`
	TotalLeaves         int            `json:"total_leaves"`
	Wbs                 []WbsNodeState `json:"wbs"`
}

type RoadmapState struct {
	CurrentMilestoneID *string          `json:"current_milestone_id"`
	ExemptTasks        []TaskWbsLink    `json:"exempt_tasks"`
	GeneratedAt        string           `json:"generated_at"`
	GeneratedBy        string           `json:"generated_by"`
	Issues             []RoadmapIssue   `json:"issues"`
	Milestones         []MilestoneState `json:"milestones"`
	SchemaVersion      int              `json:"schema_version"`
}

type WbsGateVerdict struct {
	Allowed     bool   `json:"allowed"`
	Code        string `json:"code"`
	Detail      string `json:"detail"`
	MilestoneID string `json:"milestone_id"`
}

func pyLStrip(s string) string {
	return strings.TrimLeftFunc(s, isPySpace)
}

func parseFrontmatterBlock(text string) (map[string]any, string) {
	loc := rmFrontmatter.FindStringSubmatchIndex(text)
	if loc == nil {
		return nil, text
	}
	block := text[loc[2]:loc[3]]
	body := text[loc[1]:]
	pairs := make(map[string]any)
	currentListKey := ""
	for _, raw := range splitPyLines(block) {
		stripped := pyStrip(raw)
		if stripped == "" || strings.HasPrefix(pyLStrip(raw), "#") {
			continue
		}
		if currentListKey != "" && strings.HasPrefix(stripped, "- ") {
			existing := pairs[currentListKey].([]string)
			existing = append(existing, pyStrip(stripped[2:]))
			pairs[currentListKey] = existing
			continue
		}
		currentListKey = ""
		key, val, ok := strings.Cut(raw, ":")
		if !ok {
			continue
		}
		key = pyStrip(key)
		val, _, _ = strings.Cut(val, "#")
		val = pyStrip(val)
		if val == "" {
			pairs[key] = make([]string, 0)
			currentListKey = key
		} else if strings.HasPrefix(val, "[") && strings.HasSuffix(val, "]") {
			inner := pyStrip(val[1 : len(val)-1])
			items := make([]string, 0)
			if inner != "" {
				for _, part := range strings.Split(inner, ",") {
					p := pyStrip(part)
					if p != "" {
						items = append(items, p)
					}
				}
			}
			pairs[key] = items
		} else {
			pairs[key] = val
		}
	}
	return pairs, body
}

func fmAsStr(pairs map[string]any, key string) string {
	v, ok := pairs[key]
	if !ok {
		return ""
	}
	s, ok := v.(string)
	if !ok {
		return ""
	}
	return s
}

func fmAsList(pairs map[string]any, key string) []string {
	v, ok := pairs[key]
	if !ok {
		return make([]string, 0)
	}
	arr, ok := v.([]string)
	if !ok {
		return make([]string, 0)
	}
	return arr
}

func parseWbsGoals(lines []string) map[string][]string {
	out := make(map[string][]string, len(lines))
	for _, line := range lines {
		s := pyStrip(line)
		m := wbsGoalsLineRe.FindStringSubmatch(s)
		if m == nil {
			out[s] = make([]string, 0)
			continue
		}
		node := pyStrip(m[1])
		goals := make([]string, 0)
		for _, part := range strings.Split(m[2], ",") {
			g := pyStrip(part)
			if g != "" {
				goals = append(goals, g)
			}
		}
		out[node] = goals
	}
	return out
}

func walkWbsIDs(nodes []*WbsNode) []string {
	var out []string
	for _, n := range nodes {
		out = append(out, n.ID)
		out = append(out, walkWbsIDs(n.Children)...)
	}
	return out
}

func parseWbsSection(body, sourcePath string) ([]*WbsNode, []RoadmapIssue) {
	issues := make([]RoadmapIssue, 0)
	roots := make([]*WbsNode, 0)
	type stackEntry struct {
		indent int
		node   *WbsNode
	}
	var stack []stackEntry
	seen := make(map[string]bool)
	inWbs := false

	for _, line := range splitPyLines(body) {
		if strings.HasPrefix(line, "## ") {
			inWbs = pyStrip(line) == "## WBS"
			continue
		}
		if !inWbs {
			continue
		}
		m := wbsLineRe.FindStringSubmatch(line)
		if m == nil {
			continue
		}
		indentStr, nodeID, rawTitle, rawNote := m[1], m[2], m[3], m[4]
		if seen[nodeID] {
			issues = append(issues, RoadmapIssue{
				Code:   "duplicate_wbs_id",
				Detail: "WBS id 중복: " + nodeID,
				Where:  sourcePath,
			})
			continue
		}
		if !wbsIDRe.MatchString(nodeID) {
			issues = append(issues, RoadmapIssue{
				Code:   "wbs_id_format",
				Detail: "WBS id 형식 위반: " + nodeID,
				Where:  sourcePath,
			})
			continue
		}
		seen[nodeID] = true
		title := pyStrip(rawTitle)
		note := pyStrip(rawNote)
		titleRunes := utf8.RuneCountInString(title)
		if titleRunes < 1 {
			issues = append(issues, RoadmapIssue{
				Code:   "wbs_node_invalid",
				Detail: nodeID + ": title String should have at least 1 character",
				Where:  sourcePath,
			})
			continue
		}
		if titleRunes > 200 {
			issues = append(issues, RoadmapIssue{
				Code:   "wbs_node_invalid",
				Detail: nodeID + ": title String should have at most 200 characters",
				Where:  sourcePath,
			})
			continue
		}
		node := &WbsNode{
			ID:              nodeID,
			Title:           title,
			DeliverableNote: note,
		}
		indent := len(indentStr)
		for len(stack) > 0 && stack[len(stack)-1].indent >= indent {
			stack = stack[:len(stack)-1]
		}
		if len(stack) > 0 {
			parent := stack[len(stack)-1].node
			parent.Children = append(parent.Children, node)
		} else {
			roots = append(roots, node)
		}
		stack = append(stack, stackEntry{indent: indent, node: node})
	}
	return roots, issues
}

func isASCIIDigits(s string) bool {
	if s == "" {
		return false
	}
	for i := 0; i < len(s); i++ {
		if s[i] < '0' || s[i] > '9' {
			return false
		}
	}
	return true
}

func ParseMilestoneText(text, sourcePath string) (*Milestone, []RoadmapIssue) {
	issues := make([]RoadmapIssue, 0)
	pairs, body := parseFrontmatterBlock(text)
	if len(pairs) == 0 {
		issues = append(issues, RoadmapIssue{
			Code:   "milestone_parse_error",
			Detail: "frontmatter 부재",
			Where:  sourcePath,
		})
		return nil, issues
	}
	wbsNodes, wbsIssues := parseWbsSection(body, sourcePath)
	issues = append(issues, wbsIssues...)

	phaseStr := fmAsStr(pairs, "sdlc_phase")
	if !validSdlcPhases[phaseStr] {
		issues = append(issues, RoadmapIssue{
			Code:   "milestone_parse_error",
			Detail: pyReprStr(phaseStr) + " is not a valid SdlcPhase",
			Where:  sourcePath,
		})
		return nil, issues
	}
	statusStr := fmAsStr(pairs, "status")
	if !validRoadmapStatuses[statusStr] {
		issues = append(issues, RoadmapIssue{
			Code:   "milestone_parse_error",
			Detail: pyReprStr(statusStr) + " is not a valid RoadmapItemStatus",
			Where:  sourcePath,
		})
		return nil, issues
	}

	idStr := fmAsStr(pairs, "id")
	titleStr := fmAsStr(pairs, "title")
	orderText := fmAsStr(pairs, "order")
	orderVal := -1
	if isASCIIDigits(orderText) {
		if parsed, err := strconv.Atoi(orderText); err == nil {
			orderVal = parsed
		}
	}
	goals := fmAsList(pairs, "goals")
	wbsGoals := parseWbsGoals(fmAsList(pairs, "wbs_goals"))

	var valErrs []string
	idMatch := milestoneIDRe.FindStringSubmatch(idStr)
	if idMatch == nil {
		valErrs = append(valErrs, "id Value error, milestone id 형식 위반 (M-NNN): "+pyReprStr(idStr))
	}
	if rc := utf8.RuneCountInString(titleStr); rc < 1 || rc > 200 {
		valErrs = append(valErrs, "title String length invalid")
	}
	if orderVal < 1 {
		valErrs = append(valErrs, "order Input should be greater than or equal to 1")
	}
	for _, gid := range goals {
		if !goalIDRe.MatchString(gid) {
			valErrs = append(valErrs, "goals Value error, goal id 형식 위반 (G<숫자>): "+pyReprStr(gid))
		}
	}
	for nodeID, gids := range wbsGoals {
		if !wbsIDRe.MatchString(nodeID) {
			valErrs = append(valErrs, "wbs_goals Value error, invalid WBS id: "+pyReprStr(nodeID))
			break
		}
		badGoal := false
		for _, gid := range gids {
			if !goalIDRe.MatchString(gid) {
				valErrs = append(valErrs, "wbs_goals Value error, invalid goal id: "+pyReprStr(gid))
				badGoal = true
				break
			}
		}
		if badGoal {
			break
		}
	}
	if len(valErrs) > 0 {
		issues = append(issues, RoadmapIssue{
			Code:   "milestone_parse_error",
			Detail: strings.Join(valErrs, "; "),
			Where:  sourcePath,
		})
		return nil, issues
	}

	num, _ := strconv.Atoi(idMatch[1])
	m := &Milestone{
		ID:              idStr,
		Title:           titleStr,
		SdlcPhase:       phaseStr,
		Status:          statusStr,
		Order:           orderVal,
		ParallelAllowed: fmAsList(pairs, "parallel_allowed"),
		Deliverables:    fmAsList(pairs, "deliverables"),
		Goals:           goals,
		WbsGoals:        wbsGoals,
		Wbs:             wbsNodes,
		SourcePath:      sourcePath,
		Number:          num,
	}

	for _, nodeID := range walkWbsIDs(m.Wbs) {
		wm := wbsIDRe.FindStringSubmatch(nodeID)
		if wm != nil {
			seg, _ := strconv.Atoi(wm[1])
			if seg != m.Number {
				issues = append(issues, RoadmapIssue{
					Code:   "wbs_milestone_number_mismatch",
					Detail: fmt.Sprintf("%s 의 첫 세그먼트가 %s 의 번호와 다르다", nodeID, m.ID),
					Where:  sourcePath,
				})
			}
		}
	}
	return m, issues
}

func ParseIndexText(text string) ([]RoadmapIndexEntry, []RoadmapIssue) {
	issues := make([]RoadmapIssue, 0)
	entries := make([]RoadmapIndexEntry, 0)
	var pending *[2]string
	position := 0

	for _, line := range splitPyLines(text) {
		if em := indexEntryRe.FindStringSubmatch(line); em != nil {
			if pending != nil {
				issues = append(issues, RoadmapIssue{
					Code:   "index_entry_without_path",
					Detail: "path 줄 부재: " + pending[0],
					Where:  RoadmapIndexFile,
				})
			}
			pending = &[2]string{em[1], em[4]}
			continue
		}
		if pm := indexPathRe.FindStringSubmatch(line); pm != nil && pending != nil {
			entryID, statusText := pending[0], pending[1]
			pending = nil
			position++
			if !validRoadmapStatuses[statusText] {
				issues = append(issues, RoadmapIssue{
					Code:   "index_status_vocab",
					Detail: fmt.Sprintf("%s status 어휘 밖: %s", entryID, pyReprStr(statusText)),
					Where:  RoadmapIndexFile,
				})
				continue
			}
			entries = append(entries, RoadmapIndexEntry{
				ID:       entryID,
				Status:   statusText,
				Path:     pm[1],
				Position: position,
			})
		}
	}
	if pending != nil {
		issues = append(issues, RoadmapIssue{
			Code:   "index_entry_without_path",
			Detail: "path 줄 부재: " + pending[0],
			Where:  RoadmapIndexFile,
		})
	}
	return entries, issues
}

func AssembleRoadmap(indexText string, milestoneTexts map[string]string) (*Roadmap, []RoadmapIssue) {
	issues := make([]RoadmapIssue, 0)
	entries, indexIssues := ParseIndexText(indexText)
	issues = append(issues, indexIssues...)

	milestones := make([]Milestone, 0)
	seenIDs := make(map[string]bool)
	filesByID := make(map[string]string)

	names := make([]string, 0, len(milestoneTexts))
	for name := range milestoneTexts {
		names = append(names, name)
	}
	sort.Strings(names)

	for _, name := range names {
		fm := milestoneFileRe.FindStringSubmatch(name)
		if fm == nil {
			issues = append(issues, RoadmapIssue{
				Code:   "milestone_filename_format",
				Detail: "파일명 형식 위반 (M-NNN-<slug>.md): " + name,
				Where:  name,
			})
			continue
		}
		m, mIssues := ParseMilestoneText(milestoneTexts[name], name)
		issues = append(issues, mIssues...)
		if m == nil {
			continue
		}
		if m.ID != fm[1] {
			issues = append(issues, RoadmapIssue{
				Code:   "index_id_mismatch",
				Detail: fmt.Sprintf("frontmatter id %s ≠ 파일명 %s", m.ID, fm[1]),
				Where:  name,
			})
			continue
		}
		if seenIDs[m.ID] {
			issues = append(issues, RoadmapIssue{
				Code:   "duplicate_milestone_id",
				Detail: "milestone id 중복: " + m.ID,
				Where:  name,
			})
			continue
		}
		seenIDs[m.ID] = true
		filesByID[m.ID] = name
		milestones = append(milestones, *m)
	}

	byID := make(map[string]Milestone, len(milestones))
	for _, m := range milestones {
		byID[m.ID] = m
	}

	for _, entry := range entries {
		m, ok := byID[entry.ID]
		if !ok {
			issues = append(issues, RoadmapIssue{
				Code:   "index_missing_file",
				Detail: fmt.Sprintf("index 가 가리키는 %s 의 파일이 없다", entry.ID),
				Where:  RoadmapIndexFile,
			})
			continue
		}
		if m.Order != entry.Position {
			where := filesByID[entry.ID]
			if where == "" {
				where = entry.ID
			}
			issues = append(issues, RoadmapIssue{
				Code:   "order_mismatch",
				Detail: fmt.Sprintf("%s: index 위치 %d ≠ frontmatter order %d", entry.ID, entry.Position, m.Order),
				Where:  where,
			})
		}
		if m.Status != entry.Status {
			where := filesByID[entry.ID]
			if where == "" {
				where = entry.ID
			}
			issues = append(issues, RoadmapIssue{
				Code:   "index_status_mismatch",
				Detail: fmt.Sprintf("%s: index status %s ≠ frontmatter status %s", entry.ID, entry.Status, m.Status),
				Where:  where,
			})
		}
	}

	indexedIDs := make(map[string]bool, len(entries))
	for _, entry := range entries {
		indexedIDs[entry.ID] = true
	}
	for _, m := range milestones {
		if !indexedIDs[m.ID] {
			issues = append(issues, RoadmapIssue{
				Code:   "index_entry_missing_for_file",
				Detail: m.ID + " 가 index 목록에 없다",
				Where:  m.SourcePath,
			})
		}
	}

	return &Roadmap{IndexEntries: entries, Milestones: milestones}, issues
}

func collectWbsRefs(r *Roadmap) (map[string]bool, map[string]bool) {
	leafRefs := make(map[string]bool)
	nonLeafRefs := make(map[string]bool)
	var collect func(node *WbsNode, mid string)
	collect = func(node *WbsNode, mid string) {
		ref := mid + "/" + node.ID
		if len(node.Children) > 0 {
			nonLeafRefs[ref] = true
			for _, child := range node.Children {
				collect(child, mid)
			}
		} else {
			leafRefs[ref] = true
		}
	}
	for _, m := range r.Milestones {
		for _, rootNode := range m.Wbs {
			collect(rootNode, m.ID)
		}
	}
	return leafRefs, nonLeafRefs
}

func JudgeWbs(r *Roadmap, isDraft bool, wbs *string, exemptReason *string) WbsGateVerdict {
	if isDraft {
		return WbsGateVerdict{
			Allowed:     true,
			Code:        "draft_roadmap",
			Detail:      "로드맵이 draft(소유자 미확정 초안)라 게이트가 아직 서지 않는다 — index.md 상태를 active 로 바꾸고 현재 마일스톤을 선언하면 발동한다.",
			MilestoneID: "",
		}
	}
	if r == nil || len(r.Milestones) == 0 {
		return WbsGateVerdict{
			Allowed:     true,
			Code:        "not_applicable",
			Detail:      "roadmap 을 읽지 못했다 — 게이트 해당 없음",
			MilestoneID: "",
		}
	}
	if wbs == nil || *wbs == "" {
		return WbsGateVerdict{
			Allowed:     false,
			Code:        "wbs_required",
			Detail:      "roadmap 이 있는 프로젝트의 task 생성은 --wbs <M-NNN/WBS-N.N> 가 필수다. 로드맵 밖 작업은 --wbs exempt --wbs-exempt-reason <사유> 로 선언한다 (스펙 §6-1).",
			MilestoneID: "",
		}
	}
	w := *wbs
	if w == WbsExemptValue {
		er := ""
		if exemptReason != nil {
			er = *exemptReason
		}
		if pyStrip(er) == "" {
			return WbsGateVerdict{
				Allowed:     false,
				Code:        "exempt_reason_required",
				Detail:      "--wbs exempt 는 --wbs-exempt-reason <사유> 가 필수다 — 우회는 침묵이 아니라 선언이다.",
				MilestoneID: "",
			}
		}
		return WbsGateVerdict{
			Allowed:     true,
			Code:        "exempt_declared",
			Detail:      "게이트 예외 선언: " + er,
			MilestoneID: "",
		}
	}

	rmMatch := wbsRefRe.FindStringSubmatch(w)
	if rmMatch == nil {
		return WbsGateVerdict{
			Allowed:     false,
			Code:        "wbs_ref_format",
			Detail:      fmt.Sprintf("wbs 참조 형식 위반: %s — 'M-NNN/WBS-N.N' 형태여야 한다.", pyReprStr(w)),
			MilestoneID: "",
		}
	}
	mid := rmMatch[1]
	leafRefs, nonLeafRefs := collectWbsRefs(r)
	if nonLeafRefs[w] {
		return WbsGateVerdict{
			Allowed:     false,
			Code:        "wbs_not_leaf",
			Detail:      w + " 는 leaf 가 아니다 — task 는 leaf 에만 연결한다 (스펙 §3.2).",
			MilestoneID: mid,
		}
	}
	if !leafRefs[w] {
		return WbsGateVerdict{
			Allowed:     false,
			Code:        "wbs_dangling",
			Detail:      w + " 가 로드맵에 없다 — 로드맵에 leaf 를 먼저 선언한다.",
			MilestoneID: mid,
		}
	}

	var target *Milestone
	for i := range r.Milestones {
		if r.Milestones[i].ID == mid {
			target = &r.Milestones[i]
			break
		}
	}
	if target.Status == "done" {
		return WbsGateVerdict{
			Allowed:     false,
			Code:        "milestone_done",
			Detail:      mid + " 는 done 선언이다 — 일이 남았다면 마일스톤 status 를 먼저 되돌린다 (스펙 §6-3).",
			MilestoneID: mid,
		}
	}
	for _, earlier := range r.Milestones {
		if earlier.Order >= target.Order || earlier.Status == "done" {
			continue
		}
		if containsStr(target.ParallelAllowed, earlier.ID) || containsStr(earlier.ParallelAllowed, target.ID) {
			continue
		}
		return WbsGateVerdict{
			Allowed:     false,
			Code:        "sdlc_order",
			Detail:      fmt.Sprintf("앞선 마일스톤 %s(%s)가 끝나지 않았다 — 먼저 닫거나, 병행이 맞다면 로드맵의 parallel_allowed 에 선언한다 (스펙 §6-2).", earlier.ID, earlier.Status),
			MilestoneID: mid,
		}
	}
	return WbsGateVerdict{
		Allowed:     true,
		Code:        "linked",
		Detail:      w + " 에 연결",
		MilestoneID: mid,
	}
}

func containsStr(slice []string, item string) bool {
	for _, s := range slice {
		if s == item {
			return true
		}
	}
	return false
}

func deriveLeafStatus(taskStatuses []string) string {
	if len(taskStatuses) == 0 {
		return "planned"
	}
	set := make(map[string]bool, len(taskStatuses))
	for _, s := range taskStatuses {
		set[s] = true
	}
	if len(set) == 1 && set["done"] {
		return "done"
	}
	if set["in_progress"] {
		return "in_progress"
	}
	if set["blocked"] {
		return "blocked"
	}
	if set["done"] {
		return "in_progress"
	}
	return "planned"
}

func deriveNodeState(node *WbsNode, mid string, linksByRef map[string][]TaskWbsLink) WbsNodeState {
	if len(node.Children) > 0 {
		childStates := make([]WbsNodeState, 0, len(node.Children))
		total := 0
		done := 0
		statuses := make(map[string]bool)
		for _, child := range node.Children {
			cs := deriveNodeState(child, mid, linksByRef)
			childStates = append(childStates, cs)
			total += cs.TotalLeaves
			done += cs.DoneLeaves
			statuses[cs.DerivedStatus] = true
		}
		var derived string
		if len(statuses) == 1 && statuses["done"] {
			derived = "done"
		} else if len(statuses) == 1 && statuses["planned"] {
			derived = "planned"
		} else if statuses["blocked"] && !statuses["in_progress"] {
			derived = "blocked"
		} else {
			derived = "in_progress"
		}
		return WbsNodeState{
			Children:      childStates,
			DerivedStatus: derived,
			DoneLeaves:    done,
			ID:            node.ID,
			LinkedTaskIDs: make([]string, 0),
			Title:         node.Title,
			TotalLeaves:   total,
		}
	}
	linked := linksByRef[mid+"/"+node.ID]
	taskStatuses := make([]string, len(linked))
	taskIDs := make([]string, len(linked))
	for i, l := range linked {
		taskStatuses[i] = l.TaskStatus
		taskIDs[i] = l.TaskID
	}
	derived := deriveLeafStatus(taskStatuses)
	doneLeaves := 0
	if derived == "done" {
		doneLeaves = 1
	}
	return WbsNodeState{
		Children:      make([]WbsNodeState, 0),
		DerivedStatus: derived,
		DoneLeaves:    doneLeaves,
		ID:            node.ID,
		LinkedTaskIDs: taskIDs,
		Title:         node.Title,
		TotalLeaves:   1,
	}
}

func currentMilestoneID(milestones []Milestone) *string {
	var openMs []Milestone
	for _, m := range milestones {
		if m.Status == "in_progress" {
			openMs = append(openMs, m)
		}
	}
	if len(openMs) == 0 {
		return nil
	}
	sort.SliceStable(openMs, func(i, j int) bool {
		return openMs[i].Order < openMs[j].Order
	})
	bg := make(map[string]bool)
	for _, m := range openMs {
		for _, pid := range m.ParallelAllowed {
			if pid != m.ID {
				bg[pid] = true
			}
		}
	}
	for _, m := range openMs {
		if !bg[m.ID] {
			id := m.ID
			return &id
		}
	}
	id := openMs[0].ID
	return &id
}

func DeriveRoadmapState(
	r *Roadmap,
	links []TaskWbsLink,
	baseIssues []RoadmapIssue,
	deliverableExists func(string) bool,
	generatedAt string,
) RoadmapState {
	issues := make([]RoadmapIssue, len(baseIssues))
	copy(issues, baseIssues)

	leafRefs, nonLeafRefs := collectWbsRefs(r)
	linksByRef := make(map[string][]TaskWbsLink)
	exemptTasks := make([]TaskWbsLink, 0)

	for _, link := range links {
		if link.WbsRef == WbsExemptValue {
			if link.ExemptReason == "" {
				issues = append(issues, RoadmapIssue{
					Code:   "exempt_without_reason",
					Detail: link.TaskID + ": wbs=exempt 인데 사유 선언이 없다",
					Where:  link.SourcePath,
				})
			}
			exemptTasks = append(exemptTasks, link)
			continue
		}
		if !wbsRefRe.MatchString(link.WbsRef) {
			issues = append(issues, RoadmapIssue{
				Code:   "wbs_ref_format",
				Detail: fmt.Sprintf("%s: wbs 참조 형식 위반: %s", link.TaskID, pyReprStr(link.WbsRef)),
				Where:  link.SourcePath,
			})
			continue
		}
		if nonLeafRefs[link.WbsRef] {
			issues = append(issues, RoadmapIssue{
				Code:   "wbs_link_not_leaf",
				Detail: fmt.Sprintf("%s: %s 는 leaf 가 아니다", link.TaskID, link.WbsRef),
				Where:  link.SourcePath,
			})
			continue
		}
		if !leafRefs[link.WbsRef] {
			issues = append(issues, RoadmapIssue{
				Code:   "wbs_dangling_link",
				Detail: fmt.Sprintf("%s: %s 가 로드맵에 없다", link.TaskID, link.WbsRef),
				Where:  link.SourcePath,
			})
			continue
		}
		linksByRef[link.WbsRef] = append(linksByRef[link.WbsRef], link)
	}

	sortedMs := make([]Milestone, len(r.Milestones))
	copy(sortedMs, r.Milestones)
	sort.SliceStable(sortedMs, func(i, j int) bool {
		return sortedMs[i].Order < sortedMs[j].Order
	})

	sortedRefs := make([]string, 0, len(linksByRef))
	for ref := range linksByRef {
		sortedRefs = append(sortedRefs, ref)
	}
	// Note: in Python dict preserves insertion order (order of `links`!).
	// Track ref order as first seen in linksByRef:
	var seenRefOrder []string
	seenRefSet := make(map[string]bool)
	for _, link := range links {
		if _, ok := linksByRef[link.WbsRef]; ok && !seenRefSet[link.WbsRef] {
			seenRefSet[link.WbsRef] = true
			seenRefOrder = append(seenRefOrder, link.WbsRef)
		}
	}
	_ = sortedRefs

	milestoneStates := make([]MilestoneState, 0, len(sortedMs))
	for _, m := range sortedMs {
		wbsStates := make([]WbsNodeState, 0, len(m.Wbs))
		total := 0
		done := 0
		statuses := make(map[string]bool)
		for _, node := range m.Wbs {
			ns := deriveNodeState(node, m.ID, linksByRef)
			wbsStates = append(wbsStates, ns)
			total += ns.TotalLeaves
			done += ns.DoneLeaves
			statuses[ns.DerivedStatus] = true
		}

		missing := make([]string, 0)
		for _, d := range m.Deliverables {
			if !deliverableExists(d) {
				missing = append(missing, d)
			}
		}

		allLeavesDone := total > 0 && done == total
		var derived string
		if allLeavesDone && len(missing) == 0 {
			derived = "done"
		} else if allLeavesDone && len(missing) > 0 {
			derived = "in_progress"
		} else if len(statuses) == 0 || (len(statuses) == 1 && statuses["planned"]) {
			derived = "planned"
		} else if statuses["blocked"] && !statuses["in_progress"] {
			derived = "blocked"
		} else {
			derived = "in_progress"
		}

		if m.Status == "done" && len(missing) > 0 {
			issues = append(issues, RoadmapIssue{
				Code:   "deliverable_missing",
				Detail: fmt.Sprintf("%s: done 선언인데 산출물 부재: %s", m.ID, pyListReprStr(missing)),
				Where:  m.SourcePath,
			})
		}

		declaredDone := m.Status == "done"
		derivedDone := derived == "done"
		if declaredDone != derivedDone {
			issues = append(issues, RoadmapIssue{
				Code:   "declared_derived_mismatch",
				Detail: fmt.Sprintf("%s: 선언 %s ≠ 파생 %s (done 경계)", m.ID, m.Status, derived),
				Where:  m.SourcePath,
			})
		}

		if m.Status == "done" {
			prefix := m.ID + "/"
			for _, ref := range seenRefOrder {
				if strings.HasPrefix(ref, prefix) {
					var openTasks []string
					for _, l := range linksByRef[ref] {
						if l.TaskStatus == "planned" || l.TaskStatus == "in_progress" || l.TaskStatus == "blocked" {
							openTasks = append(openTasks, l.TaskID)
						}
					}
					if len(openTasks) > 0 {
						issues = append(issues, RoadmapIssue{
							Code:   "done_milestone_open_task",
							Detail: fmt.Sprintf("%s: done 선언 아래 열린 task %s", m.ID, pyListReprStr(openTasks)),
							Where:  m.SourcePath,
						})
					}
				}
			}
		}

		var prog PyFloat
		if total > 0 {
			prog = PyFloat(float64(done) / float64(total))
		}
		milestoneStates = append(milestoneStates, MilestoneState{
			DeclaredStatus:      m.Status,
			DeliverablesMissing: missing,
			DerivedStatus:       derived,
			DoneLeaves:          done,
			ID:                  m.ID,
			Progress:            prog,
			SdlcPhase:           m.SdlcPhase,
			Title:               m.Title,
			TotalLeaves:         total,
			Wbs:                 wbsStates,
		})
	}

	return RoadmapState{
		CurrentMilestoneID: currentMilestoneID(r.Milestones),
		ExemptTasks:        exemptTasks,
		GeneratedAt:        generatedAt,
		GeneratedBy:        RoadmapGenBy,
		Issues:             issues,
		Milestones:         milestoneStates,
		SchemaVersion:      RoadmapSchemaVer,
	}
}
