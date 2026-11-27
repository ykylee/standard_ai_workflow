package judge

import (
	"encoding/json"
	"path"
	"regexp"
	"sort"
	"strings"
	"time"
	"unicode/utf8"
)

const (
	recentDoneItemsCap         = 10
	memoryEntriesSchemaVersion = "2"
	pointerAbstractionMaxChars = 120
	missingStatusMarker        = "<미기재>"
)

var (
	purposeFmRe       = regexp.MustCompile(`(?s)\A---\n(.+?)\n---`)
	purposeReviewRe   = regexp.MustCompile(`last_purpose_review\s*:\s*(\d{4}-\d{2}-\d{2})`)
	purposeGoalRe     = regexp.MustCompile(`(?m)^- \*\*G\d+\*\*\s*:\s*(.+)$`)
	taskRecencyFields = []string{"completed_at", "updated_at", "created_at"}
	isoDateFieldRes   = map[string]*regexp.Regexp{
		"completed_at": regexp.MustCompile(`(?m)^completed_at\s*:\s*(\d{4}-\d{2}-\d{2})`),
		"updated_at":   regexp.MustCompile(`(?m)^updated_at\s*:\s*(\d{4}-\d{2}-\d{2})`),
		"created_at":   regexp.MustCompile(`(?m)^created_at\s*:\s*(\d{4}-\d{2}-\d{2})`),
	}
	taskIDPattern        = `TASK-\d{4}-\d{2}-\d{2}(?:-[A-Za-z0-9._-]+?)?-\d{3}`
	taskIDCaptureRe      = regexp.MustCompile(`^TASK-(?:(\d{4}-\d{2}-\d{2})-)?(?:(.+?)-)?(\d{1,3})$`)
	taskHeaderRe         = regexp.MustCompile(`^#{1,2}\s+(TASK-[A-Za-z0-9._-]+)\s+(.+)$`)
	workItemIDRe         = regexp.MustCompile(`^(` + workItemIDPattern + `)\b`)
	dailyFileNameRe      = regexp.MustCompile(`^\d{4}-\d{2}-\d{2}\.md$`)
	dailyEntryHeadRe     = regexp.MustCompile(`(?m)^-\s+\*\*(` + taskIDPattern + `)\*\*`)
	dailyBlockStatusRe   = regexp.MustCompile(`(?m)^\s*-\s*status:\s*(\S+)\s*$`)
	dailyDoneTitleRe     = regexp.MustCompile(`^\[[^\]]+\]\s+(.+)$`)
	backtickPathRe       = regexp.MustCompile("(?m)^\\s*-?\\s*path:\\s*`([^`]+)`")
	taskFmTrailingRe     = regexp.MustCompile(`(?s)\A---\n(.*?)\n---\n`)
	taskFmNoTrailRe      = regexp.MustCompile(`(?s)\A---\n(.+?)\n---`)
	fmIDRe               = regexp.MustCompile(`(?m)^id:\s*(\S+)`)
	fmStatusRe           = regexp.MustCompile(`(?m)^status:\s*(\S+)`)
	fmStatusStrictRe     = regexp.MustCompile(`(?m)^status:\s*(\S+)\s*$`)
	bodyStatusLineRe     = regexp.MustCompile(`^- (?:상태|Status):`)
	statusLineRe         = regexp.MustCompile(`^- (?:상태|Status):\s*(planned|in_progress|blocked|done)\s*$`)
	modeLineRe           = regexp.MustCompile(`^- 모드:\s*(Analysis|Requirements|Design|Planning|Implementation|Refactoring)\s*$`)
	indexDateCandidateRe = regexp.MustCompile(`(\.?\.?/.*\d{4}-\d{2}-\d{2}\.md)`)
	indexDatePresentRe   = regexp.MustCompile(`\d{4}-\d{2}-\d{2}\.md`)
	memEntryIDRe         = regexp.MustCompile(`^MEM-\d{4}-\d{2}-\d{2}-\d{3}$`)
	validTaskStatuses    = map[string]bool{
		"planned":     true,
		"in_progress": true,
		"blocked":     true,
		"done":        true,
	}
	planMarkers = []string{"- 주장:", "- Claims:", "- 결정:", "- Decisions:"}
)

func pyStrFieldsJoin(s string) string {
	// Python " ".join(s.strip().split())
	parts := strings.FieldsFunc(s, isPySpace)
	return strings.Join(parts, " ")
}

