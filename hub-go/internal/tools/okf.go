package tools

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"path"
	"regexp"
	"sort"
	"strings"
	"time"

	"github.com/ykylee/standard_ai_workflow/hub-go/internal/judge"
)

// OKF(Open Knowledge Format) 출판 · 들여오기 — Python okf_export.py · okf_import.py 와 같은 변환 (resolve=False).

const okfSpecVersion = "0.2"

var (
	okfFrontmatter = regexp.MustCompile(`(?s)\A---\s*\n(.*?)\n---\s*\n(.*)\z`)
	okfWikiLink    = regexp.MustCompile(`\[\[([^\]]+?)\]\]`)
	okfH1          = regexp.MustCompile(`(?m)^# (.+)$`)
	okfSpaces      = regexp.MustCompile(`\s+`)
	okfTypeDirs    = []string{"concepts", "decisions", "entities", "patterns", "queries"}
	okfStatus      = map[string]string{"active": "stable", "accepted": "stable", "stable": "stable", "draft": "draft", "proposed": "draft", "deprecated": "deprecated", "superseded": "deprecated"}
)

type okfMatter struct {
	typ, status, title, description, source, created, updated, adr string
	related, tags                                                  []string
	r9skip                                                         bool
}

func universalNewlines(s string) string {
	return strings.ReplaceAll(strings.ReplaceAll(s, "\r\n", "\n"), "\r", "\n")
}

// simpleYAML parses the frontmatter subset: scalars, inline lists and block lists.
func simpleYAML(body string) map[string]any {
	out := map[string]any{}
	lines := judge.SplitLines(body)
	for i := 0; i < len(lines); {
		line := lines[i]
		stripped := judge.Strip(line)
		indented := strings.HasPrefix(line, " ") || strings.HasPrefix(line, "\t")
		if stripped == "" || strings.HasPrefix(stripped, "#") || indented || !strings.Contains(line, ":") {
			i++
			continue
		}
		key, rest, _ := strings.Cut(line, ":")
		key, rest = judge.Strip(key), judge.Strip(rest)
		if rest == "" {
			items := []string{}
			j := i + 1
			for ; j < len(lines); j++ {
				if judge.Strip(lines[j]) == "" {
					continue
				}
				item := strings.TrimLeft(lines[j], " \t")
				if !strings.HasPrefix(item, "- ") {
					break
				}
				items = append(items, judge.Strip(item[2:]))
			}
			if len(items) > 0 {
				out[key] = items
				i = j
			} else {
				out[key] = ""
				i++
			}
			continue
		}
		switch {
		case strings.HasPrefix(rest, "[") && strings.HasSuffix(rest, "]"):
			items := []string{}
			for _, part := range strings.Split(judge.Strip(rest[1:len(rest)-1]), ",") {
				if judge.Strip(part) != "" {
					items = append(items, strings.Trim(judge.Strip(part), `"'`))
				}
			}
			out[key] = items
		case rest == "true" || rest == "True" || rest == "yes":
			out[key] = true
		case rest == "false" || rest == "False" || rest == "no":
			out[key] = false
		case rest == "null" || rest == "None" || rest == "~":
			out[key] = nil
		default:
			if len(rest) >= 2 && (rest[0] == '"' && rest[len(rest)-1] == '"' || rest[0] == '\'' && rest[len(rest)-1] == '\'') {
				rest = rest[1 : len(rest)-1]
			}
			out[key] = rest
		}
		i++
	}
	return out
}

func yamlText(raw map[string]any, key string) string {
	v, ok := raw[key]
	if !ok {
		return ""
	}
	switch x := v.(type) {
	case nil:
		return "None"
	case bool:
		if x {
			return "True"
		}
		return "False"
	case []string:
		quoted := make([]string, len(x))
		for i, item := range x {
			quoted[i] = "'" + item + "'"
		}
		return "[" + strings.Join(quoted, ", ") + "]"
	default:
		return judge.Strip(fmt.Sprint(x))
	}
}

func yamlList(v any) []string {
	out := []string{}
	switch x := v.(type) {
	case []string:
		for _, item := range x {
			if t := judge.Strip(item); t != "" {
				out = append(out, t)
			}
		}
	case string:
		text := judge.Strip(x)
		if text == "" {
			return out
		}
		if strings.HasPrefix(text, "[") && strings.HasSuffix(text, "]") {
			for _, part := range strings.Split(text[1:len(text)-1], ",") {
				if judge.Strip(part) != "" {
					out = append(out, strings.Trim(judge.Strip(part), `"'`))
				}
			}
			return out
		}
		out = append(out, text)
	case bool:
		out = append(out, yamlText(map[string]any{"v": x}, "v"))
	}
	return out
}

