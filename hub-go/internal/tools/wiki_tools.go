package tools

import (
	"bytes"
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"os"
	"os/exec"
	"path"
	"path/filepath"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"time"

	"github.com/ykylee/standard_ai_workflow/hub-go/internal/db"
	"github.com/ykylee/standard_ai_workflow/hub-go/internal/judge"
	"github.com/ykylee/standard_ai_workflow/hub-go/internal/pytext"
	"github.com/ykylee/standard_ai_workflow/hub-go/internal/store"
)

// 위키 lint · 내보내기 · OKF — Python hub/wiki.py 와 1.x wiki_rules · bidir_link 의 판정.

const wikiRemoteTimeout = 120 * time.Second

var (
	wikiEntryRE    = regexp.MustCompile(`^### \[\[([^\]]+)\]\] \{#([^}]+)\}$`)
	wikiLinkRE     = regexp.MustCompile(`\[\[([^\]|#]+)(?:[#|][^\]]*)?\]\]`)
	wikiCodeRE     = regexp.MustCompile("`[^`]*`")
	wikiIngestedRE = regexp.MustCompile(`(?m)^last_ingested_from:\s*(.+)$`)
	wikiSplitRE    = regexp.MustCompile(`[,\s]+`)
)

func splitTextLines(text string) []string { return judge.SplitLines(text) }

func validateWikiIndex(text string, has func(string) bool) ([]string, int) {
	errs, total := []string{}, 0
	lines := splitTextLines(text)
	if len(lines) == 0 || !strings.HasPrefix(lines[0], "# ") {
		return append(errs, "First line must be a top-level '# Title' heading"), 0
	}
	seen := map[string]int{}
	section, inSection, hasEntry, sawH2 := "", false, false, false
	for i, raw := range lines {
		n, line := strconv.Itoa(i+1), pytext.RStrip(raw)
		switch {
		case line == "":
		case strings.HasPrefix(line, "# "):
			if i > 0 {
				errs = append(errs, "Line "+n+": extra '#' top-level heading '"+line+"' (R4 allows a single H1 per index.md).")
			}
		case strings.HasPrefix(line, "## "):
			if inSection && !hasEntry {
				errs = append(errs, "Line "+n+": ## section '"+section+"' has no ### entries (R4 forbids empty sections).")
			}
			section, inSection, hasEntry, sawH2 = judge.Strip(line[3:]), true, false, true
		case strings.HasPrefix(line, "### "):
			m := wikiEntryRE.FindStringSubmatch(line)
			if m == nil {
				errs = append(errs, "Line "+n+": malformed ### entry '"+line+"' (R4 requires '### [[<path>]] {#<anchor-id>}' format).")
				continue
			}
			p, anchor := judge.Strip(m[1]), judge.Strip(m[2])
			if p == "" || anchor == "" {
				errs = append(errs, "Line "+n+": empty path or anchor-id in entry '"+line+"'.")
				continue
			}
			if first, dup := seen[anchor]; dup {
				errs = append(errs, "Line "+n+": duplicate anchor-id '"+anchor+"' (first seen on line "+strconv.Itoa(first)+").")
			} else {
				seen[anchor] = i + 1
			}
			if !has(p + ".md") {
				errs = append(errs, "Line "+n+": entry path '"+p+"' does not resolve to a file.")
			}
			hasEntry = true
			total++
		default:
			if !inSection && !sawH2 {
				errs = append(errs, "Line "+n+": orphan content outside any '##' section (R4 requires anchor-based structure).")
			}
		}
	}
	if inSection && !hasEntry {
		errs = append(errs, "## section '"+section+"' has no ### entries (R4 forbids empty sections).")
	}
	if !sawH2 {
		errs = append(errs, "index.md has no '##' sections (R4 requires at least one).")
	}
	return errs, total
}

func wikiLinks(body string) []string {
	out, fenced := []string{}, false
	for _, line := range splitTextLines(body) {
		if strings.HasPrefix(strings.TrimLeftFunc(line, pytext.IsSpace), "```") {
			fenced = !fenced
			continue
		}
		if fenced {
			continue
		}
		for _, m := range wikiLinkRE.FindAllStringSubmatch(wikiCodeRE.ReplaceAllString(line, ""), -1) {
			out = append(out, judge.Strip(m[1]))
		}
	}
	return out
}