func normalizeBackticked(v string) string {
	n := pyStrip(v)
	if strings.HasPrefix(n, "`") && strings.HasSuffix(n, "`") && len(n) >= 2 {
		n = pyStrip(n[1 : len(n)-1])
	}
	return pyStrFieldsJoin(n)
}

func dedupeStrings(items []string) []string {
	seen := make(map[string]bool)
	out := make([]string, 0)
	for _, it := range items {
		norm := pyStrFieldsJoin(it)
		if norm != "" && !seen[norm] {
			seen[norm] = true
			out = append(out, norm)
		}
	}
	return out
}

func dedupeNormalizedBackticked(items []string) []string {
	seen := make(map[string]bool)
	out := make([]string, 0)
	for _, it := range items {
		norm := normalizeBackticked(it)
		if norm != "" && !seen[norm] {
			seen[norm] = true
			out = append(out, norm)
		}
	}
	return out
}

func dedupeWorkItems(items []string) []string {
	seen := make(map[string]bool)
	out := make([]string, 0)
	for _, it := range items {
		norm := normalizeBackticked(it)
		key := norm
		if m := workItemIDRe.FindStringSubmatch(norm); m != nil {
			key = m[1]
		}
		if norm != "" && !seen[key] {
			seen[key] = true
			out = append(out, norm)
		}
	}
	return out
}

func isMeaningfulText(v *string) bool {
	if v == nil {
		return false
	}
	s := pyStrip(*v)
	return s != "" && !strings.HasPrefix(s, "TODO:")
}

func isMeaningfulStr(s string) bool {
	t := pyStrip(s)
	return t != "" && !strings.HasPrefix(t, "TODO:")
}

type virtualFS struct {
	files map[string]string // universal-newline normalized content keyed by clean POSIX relpath
	dirs  map[string]bool   // directory paths (e.g. "ai-workflow/memory/active/main/backlog")
}

func newVirtualFS(raw map[string]string) virtualFS {
	files := make(map[string]string, len(raw))
	dirs := make(map[string]bool)
	for k, v := range raw {
		clean := path.Clean(k)
		files[clean] = normalizeUniversalNewlines(v)
		d := path.Dir(clean)
		for d != "." && d != "/" && d != "" {
			dirs[d] = true
			d = path.Dir(d)
		}
	}
	return virtualFS{files: files, dirs: dirs}
}

func (v virtualFS) fileExists(p string) bool {
	_, ok := v.files[p]
	return ok
}

func (v virtualFS) dirExists(p string) bool {
	return v.dirs[p]
}

func (v virtualFS) exists(p string) bool {
	if p == "" || p == "." {
		return true
	}
	return v.fileExists(p) || v.dirExists(p)
}

func (v virtualFS) resolveFrom(baseDir, rawRel string) (string, bool) {
	// Resolve relative POSIX path inside workspace; reject escape above root ("..").
	if strings.HasPrefix(rawRel, "/") {
		return "", false
	}
	joined := rawRel
	if baseDir != "" && baseDir != "." {
		joined = baseDir + "/" + rawRel
	}
	cleaned := path.Clean(joined)
	if cleaned == ".." || strings.HasPrefix(cleaned, "../") {
		return "", false
	}
	return cleaned, true
}

func (v virtualFS) directFiles(dir string) []string {
	prefix := ""
	if dir != "" && dir != "." {
		prefix = dir + "/"
	}
	var out []string
	for p := range v.files {
		if !strings.HasPrefix(p, prefix) {
			continue
		}
		rest := p[len(prefix):]
		if rest != "" && !strings.ContainsRune(rest, '/') {
			out = append(out, p)
		}
	}
	sort.Strings(out)
	return out
}

func parsePurposeSummary(text string) (*string, *string) {
	var rev *string
	if fm := purposeFmRe.FindStringSubmatch(text); fm != nil {
		if rm := purposeReviewRe.FindStringSubmatch(fm[1]); rm != nil {
			s := rm[1]
			rev = &s
		}
	}
	var digest *string
	if gm := purposeGoalRe.FindStringSubmatch(text); gm != nil {
		s := pyStrip(gm[1])
		digest = &s
	}
	return digest, rev
}

func taskRecencyKey(frontmatter, taskID string) string {
	for _, field := range taskRecencyFields {
		if m := isoDateFieldRes[field].FindStringSubmatch(frontmatter); m != nil {
			return m[1]
		}
	}
	if m := taskIDCaptureRe.FindStringSubmatch(taskID); m != nil && m[1] != "" {
		return m[1]
	}
	return ""
}