// parseMatter returns the frontmatter and body, or why it cannot be used.
func parseMatter(text string) (okfMatter, string, string) {
	var fm okfMatter
	m := okfFrontmatter.FindStringSubmatch(text)
	if m == nil {
		return fm, "", "no frontmatter block"
	}
	raw := simpleYAML(m[1])
	if fm.typ = yamlText(raw, "type"); fm.typ == "" {
		return fm, "", "missing or empty `type` field (required by OKF §4.1)"
	}
	fm.status, fm.title, fm.description = yamlText(raw, "status"), yamlText(raw, "title"), yamlText(raw, "description")
	fm.source, fm.created, fm.updated, fm.adr = yamlText(raw, "last_ingested_from"), yamlText(raw, "created"), yamlText(raw, "updated"), yamlText(raw, "adr_id")
	fm.related, fm.tags = yamlList(raw["related_pages"]), yamlList(raw["tags"])
	switch x := raw["r9_skip"].(type) {
	case bool:
		fm.r9skip = x
	case string:
		fm.r9skip = x != ""
	case []string:
		fm.r9skip = len(x) > 0
	}
	return fm, m[2], ""
}

func okfDate(text string) string {
	if t, err := time.Parse("2006-1-2", text); err == nil {
		return t.Format("2006-01-02T15:04:05Z")
	}
	return ""
}

func okfProse(body, fallback string) (string, string) {
	title, prose := fallback, []string{}
	lines := judge.SplitLines(body)
	for _, line := range lines {
		s := judge.Strip(line)
		if strings.HasPrefix(s, "# ") {
			title = judge.Strip(s[2:])
			continue
		}
		block := false
		for _, p := range []string{"#", "```", "|", "- ", "* ", "> "} {
			block = block || strings.HasPrefix(s, p)
		}
		if block || s == "" {
			if len(prose) > 0 {
				break
			}
			continue
		}
		if prose = append(prose, s); len(prose) >= 3 {
			break
		}
	}
	text := strings.Join(prose, " ")
	if r := []rune(text); len(r) > 200 {
		text = string(r[:197]) + "..."
	}
	return title, text
}

func okfScalar(text string) string {
	if strings.ContainsAny(text, ":#&*{}[]|><%@`") {
		return `"` + text + `"`
	}
	return text
}

func okfPage(fm okfMatter, rawBody string) string {
	body := strings.TrimRight(rawBody, "\n")
	lines := []string{"---"}
	str := func(key, value string) {
		if value != "" {
			lines = append(lines, key+": "+okfScalar(value))
		}
	}
	list := func(key string, values []string) {
		if len(values) == 0 {
			return
		}
		inline := true
		for _, v := range values {
			inline = inline && !strings.ContainsAny(v, ",[]")
		}
		if inline {
			lines = append(lines, key+": ["+strings.Join(values, ", ")+"]")
			return
		}
		lines = append(lines, key+":")
		for _, v := range values {
			lines = append(lines, "  - "+v)
		}
	}
	title, description := fm.title, fm.description
	if body != "" {
		t, d := okfProse(body, fm.typ)
		if title == "" {
			title = t
		}
		if description == "" {
			description = d
		}
	}
	single := strings.Join(strings.Fields(fm.source), " ") == fm.source && !strings.Contains(fm.source, " ")
	resource := ""
	if single && (strings.HasPrefix(fm.source, "http://") || strings.HasPrefix(fm.source, "https://")) {
		resource = fm.source
	}
	str("type", fm.typ)
	str("title", title)
	str("description", description)
	str("resource", resource)
	tags, seen := []string{}, map[string]bool{}
	for _, t := range append(append([]string{}, fm.tags...), "status:"+fm.status, "wiki-type:"+fm.typ) {
		if t != "status:" && !seen[t] {
			seen[t] = true
			tags = append(tags, t)
		}
	}
	list("tags", tags)
	stamp := okfDate(fm.updated)
	if stamp == "" {
		stamp = okfDate(fm.created)
	}
	str("timestamp", stamp)
	if fm.source != "" {
		lines = append(lines, "sources:", "  - resource: "+okfScalar(fm.source))
	}
	str("created", fm.created)
	if fm.status != "" {
		mapped := okfStatus[strings.ToLower(judge.Strip(fm.status))]
		if mapped == "" {
			mapped = "draft"
		}
		str("status", mapped)
		if mapped != fm.status {
			str("wiki_status", fm.status)
		}
	}
	list("related_pages", fm.related)
	str("adr_id", fm.adr)
	if fm.r9skip {
		lines = append(lines, "r9_skip: true")
	}
	if fm.source != "" && resource == "" {
		str("last_ingested_from", fm.source)
	}
	lines = append(lines, "---")
	suffix := []string{}
	if fm.source != "" && resource == "" {
		cite := "[1] " + fm.source
		if single {
			cite = "[1] [" + fm.source + "](" + fm.source + ")"
		}
		suffix = append(suffix, "", "# Citations", "", cite)
	}
	if len(fm.related) > 0 {
		suffix = append(suffix, "", "## See Also", "")
		for _, ref := range fm.related {
			suffix = append(suffix, "- ["+ref+"](../"+ref+")")
		}
	}
	linked := okfWikiLink.ReplaceAllStringFunc(body, func(match string) string {
		target := judge.Strip(match[2 : len(match)-2])
		p, anchor, _ := strings.Cut(target, "#")
		if strings.Contains(target, "#") {
			p, anchor = judge.Strip(p), judge.Strip(anchor)
		}
		display := p[strings.LastIndexByte(p, '/')+1:]
		if p == "" {
			display = target
		}
		url := "../" + p
		if !strings.HasSuffix(p, ".md") {
			url += ".md"
		}
		if anchor != "" {
			url += "#" + anchor
		}
		return "[" + display + "](" + url + ")"
	})
	text := strings.Join(lines, "\n") + "\n" + linked + "\n"
	if len(suffix) > 0 {
		text += strings.Join(suffix, "\n") + "\n"
	}
	return text
}