func wikiProject(s *store.Store, pid string) ([]store.WikiBody, map[string]any, error) {
	pages, err := s.WikiBodies(pid)
	if err != nil {
		return nil, nil, err
	}
	var raw sql.NullString
	if err := s.DB().QueryRow("SELECT settings_json FROM project WHERE id=?", pid).Scan(&raw); err != nil {
		return nil, nil, err
	}
	settings := map[string]any{}
	if raw.String != "" {
		if err := json.Unmarshal([]byte(raw.String), &settings); err != nil {
			return nil, nil, err
		}
	}
	return pages, settings, nil
}

func wikiLint(s *store.Store, ctx store.Ctx) (map[string]any, error) {
	p, err := store.NeedCallsign(ctx)
	if err != nil {
		return nil, err
	}
	pages, settings, err := wikiProject(s, p.ProjectID)
	if err != nil {
		return nil, err
	}
	rows, err := s.DB().Query("SELECT id,body_json FROM memory_entry WHERE project_id=? ORDER BY id", p.ProjectID)
	if err != nil {
		return nil, err
	}
	type memory struct {
		id        string
		mentioned []string
	}
	entries := []memory{}
	for rows.Next() {
		var id, raw string
		if err := rows.Scan(&id, &raw); err != nil {
			rows.Close()
			return nil, err
		}
		var body struct {
			Mentioned []string `json:"mentioned_in"`
		}
		_ = json.Unmarshal([]byte(raw), &body)
		entries = append(entries, memory{id, body.Mentioned})
	}
	if err := rows.Err(); err != nil {
		rows.Close()
		return nil, err
	}
	rows.Close()
	if len(pages) == 0 { // 잴 것이 없음은 통과가 아니다
		return map[string]any{"ok": nil, "status": "empty", "pages": 0, "memory_entries": len(entries)}, nil
	}
	const root = "ai-workflow/wiki/"
	files := map[string]bool{root + "index.md": true, root + "log.md": true}
	for _, page := range pages {
		files[root+page.Path] = true
	}
	has := func(rel string) bool { return !strings.HasPrefix(rel, "/") && files[path.Clean(root+rel)] }
	index, err := s.WikiPageOf(p.ProjectID, "index.md")
	if err != nil {
		return nil, err
	}
	indexErrors, indexEntries := validateWikiIndex(index["body"].(string), has)
	broken, refs := []map[string]any{}, [][2]string{}
	related := map[string]map[string]bool{"index.md": {}, "log.md": {}}
	for _, page := range pages {
		body := universalNewlines(page.Body)
		for _, target := range wikiLinks(body) {
			if strings.HasSuffix(target, ".md") {
				refs = append(refs, [2]string{page.Path, target})
			} else if !has(target + ".md") {
				broken = append(broken, map[string]any{"page": page.Path, "target": target})
			}
		}
		related[page.Path] = map[string]bool{}
		if fm, _, why := parseMatter(body); why == "" {
			for _, ref := range fm.related {
				related[page.Path][ref] = true
			}
		}
	}
	symmetric, asymmetric := 0, []map[string]any{}
	names := make([]string, 0, len(related))
	for name := range related {
		names = append(names, name)
	}
	sort.Strings(names)
	for _, e := range entries {
		full := "ai-workflow/memory/active/memory_index/entries/" + e.id + ".json"
		mentioned := map[string]bool{}
		for _, m := range e.mentioned {
			rel := strings.TrimPrefix(m, root)
			top, _, _ := strings.Cut(strings.ReplaceAll(m, `\`, "/"), "/")
			switch {
			case rel != m:
				mentioned[rel] = true
			case top == "topics" || top == "concepts" || top == "decisions" || top == "entities" || top == "patterns" || top == "queries":
				mentioned[m] = true
			}
		}
		for _, page := range sortedSet(mentioned) {
			if related[page][full] || related[page][e.id] {
				symmetric++
			} else {
				asymmetric = append(asymmetric, map[string]any{"entry": e.id, "page": page, "direction": "memory_only"})
			}
		}
		for _, page := range names {
			if (related[page][full] || related[page][e.id]) && !mentioned[page] {
				asymmetric = append(asymmetric, map[string]any{"entry": e.id, "page": page, "direction": "wiki_only"})
			}
		}
	}
	ok := len(indexErrors) == 0 && len(broken) == 0 && len(asymmetric) == 0
	status := "violations"
	if ok {
		status = "ok"
	}
	out := map[string]any{"ok": ok, "status": status, "pages": len(pages), "location": map[string]any{"errors": []string{}},
		"index": map[string]any{"errors": indexErrors, "entries": indexEntries}, "broken_links": broken,
		"bidir": map[string]any{"memory_entries": len(entries), "symmetric": symmetric, "asymmetric": asymmetric}}
	fetch := ""
	if remote, _ := settings["wiki_remote"].(map[string]any); remote != nil && s.WikiRemoteAllowed {
		fetch, _ = remote["fetch_url"].(string)
	}
	for k, v := range measureRemote(fetch, pages, refs) {
		out[k] = v
	}
	return out, nil
}

func unmeasuredRemote(reason string, refs int) map[string]any {
	return map[string]any{
		"repo_references": map[string]any{"status": "unmeasured", "count": refs, "reason": reason},
		"source_sha":      map[string]any{"status": "unmeasured", "reason": reason},
		"freshness":       map[string]any{"status": "unmeasured", "targets": 0, "reason": reason},
	}
}

func wikiSourcePaths(body string) []string {
	if !strings.HasPrefix(body, "---\n") {
		return nil
	}
	end := strings.Index(body[4:], "\n---")
	if end < 0 {
		return nil
	}
	m := wikiIngestedRE.FindStringSubmatch(body[4 : 4+end])
	if m == nil {
		return nil
	}
	out := []string{}
	for _, part := range wikiSplitRE.Split(strings.Trim(judge.Strip(m[1]), "[]"), -1) {
		part, _, _ = strings.Cut(strings.Trim(judge.Strip(part), "'\"`"), "#")
		suffix := strings.HasSuffix(part, ".md") || strings.HasSuffix(part, ".py") || strings.HasSuffix(part, ".json") || strings.HasSuffix(part, ".toml")
		if part != "" && (strings.Contains(part, "/") || suffix) {
			out = append(out, strings.TrimRight(part, "/"))
		}
	}
	return out
}

func wikiGit(dir string, args ...string) (string, string, error) {
	ctx, cancel := context.WithTimeout(context.Background(), wikiRemoteTimeout)
	defer cancel()
	cmd := exec.CommandContext(ctx, "git", args...)
	cmd.Dir = dir
	cmd.Env = append(os.Environ(), "GIT_TERMINAL_PROMPT=0", "GIT_ASKPASS=true", "SSH_ASKPASS=true", "GIT_CONFIG_NOSYSTEM=1", "LC_ALL=C")
	var out, errOut bytes.Buffer
	cmd.Stdout, cmd.Stderr = &out, &errOut
	err := cmd.Run()
	if ctx.Err() != nil {
		return "", "", ctx.Err()
	}
	return judge.Strip(out.String()), judge.Strip(errOut.String()), err
}

// measureRemote clones read-only without file contents; anything it cannot get stays unmeasured, not passed.
func measureRemote(fetch string, pages []store.WikiBody, refs [][2]string) map[string]any {
	if fetch == "" {
		return unmeasuredRemote("위키 원격 읽기 꺼짐 — 소유자가 hub_wiki_remote_set 으로 켠다 (R8.4)", len(refs))
	}
	dir, err := os.MkdirTemp("", "hubwiki-remote-")
	if err != nil {
		return unmeasuredRemote("임시 디렉터리를 만들지 못했다", len(refs))
	}
	defer func() { _ = os.RemoveAll(dir) }()
	repo := filepath.Join(dir, "repo.git")
	if _, stderr, err := wikiGit(dir, "clone", "--bare", "--quiet", "--filter=blob:none", "--no-tags", "--", fetch, repo); err != nil {
		var exit *exec.ExitError
		switch {
		case errors.Is(err, context.DeadlineExceeded):
			return unmeasuredRemote("원격 받기 시간 초과 (120s)", len(refs))
		case errors.As(err, &exit):
			if r := []rune(stderr); len(r) > 300 {
				stderr = string(r[len(r)-300:])
			}
			return unmeasuredRemote("원격 받기 실패: "+stderr, len(refs))
		}
		return unmeasuredRemote("git 실행 실패: "+err.Error(), len(refs))
	}
	head, _, err := wikiGit(repo, "rev-parse", "HEAD")
	if err != nil || head == "" {
		return unmeasuredRemote("원격에 기본 브랜치 커밋이 없다", len(refs))
	}
	missing := []map[string]any{}
	for _, ref := range refs {
		if out, _, _ := wikiGit(repo, "ls-tree", "--name-only", "HEAD", "--", ref[1]); out == "" {
			missing = append(missing, map[string]any{"page": ref[0], "target": ref[1]})
		}
	}
	known := map[string]bool{}
	hasCommit := func(sha string) bool {
		if v, seen := known[sha]; seen {
			return v
		}
		_, _, err := wikiGit(repo, "cat-file", "-e", sha+"^{commit}")
		known[sha] = err == nil
		return err == nil
	}
	withSHA, unknown, stale, targets := 0, []map[string]any{}, []map[string]any{}, 0
	for _, page := range pages {
		if page.SourceSHA == "" {
			continue
		}
		withSHA++
		if !hasCommit(page.SourceSHA) {
			unknown = append(unknown, map[string]any{"page": page.Path, "sha": page.SourceSHA})
			continue
		}
		paths := wikiSourcePaths(page.Body)
		if len(paths) == 0 {
			continue
		}
		targets++
		out, _, _ := wikiGit(repo, append([]string{"rev-list", "--count", page.SourceSHA + "..HEAD", "--"}, paths...)...)
		if n, err := strconv.Atoi(out); err == nil && n > 0 {
			stale = append(stale, map[string]any{"page": page.Path, "sha": page.SourceSHA, "commits_since": n, "sources": paths})
		}
	}
	return map[string]any{
		"repo_references": map[string]any{"status": "measured", "count": len(refs), "missing": missing, "head": head},
		"source_sha":      map[string]any{"status": "measured", "pages": withSHA, "unknown": unknown},
		"freshness":       map[string]any{"status": "measured", "targets": targets, "stale": stale, "unmeasured_pages": len(pages) - targets},
	}
}

func wikiExport(s *store.Store, ctx store.Ctx, format string, outDir *string, cursor int) (map[string]any, error) {
	p, err := store.NeedCallsign(ctx)
	if err != nil {
		return nil, err
	}
	base := map[string]string{"dir": "ai-workflow/wiki", "okf": "okf-export"}[format]
	if base == "" {
		return nil, store.InvalidField("format", "dir · okf")
	}
	if outDir != nil {
		base = *outDir
	}
	if strings.HasPrefix(base, "/") || strings.HasPrefix(base, "~") || strings.Contains("/"+base+"/", "/../") {
		return nil, store.InvalidField("out_dir", "저장소 뿌리 상대 경로")
	}
	base = strings.TrimRight(base, "/")
	bodies, _, err := wikiProject(s, p.ProjectID)
	if err != nil {
		return nil, err
	}
	pages := make([][2]string, 0, len(bodies))
	for _, b := range bodies {
		pages = append(pages, [2]string{b.Path, b.Body})
	}
	report := map[string]any{"format": format, "pages": len(pages)}
	files := [][2]string{}
	if format == "dir" {
		files = append(files, pages...)
		if len(pages) > 0 {
			for _, name := range []string{"index.md", "log.md"} {
				doc, err := s.WikiPageOf(p.ProjectID, name)
				if err != nil {
					return nil, err
				}
				files = append(files, [2]string{name, doc["body"].(string)})
			}
		}
		var last *string
		var id string
		err := s.DB().QueryRow("SELECT id FROM wiki_ingest WHERE project_id=? ORDER BY seq DESC LIMIT 1", p.ProjectID).Scan(&id)
		if err == nil {
			last = &id
		} else if !errors.Is(err, sql.ErrNoRows) {
			return nil, err
		}
		var marker bytes.Buffer
		enc := json.NewEncoder(&marker)
		enc.SetEscapeHTML(false)
		enc.SetIndent("", "  ")
		if err := enc.Encode(struct {
			Canonical  string  `json:"canonical"`
			Project    string  `json:"project_id"`
			ExportedAt string  `json:"exported_at"`
			LastIngest *string `json:"last_ingest"`
			Note       string  `json:"note"`
		}{"hub", p.ProjectID, db.FormatISO(ctx.Now), last, "허브 위키의 사본이다 — 정본은 허브. 여기를 고쳐도 허브에 반영되지 않는다 (R15.2)."}); err != nil {
			return nil, err
		}
		files = append(files, [2]string{".hub-export.json", marker.String()})
	} else {
		bundle, errs, exported := exportOKF(pages, ctx.Now)
		for name, text := range bundle {
			files = append(files, [2]string{name, text})
		}
		excluded, other := []string{}, 0
		for _, page := range pages {
			if _, ok := bundle[page[0]]; !ok {
				excluded = append(excluded, page[0])
			}
			if !isOKFPage(page[0]) {
				other++
			}
		}
		for k, v := range map[string]any{"pages_exported": exported, "excluded": excluded, "excluded_not_type_dir": other, "excluded_by_error": len(excluded) - other,
			"errors": errs, "lossy": true, "note": "OKF 는 출판 형식이다 — 5종 디렉터리만 · 본문 · frontmatter 변환. 운반은 format=dir"} {
			report[k] = v
		}
	}
	sort.Slice(files, func(i, j int) bool { return files[i][0] < files[j][0] })
	const budget = 150_000
	steps, size, i := []map[string]any{}, 0, max(0, cursor)
	for ; i < len(files); i++ {
		if len(steps) > 0 && size+len(files[i][1]) > budget {
			break
		}
		size += len(files[i][1])
		steps = append(steps, map[string]any{"op": "write", "path": base + "/" + files[i][0], "content": files[i][1], "sha256": digest(files[i][1])})
	}
	report["steps"], report["total_files"], report["next_cursor"] = steps, len(files), nil
	if i < len(files) {
		report["next_cursor"] = i
	}
	return report, nil
}

func wikiImportOKF(s *store.Store, ctx store.Ctx, raw any, summary, requestID string) (map[string]any, error) {
	if _, err := store.NeedCallsign(ctx); err != nil {
		return nil, err
	}
	items, ok := raw.([]any)
	if !ok || len(items) == 0 {
		return nil, store.InvalidField("files", "[{path, content}] 하나 이상")
	}
	files := map[string]string{}
	for i, item := range items {
		m, _ := item.(map[string]any)
		content, okC := m["content"].(string)
		name, okP := m["path"].(string)
		at := "files[" + strconv.Itoa(i) + "]"
		if len(m) != 2 || !okC {
			return nil, store.InvalidField(at, "{path, content(문자열)}")
		}
		if !okP || name == "" || strings.HasPrefix(name, "/") || strings.Contains("/"+name+"/", "/../") {
			return nil, store.InvalidField(at+".path", "묶음 뿌리 상대 경로")
		}
		files[path.Clean(name)] = content
	}
	got := importOKF(files)
	if len(got.pages) == 0 {
		return nil, &store.HubError{Status: 400, Code: "invalid_field", Message: "들일 페이지가 없어요 (loose 들여오기가 하나도 받지 않았어요)", Detail: map[string]any{"field": "files", "errors": []string{}}}
	}
	pages := make([]any, 0, len(got.pages))
	for _, page := range got.pages {
		pages = append(pages, map[string]any{"path": page[0], "body": page[1]})
	}
	out, err := s.WikiIngest(ctx, pages, summary, requestID)
	if err != nil {
		return nil, err
	}
	for k, v := range map[string]any{"okf_version": got.version, "pages_total": got.total, "pages_staged": len(got.pages), "warnings": got.warnings, "errors": 0, "mode": "loose"} {
		out[k] = v
	}
	return out, nil
}