type doneRecord struct {
	recency string
	taskID  string
	prose   string
}

type appendonlyAgg struct {
	inProgress    []string
	planned       []string
	blocked       []string
	done          []string
	recentDone    []string
	unknownStatus []string
	sessions      []string
}

func aggregateFromAppendonly(vfs virtualFS, dailyDir, tasksDir, sessionsDir string) appendonlyAgg {
	var agg appendonlyAgg
	known := make(map[string]bool)
	doneSet := make(map[string]bool)
	var doneRecords []doneRecord

	if tasksDir != "" && vfs.dirExists(tasksDir) {
		for _, p := range vfs.directFiles(tasksDir) {
			name := path.Base(p)
			if !strings.HasPrefix(name, "TASK-") || !strings.HasSuffix(name, ".md") {
				continue
			}
			text := vfs.files[p]
			fm := taskFmNoTrailRe.FindStringSubmatch(text)
			if fm == nil {
				continue
			}
			frontmatter := fm[1]
			idM := fmIDRe.FindStringSubmatch(frontmatter)
			if idM == nil {
				continue
			}
			taskID := idM[1]
			known[taskID] = true
			stM := fmStatusRe.FindStringSubmatch(frontmatter)
			if stM == nil {
				agg.unknownStatus = append(agg.unknownStatus, taskID+": "+missingStatusMarker)
				continue
			}
			status := stM[1]
			if !validTaskStatuses[status] {
				agg.unknownStatus = append(agg.unknownStatus, taskID+": "+status)
				continue
			}
			switch status {
			case "in_progress":
				agg.inProgress = append(agg.inProgress, taskID)
			case "planned":
				agg.planned = append(agg.planned, taskID)
			case "blocked":
				agg.blocked = append(agg.blocked, taskID)
			case "done":
				agg.done = append(agg.done, taskID)
				doneSet[taskID] = true
				var prose string
				for _, line := range splitPyLines(text) {
					if strings.HasPrefix(line, "# ") {
						prose = pyStrip(line[2:])
						break
					}
				}
				if prose == "" {
					prose = taskID
				}
				doneRecords = append(doneRecords, doneRecord{
					recency: taskRecencyKey(frontmatter, taskID),
					taskID:  taskID,
					prose:   prose,
				})
			}
		}
	}

	if dailyDir != "" && vfs.dirExists(dailyDir) {
		for _, p := range vfs.directFiles(dailyDir) {
			name := path.Base(p)
			if !dailyFileNameRe.MatchString(name) {
				continue
			}
			dailyDate := strings.TrimSuffix(name, ".md")
			text := vfs.files[p]
			matches := dailyEntryHeadRe.FindAllStringSubmatchIndex(text, -1)
			for idx, m := range matches {
				start := m[0]
				end := len(text)
				if idx+1 < len(matches) {
					end = matches[idx+1][0]
				}
				block := text[start:end]
				taskID := text[m[2]:m[3]]
				if known[taskID] || doneSet[taskID] {
					continue
				}
				known[taskID] = true
				status := "done"
				if sm := dailyBlockStatusRe.FindStringSubmatch(block); sm != nil {
					status = sm[1]
				}
				if !validTaskStatuses[status] {
					agg.unknownStatus = append(agg.unknownStatus, taskID+": "+status)
					continue
				}
				switch status {
				case "in_progress":
					agg.inProgress = append(agg.inProgress, taskID)
				case "planned":
					agg.planned = append(agg.planned, taskID)
				case "blocked":
					agg.blocked = append(agg.blocked, taskID)
				case "done":
					agg.done = append(agg.done, taskID)
					doneSet[taskID] = true
					rest := splitPyLines(text[m[1]:end])
					after := ""
					if len(rest) > 0 {
						after = pyStrip(rest[0])
					}
					title := taskID
					if tm := dailyDoneTitleRe.FindStringSubmatch(after); tm != nil {
						title = pyStrip(tm[1])
					}
					doneRecords = append(doneRecords, doneRecord{
						recency: dailyDate,
						taskID:  taskID,
						prose:   title,
					})
				}
			}
		}
	}

	if sessionsDir != "" && vfs.dirExists(sessionsDir) {
		for _, p := range vfs.directFiles(sessionsDir) {
			name := path.Base(p)
			if strings.HasSuffix(name, ".md") {
				agg.sessions = append(agg.sessions, strings.TrimSuffix(name, ".md"))
			}
		}
	}

	sort.SliceStable(doneRecords, func(i, j int) bool {
		if doneRecords[i].recency != doneRecords[j].recency {
			return doneRecords[i].recency > doneRecords[j].recency
		}
		return doneRecords[i].taskID > doneRecords[j].taskID
	})
	for _, r := range doneRecords {
		agg.recentDone = append(agg.recentDone, r.prose)
	}
	return agg
}