func isOKFPage(p string) bool {
	if !strings.HasSuffix(p, ".md") {
		return false
	}
	switch path.Base(p) {
	case "index.md", "log.md", "SCHEMA.md", "INGEST_GUIDE.md":
		return false
	}
	top, _, nested := strings.Cut(p, "/")
	for _, d := range okfTypeDirs {
		if nested && top == d {
			return true
		}
	}
	return false
}

// exportOKF converts pages to an OKF bundle: files, errors and how many pages went out.
func exportOKF(pages [][2]string, now time.Time) (map[string]string, []string, int) {
	files, errs, exported := map[string]string{}, []string{}, 0
	type entry struct {
		rel string
		fm  okfMatter
	}
	collected := []entry{}
	sorted := append([][2]string{}, pages...)
	sort.Slice(sorted, func(i, j int) bool { return sorted[i][0] < sorted[j][0] })
	for _, p := range sorted {
		if !isOKFPage(p[0]) {
			continue
		}
		fm, body, why := parseMatter(universalNewlines(p[1]))
		if why != "" {
			errs = append(errs, p[0]+": "+why)
			continue
		}
		text := okfPage(fm, body)
		files[p[0]] = text
		exported++
		if out, _, bad := parseMatter(text); bad == "" {
			collected = append(collected, entry{p[0], out})
		}
	}
	if len(collected) == 0 {
		return files, errs, exported
	}
	at := now.UTC().Format("2006-01-02T15:04:05Z")
	const generator = "workflow_kit.okf_export v0.7.34+"
	lines := []string{"---", `okf_version: "` + okfSpecVersion + `"`, `generated_at: "` + at + `"`, `generator: "` + generator + `"`, "---", "",
		"# Knowledge Bundle Index", "", "Auto-generated by `" + generator + "` on " + at + ". OKF spec v" + okfSpecVersion + ".", ""}
	sum := sha256.New()
	for _, dir := range okfTypeDirs {
		section := []string{}
		for _, e := range collected {
			if !strings.HasPrefix(e.rel, dir+"/") {
				continue
			}
			title := e.fm.title
			if title == "" {
				title = strings.TrimSuffix(path.Base(e.rel), ".md")
			}
			line := "- [" + title + "](" + e.rel + ")"
			if d := []rune(e.fm.description); len(d) > 120 {
				line += " — " + string(d[:117]) + "..."
			} else if len(d) > 0 {
				line += " — " + string(d)
			}
			section = append(section, line)
		}
		if len(section) > 0 {
			lines = append(lines, "## "+strings.ToUpper(dir[:1])+dir[1:], "")
			lines = append(append(lines, section...), "")
		}
	}
	for _, e := range collected {
		sum.Write([]byte(files[e.rel]))
	}
	files["index.md"] = strings.Join(lines, "\n") + "\n"
	files["okf-bundle.yaml"] = fmt.Sprintf("okf_version: '%s'\ngenerated_at: '%s'\ngenerator: 'workflow_kit.okf_export %s'\nintegrity_hash: 'sha256:%s'\npage_count: %d\n",
		okfSpecVersion, at, HubVersion, hex.EncodeToString(sum.Sum(nil)), len(collected))
	return files, errs, exported
}

type okfImport struct {
	version         any
	pages           [][2]string
	warnings, total int
}

// importOKF reads a foreign bundle in loose mode: unreadable pages are left out, lint findings only counted.
func importOKF(files map[string]string) okfImport {
	out := okfImport{}
	if m := okfFrontmatter.FindStringSubmatch(universalNewlines(files["index.md"])); m != nil {
		if v := yamlText(simpleYAML(m[1]), "okf_version"); v != "" {
			out.version = v
		}
	}
	names := []string{}
	for name := range files {
		base := path.Base(name)
		if strings.HasSuffix(name, ".md") && base != "index.md" && base != "log.md" {
			names = append(names, name)
		}
	}
	sort.Strings(names)
	norm := func(s string) string { return strings.ToLower(judge.Strip(okfSpaces.ReplaceAllString(s, " "))) }
	for _, name := range names {
		text := universalNewlines(files[name])
		fm, body, why := parseMatter(text)
		if why != "" {
			continue
		}
		top, _, _ := strings.Cut(name, "/")
		located := false
		for _, d := range okfTypeDirs {
			located = located || d == top
		}
		if !located {
			out.warnings++
		}
		if fm.title != "" {
			if m := okfH1.FindStringSubmatch(body); m == nil || norm(fm.title) != norm(m[1]) {
				out.warnings++
			}
		}
		out.pages = append(out.pages, [2]string{name, text})
	}
	out.total = len(out.pages)
	return out
}