func taskLinesWithFrontmatterStatus(text string) []string {
	lines := splitPyLines(text)
	fm := taskFmTrailingRe.FindStringSubmatch(text)
	if fm == nil {
		return lines
	}
	st := fmStatusStrictRe.FindStringSubmatch(fm[1])
	if st == nil {
		return lines
	}
	kept := make([]string, 0, len(lines))
	for _, ln := range lines {
		if !bodyStatusLineRe.MatchString(pyStrip(ln)) {
			kept = append(kept, ln)
		}
	}
	for i, line := range kept {
		if taskHeaderRe.MatchString(pyStrip(line)) {
			out := make([]string, 0, len(kept)+1)
			out = append(out, kept[:i+1]...)
			out = append(out, "- Status: "+st[1])
			out = append(out, kept[i+1:]...)
			return out
		}
	}
	return lines
}

func findLatestDailyBacklog(vfs virtualFS, dailyDir string) string {
	if dailyDir == "" || !vfs.dirExists(dailyDir) {
		return ""
	}
	latest := ""
	for _, p := range vfs.directFiles(dailyDir) {
		if dailyFileNameRe.MatchString(path.Base(p)) {
			latest = p
		}
	}
	return latest
}

func findLatestBacklogFromIndex(vfs virtualFS, indexPath string) string {
	text := vfs.files[indexPath]
	baseDir := path.Dir(indexPath)
	targets := iterMarkdownLinkTargets(text)
	if len(targets) > 0 {
		last := targets[len(targets)-1]
		if resolved, ok := vfs.resolveFrom(baseDir, last); ok {
			return resolved
		}
	}
	var dateCandidates []string
	for _, line := range splitPyLines(text) {
		stripped := pyStrip(line)
		if indexDatePresentRe.MatchString(stripped) {
			if m := indexDateCandidateRe.FindStringSubmatch(stripped); m != nil {
				if resolved, ok := vfs.resolveFrom(baseDir, m[1]); ok {
					dateCandidates = append(dateCandidates, resolved)
				}
			}
		}
	}
	if len(dateCandidates) > 0 {
		return dateCandidates[len(dateCandidates)-1]
	}
	return ""
}

func linkedTaskPathsForBacklog(vfs virtualFS, backlogPath string) []string {
	text := vfs.files[backlogPath]
	baseDir := path.Dir(backlogPath)
	parentDir := path.Dir(baseDir)
	seen := make(map[string]bool)
	var out []string

	add := func(raw string) {
		cand, ok := vfs.resolveFrom(baseDir, raw)
		if !ok || !vfs.fileExists(cand) {
			cand, ok = vfs.resolveFrom(parentDir, raw)
			if !ok {
				return
			}
		}
		if vfs.fileExists(cand) && path.Base(path.Dir(cand)) == "tasks" && !seen[cand] {
			seen[cand] = true
			out = append(out, cand)
		}
	}

	for _, target := range iterMarkdownLinkTargets(text) {
		add(target)
	}
	for _, m := range backtickPathRe.FindAllStringSubmatch(text, -1) {
		add(pyStrip(m[1]))
	}
	return out
}

type parsedBacklogTask struct {
	taskID string
	title  string
	status string
}

type backlogParseResult struct {
	tasks      []parsedBacklogTask
	inProgress []string
	blocked    []string
	done       []string
}

func parseBacklogVirtual(vfs virtualFS, backlogPath string) backlogParseResult {
	var lines []string
	text := vfs.files[backlogPath]
	origLines := splitPyLines(text)
	hasInlineHeader := false
	for _, line := range origLines {
		if taskHeaderRe.MatchString(pyStrip(line)) {
			hasInlineHeader = true
			break
		}
	}
	linked := linkedTaskPathsForBacklog(vfs, backlogPath)
	if len(linked) > 0 && !hasInlineHeader {
		for _, tp := range linked {
			lines = append(lines, taskLinesWithFrontmatterStatus(vfs.files[tp])...)
			lines = append(lines, "")
		}
	} else if len(linked) == 0 && !hasInlineHeader {
		stem := strings.TrimSuffix(path.Base(backlogPath), ".md")
		tasksSubdir := path.Dir(backlogPath) + "/tasks"
		var fallback []string
		for _, p := range vfs.directFiles(tasksSubdir) {
			base := path.Base(p)
			if strings.HasPrefix(base, "TASK-"+stem) && strings.HasSuffix(base, ".md") {
				fallback = append(fallback, p)
			}
		}
		if len(fallback) > 0 {
			for _, tp := range fallback {
				lines = append(lines, taskLinesWithFrontmatterStatus(vfs.files[tp])...)
				lines = append(lines, "")
			}
		} else {
			lines = origLines
		}
	} else {
		lines = origLines
	}

	var tasks []parsedBacklogTask
	var current *parsedBacklogTask
	for _, line := range lines {
		stripped := pyStrip(line)
		if hm := taskHeaderRe.FindStringSubmatch(stripped); hm != nil {
			if current != nil {
				tasks = append(tasks, *current)
			}
			current = &parsedBacklogTask{taskID: hm[1], title: hm[2]}
			continue
		}
		if current == nil {
			continue
		}
		if sm := statusLineRe.FindStringSubmatch(stripped); sm != nil {
			current.status = sm[1]
		}
	}
	if current != nil {
		tasks = append(tasks, *current)
	}

	res := backlogParseResult{
		tasks:      tasks,
		inProgress: make([]string, 0),
		blocked:    make([]string, 0),
		done:       make([]string, 0),
	}
	for _, t := range tasks {
		label := t.taskID + " " + t.title
		switch t.status {
		case "in_progress":
			res.inProgress = append(res.inProgress, label)
		case "blocked":
			res.blocked = append(res.blocked, label)
		case "done":
			res.done = append(res.done, label)
		}
	}
	return res
}

type memoryEntryRaw struct {
	ID                 string   `json:"id"`
	SchemaVersion      *int     `json:"schema_version"`
	PrimaryAbstraction string   `json:"primary_abstraction"`
	MergeState         string   `json:"merge_state"`
	RelatedIDs         []string `json:"related_ids"`
	CreatedAt          string   `json:"created_at"`
	UpdatedAt          string   `json:"updated_at"`
}

func isValidISODateTime(s string) bool {
	if s == "" {
		return false
	}
	layouts := []string{
		time.RFC3339Nano,
		time.RFC3339,
		"2006-01-02T15:04:05.999999999",
		"2006-01-02T15:04:05",
		"2006-01-02 15:04:05",
		"2006-01-02",
	}
	for _, l := range layouts {
		if _, err := time.Parse(l, s); err == nil {
			return true
		}
	}
	return false
}

func collectMemoryEntryPointers(vfs virtualFS, memoryIndexRoot string) []map[string]string {
	entriesDir := memoryIndexRoot + "/entries"
	if !vfs.dirExists(entriesDir) {
		return nil
	}
	var out []map[string]string
	for _, p := range vfs.directFiles(entriesDir) {
		if !strings.HasSuffix(p, ".json") {
			continue
		}
		var e memoryEntryRaw
		if err := json.Unmarshal([]byte(vfs.files[p]), &e); err != nil {
			continue
		}
		if !memEntryIDRe.MatchString(e.ID) {
			continue
		}
		paRunes := utf8.RuneCountInString(e.PrimaryAbstraction)
		if paRunes < 1 || paRunes > 200 {
			continue
		}
		if e.SchemaVersion != nil && (*e.SchemaVersion < 1 || *e.SchemaVersion > 99) {
			continue
		}
		if e.MergeState != "" && e.MergeState != "active" && e.MergeState != "linked" && e.MergeState != "merged" {
			continue
		}
		if len(e.RelatedIDs) > 16 {
			continue
		}
		if !isValidISODateTime(e.CreatedAt) || !isValidISODateTime(e.UpdatedAt) {
			continue
		}
		pa := e.PrimaryAbstraction
		if paRunes > pointerAbstractionMaxChars {
			pa = firstRunes(pa, pointerAbstractionMaxChars-1) + "…"
		}
		out = append(out, map[string]string{
			"id":                  e.ID,
			"primary_abstraction": pa,
			"path":                entriesDir + "/" + e.ID + ".json",
		})
	}
	return out
}

func collectColumnOpenDecisions(vfs virtualFS, tasksDir string) map[string]int {
	if tasksDir == "" || !vfs.dirExists(tasksDir) {
		return nil
	}
	counts := make(map[string]int)
	for _, p := range vfs.directFiles(tasksDir) {
		name := path.Base(p)
		if !strings.HasPrefix(name, "TASK-") || !strings.HasSuffix(name, ".md") {
			continue
		}
		text := vfs.files[p]
		hasMarker := false
		for _, m := range planMarkers {
			if strings.Contains(text, m) {
				hasMarker = true
				break
			}
		}
		if !hasMarker {
			continue
		}
		fm := taskFmNoTrailRe.FindStringSubmatch(text)
		if fm == nil {
			continue
		}
		idM := fmIDRe.FindStringSubmatch(fm[1])
		if idM == nil {
			continue
		}
		stM := fmStatusRe.FindStringSubmatch(fm[1])
		if stM == nil {
			continue
		}
		status := stM[1]
		if status != "in_progress" && status != "blocked" && status != "planned" {
			continue
		}
		plan := ParsePlan(splitPyLines(text))
		if plan.Empty() {
			continue
		}
		opened := ColumnOpenDecisionIDs(plan)
		if len(opened) > 0 {
			counts[idM[1]] = len(opened)
		}
	}
	return counts
}

func BuildWorkflowStatePayload(rawFiles map[string]string, generatedAt string) (map[string]any, error) {
	if pyStrip(generatedAt) == "" {
		return nil, &cliError{Code: "invalid_input", Message: "generated_at 는 비어 있지 않은 문자열이어야 한다"}
	}
	for rel := range rawFiles {
		if rel == "" || strings.HasPrefix(rel, "/") || strings.ContainsRune(rel, '\\') {
			return nil, &cliError{Code: "invalid_input", Message: "files 경로가 올바르지 않다: " + pyReprStr(rel)}
		}
		for _, seg := range strings.Split(rel, "/") {
			if seg == "" || seg == "." || seg == ".." {
				return nil, &cliError{Code: "invalid_input", Message: "files 경로가 올바르지 않다: " + pyReprStr(rel)}
			}
		}
	}

	vfs := newVirtualFS(rawFiles)

	profileRel := ""
	if vfs.fileExists("docs/PROJECT_PROFILE.md") {
		profileRel = "docs/PROJECT_PROFILE.md"
	} else if vfs.fileExists("ai-workflow/memory/active/PROJECT_PROFILE.md") {
		profileRel = "ai-workflow/memory/active/PROJECT_PROFILE.md"
	} else {
		return nil, &cliError{Code: "invalid_input", Message: "files 에 docs/PROJECT_PROFILE.md 가 필요하다"}
	}

	branch := "main"
	activePrefix := "ai-workflow/memory/active/"
	skipSegs := map[string]bool{
		"roadmap":      true,
		"memory_index": true,
		"environments": true,
		"archived":     true,
		"backlog":      true,
		"sessions":     true,
	}
	sortedKeys := make([]string, 0, len(rawFiles))
	for k := range rawFiles {
		sortedKeys = append(sortedKeys, k)
	}
	sort.Strings(sortedKeys)
	for _, rel := range sortedKeys {
		if strings.HasPrefix(rel, activePrefix) {
			rest := rel[len(activePrefix):]
			if seg, _, ok := strings.Cut(rest, "/"); ok && !skipSegs[seg] {
				branch = seg
				break
			}
		}
	}

	activeDir := "ai-workflow/memory/active"
	memoryDir := activeDir
	if profileRel == "docs/PROJECT_PROFILE.md" && !vfs.dirExists(activeDir) && vfs.dirExists("ai-workflow/memory") {
		memoryDir = "ai-workflow/memory"
	}
	branchDir := memoryDir + "/" + branch

	branchScoped := func(leaf string) string {
		cand := branchDir + "/" + leaf
		if vfs.exists(cand) {
			return cand
		}
		legacy := memoryDir + "/" + leaf
		if vfs.exists(legacy) {
			return legacy
		}
		return cand
	}

	handoffCand := branchScoped("session_handoff.md")
	handoffPath := ""
	if vfs.fileExists(handoffCand) {
		handoffPath = handoffCand
	}
	wbCand := memoryDir + "/work_backlog.md"
	workBacklogIndexPath := ""
	if vfs.fileExists(wbCand) {
		workBacklogIndexPath = wbCand
	}
	dailyBacklogDir := branchScoped("backlog")
	tasksDir := dailyBacklogDir + "/tasks"
	sessionsDir := branchScoped("sessions")
	repoAssessCand := memoryDir + "/repository_assessment.md"
	repoAssessmentPath := ""
	if vfs.fileExists(repoAssessCand) {
		repoAssessmentPath = repoAssessCand
	}

	resolvedLatestBacklogPath := ""
	if workBacklogIndexPath != "" {
		resolvedLatestBacklogPath = findLatestBacklogFromIndex(vfs, workBacklogIndexPath)
	}
	if resolvedLatestBacklogPath == "" {
		resolvedLatestBacklogPath = findLatestDailyBacklog(vfs, dailyBacklogDir)
	}
	if resolvedLatestBacklogPath != "" && !vfs.fileExists(resolvedLatestBacklogPath) {
		resolvedLatestBacklogPath = ""
	}

	profileLines := splitPyLines(vfs.files[profileRel])
	profileCore := map[string]*string{
		"project_name":     extractSectionValue(profileLines, "프로젝트명"),
		"document_home":    extractSectionValue(profileLines, "문서 위키 홈"),
		"operations_path":  extractSectionValue(profileLines, "운영 문서 위치"),
		"backlog_path":     extractSectionValue(profileLines, "백로그 위치"),
		"handoff_path":     extractSectionValue(profileLines, "세션 인계 문서 위치"),
		"environment_path": extractSectionValue(profileLines, "환경 기록 위치"),
	}
	profileValidation := map[string]*string{
		"quick_tests":    extractSectionValue(profileLines, "빠른 테스트"),
		"isolated_tests": extractSectionValue(profileLines, "격리 테스트"),
		"runtime_checks": extractSectionValue(profileLines, "UI/API 실행 확인"),
	}

	var handoffRes HandoffParseResult
	var handoffNextRawTargets []string
	if handoffPath != "" {
		handoffRes, handoffNextRawTargets = parseHandoffInternal(vfs.files[handoffPath], path.Base(handoffPath))
	} else {
		handoffRes = HandoffParseResult{
			BlockedItems:    make([]string, 0),
			InProgressItems: make([]string, 0),
			NextDocuments:   make([]string, 0),
			RecentCoreDocs:  make([]string, 0),
			RecentDoneItems: make([]string, 0),
			Warnings:        make([]string, 0),
		}
	}

	var backlogRes backlogParseResult
	if resolvedLatestBacklogPath != "" {
		backlogRes = parseBacklogVirtual(vfs, resolvedLatestBacklogPath)
	} else {
		backlogRes = backlogParseResult{
			inProgress: make([]string, 0),
			blocked:    make([]string, 0),
			done:       make([]string, 0),
		}
	}

	appendonly := aggregateFromAppendonly(vfs, dailyBacklogDir, tasksDir, sessionsDir)

	var inProgSeeds []string
	for _, it := range handoffRes.InProgressItems {
		if isMeaningfulStr(it) {
			inProgSeeds = append(inProgSeeds, it)
		}
	}
	for _, it := range appendonly.inProgress {
		if isMeaningfulStr(it) {
			inProgSeeds = append(inProgSeeds, it)
		}
	}
	inProgSeeds = append(inProgSeeds, backlogRes.inProgress...)
	inProgressItems := dedupeWorkItems(inProgSeeds)

	var blockedSeeds []string
	for _, it := range handoffRes.BlockedItems {
		if isMeaningfulStr(it) {
			blockedSeeds = append(blockedSeeds, it)
		}
	}
	for _, it := range appendonly.blocked {
		if isMeaningfulStr(it) {
			blockedSeeds = append(blockedSeeds, it)
		}
	}
	blockedSeeds = append(blockedSeeds, backlogRes.blocked...)
	blockedItems := dedupeWorkItems(blockedSeeds)

	var recentSeeds []string
	for _, it := range appendonly.recentDone {
		if isMeaningfulStr(it) {
			recentSeeds = append(recentSeeds, it)
		}
	}
	for _, it := range handoffRes.RecentDoneItems {
		if isMeaningfulStr(it) {
			recentSeeds = append(recentSeeds, it)
		}
	}
	recentSeeds = append(recentSeeds, backlogRes.done...)
	recentDoneItems := dedupeWorkItems(recentSeeds)
	if len(recentDoneItems) > recentDoneItemsCap {
		recentDoneItems = recentDoneItems[:recentDoneItemsCap]
	}

	nextDocSeeds := []string{
		profileRel,
		handoffPath,
		workBacklogIndexPath,
		resolvedLatestBacklogPath,
	}
	if handoffPath != "" {
		handoffDir := path.Dir(handoffPath)
		for _, target := range handoffNextRawTargets {
			if resolved, ok := vfs.resolveFrom(handoffDir, target); ok && vfs.exists(resolved) {
				nextDocSeeds = append(nextDocSeeds, resolved)
			}
		}
	}
	nextDocuments := dedupeStrings(nextDocSeeds)

	var currentFocus *string
	if len(inProgressItems) > 0 {
		s := inProgressItems[0]
		currentFocus = &s
	} else if len(blockedItems) > 0 {
		s := blockedItems[0]
		currentFocus = &s
	} else if len(backlogRes.tasks) > 0 {
		for _, t := range backlogRes.tasks {
			if t.status != "done" {
				s := t.taskID + " " + t.title
				currentFocus = &s
				break
			}
		}
	}

	var purposeDigest, purposeDigestRev *string
	for _, pCand := range []string{"ai-workflow/memory/active/PURPOSE.md", "PURPOSE.md"} {
		if vfs.fileExists(pCand) {
			purposeDigest, purposeDigestRev = parsePurposeSummary(vfs.files[pCand])
			break
		}
	}

	strOrNil := func(s string) any {
		if s == "" {
			return nil
		}
		return s
	}

	var envConstraints []string
	if isMeaningfulText(handoffRes.Constraints) {
		envConstraints = dedupeNormalizedBackticked([]string{*handoffRes.Constraints})
	} else {
		envConstraints = make([]string, 0)
	}

	var repoAssessAny any
	if repoAssessmentPath != "" {
		repoAssessAny = repoAssessmentPath
	}

	payload := map[string]any{
		"schema_version":     "1",
		"generated_at":       generatedAt,
		"purpose_digest":     purposeDigest,
		"purpose_digest_rev": purposeDigestRev,
		"source_of_truth": map[string]any{
			"project_profile_path":       profileRel,
			"session_handoff_path":       strOrNil(handoffPath),
			"work_backlog_index_path":    strOrNil(workBacklogIndexPath),
			"daily_backlog_dir":          dailyBacklogDir,
			"tasks_dir":                  tasksDir,
			"sessions_dir":               sessionsDir,
			"latest_backlog_path":        strOrNil(resolvedLatestBacklogPath),
			"repository_assessment_path": repoAssessAny,
		},
		"project":  profileCore,
		"commands": profileValidation,
		"session": map[string]any{
			"current_baseline":        handoffRes.CurrentBaseline,
			"current_axis":            handoffRes.CurrentAxis,
			"current_focus":           currentFocus,
			"in_progress_items":       inProgressItems,
			"blocked_items":           blockedItems,
			"planned_items":           dedupeStrings(appendonly.planned),
			"recent_done_items":       recentDoneItems,
			"unknown_status_items":    dedupeStrings(appendonly.unknownStatus),
			"environment_constraints": envConstraints,
		},
		"backlog": map[string]any{
			"latest_backlog_path": strOrNil(resolvedLatestBacklogPath),
			"task_count":          len(backlogRes.tasks),
			"in_progress_items":   backlogRes.inProgress,
			"blocked_items":       backlogRes.blocked,
			"done_items":          backlogRes.done,
		},
		"next_documents": nextDocuments,
		"repository_assessment": map[string]any{
			"path":    repoAssessAny,
			"present": repoAssessmentPath != "",
		},
		"schema_version_memory_entries": memoryEntriesSchemaVersion,
	}

	memEntries := collectMemoryEntryPointers(vfs, "ai-workflow/memory/active/memory_index")
	if len(memEntries) > 0 {
		payload["memory_entries"] = memEntries
		payload["memory_entries_count"] = len(memEntries)
	}

	openDecisions := collectColumnOpenDecisions(vfs, tasksDir)
	if len(openDecisions) > 0 {
		payload["open_decisions"] = openDecisions
	}

	return payload, nil
}
