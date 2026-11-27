package store

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"path"
	"regexp"
	"sort"
	"strings"
)

// 위키 읽기 — MCP 도구와 화면이 같은 함수를 쓴다 (Python hub/wiki.py 의 get · list_pages · search).

var (
	wikiFrontTitle = regexp.MustCompile(`(?m)^title:[ \t]*(.+?)[ \t\r]*$`)
	wikiH1         = regexp.MustCompile(`(?m)^# (.+)$`)
)

var wikiSectionOrder = []string{"concepts", "decisions", "entities", "patterns", "queries", "sources", "topics"}

type wikiPageRow struct {
	path, body, by, at string
	version            int
}

func wikiPageTitle(p, body string) string {
	if strings.HasPrefix(body, "---\n") {
		if end := strings.Index(body[4:], "\n---"); end >= 0 {
			if m := wikiFrontTitle.FindStringSubmatch(body[4 : 4+end]); m != nil {
				return strings.Trim(strings.TrimSpace(m[1]), `"'`)
			}
		}
	}
	if m := wikiH1.FindStringSubmatch(body); m != nil {
		return strings.TrimSpace(m[1])
	}
	return strings.TrimSuffix(p, ".md")
}

func (s *Store) wikiPages(pid string) ([]wikiPageRow, error) {
	rows, err := s.pool.Query("SELECT path,body_md,version,updated_by,updated_at FROM wiki_page WHERE project_id=? ORDER BY path", pid)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	out := []wikiPageRow{}
	for rows.Next() {
		var x wikiPageRow
		if err := rows.Scan(&x.path, &x.body, &x.version, &x.by, &x.at); err != nil {
			return nil, err
		}
		out = append(out, x)
	}
	return out, rows.Err()
}

func wikiReaderProject(ctx Ctx) (string, error) {
	p, err := NeedReader(ctx)
	if err != nil {
		return "", err
	}
	return p.ProjectID, nil
}

// WikiGet returns one page of the caller's project (index.md and log.md are generated).
func (s *Store) WikiGet(ctx Ctx, p string) (map[string]any, error) {
	pid, err := wikiReaderProject(ctx)
	if err != nil {
		return nil, err
	}
	return s.WikiPageOf(pid, p)
}

// WikiList lists the caller's project pages under prefix.
func (s *Store) WikiList(ctx Ctx, prefix string) (map[string]any, error) {
	pid, err := wikiReaderProject(ctx)
	if err != nil {
		return nil, err
	}
	return s.WikiListOf(pid, prefix)
}

// WikiListOf lists pages of an already authorized project.
func (s *Store) WikiListOf(pid, prefix string) (map[string]any, error) {
	items, err := s.wikiPages(pid)
	if err != nil {
		return nil, err
	}
	pages := []map[string]any{}
	for _, x := range items {
		if strings.HasPrefix(x.path, prefix) {
			pages = append(pages, map[string]any{"path": x.path, "title": wikiPageTitle(x.path, x.body), "version": x.version, "updated_by": x.by, "updated_at": x.at})
		}
	}
	return map[string]any{"pages": pages, "generated": []string{"index.md", "log.md"}}, nil
}

// WikiSearch finds pages containing every word; offsets are counted in runes so Korean snippets stay intact.
func (s *Store) WikiSearch(ctx Ctx, query string, limit int) (map[string]any, error) {
	pid, err := wikiReaderProject(ctx)
	if err != nil {
		return nil, err
	}
	words := strings.Fields(strings.ToLower(query))
	if len(words) == 0 {
		return nil, InvalidField("query", "비었어요")
	}
	items, err := s.wikiPages(pid)
	if err != nil {
		return nil, err
	}
	hits := []map[string]any{}
	for _, x := range items {
		title := wikiPageTitle(x.path, x.body)
		hay := strings.ToLower(x.path + "\n" + title + "\n" + x.body)
		lowerPath, lowerTitle := strings.ToLower(x.path), strings.ToLower(title)
		match, score := true, 0
		for _, w := range words {
			if !strings.Contains(hay, w) {
				match = false
				break
			}
			if strings.Contains(lowerPath, w) || strings.Contains(lowerTitle, w) {
				score += 3
			}
			score += strings.Count(hay, w)
		}
		if !match {
			continue
		}
		snippet := ""
		lower := strings.ToLower(x.body)
		if at := strings.Index(lower, words[0]); at >= 0 {
			body := []rune(x.body)
			pos := len([]rune(lower[:at]))
			start, end := max(0, pos-60), min(len(body), pos+120)
			if start < end {
				snippet = strings.ReplaceAll(string(body[start:end]), "\n", " ")
			}
		}
		hits = append(hits, map[string]any{"path": x.path, "title": title, "score": score, "snippet": snippet})
	}
	sort.SliceStable(hits, func(i, j int) bool {
		a, b := hits[i]["score"].(int), hits[j]["score"].(int)
		if a != b {
			return a > b
		}
		return hits[i]["path"].(string) < hits[j]["path"].(string)
	})
	total := len(hits)
	if n := max(1, min(limit, 100)); len(hits) > n {
		hits = hits[:n]
	}
	return map[string]any{"query": query, "hits": hits, "total": total}, nil
}

// WikiPageOf reads one page of an already authorized project.
func (s *Store) WikiPageOf(pid, p string) (map[string]any, error) {
	switch p {
	case "index.md":
		items, err := s.wikiPages(pid)
		if err != nil {
			return nil, err
		}
		paths := make([]string, 0, len(items))
		for _, x := range items {
			paths = append(paths, x.path)
		}
		return map[string]any{"path": p, "generated": true, "body": renderWikiIndex(paths)}, nil
	case "log.md":
		body, err := s.renderWikiLog(pid)
		if err != nil {
			return nil, err
		}
		return map[string]any{"path": p, "generated": true, "body": body}, nil
	}
	if !wikiPagePath.MatchString(p) || containsPathTraversal(p) {
		return nil, InvalidField("path", "위키 안 상대 경로 · .md (예: concepts/foo.md)")
	}
	var body, by, at string
	var last, repo, sha sql.NullString
	var version int
	err := s.pool.QueryRow("SELECT body_md,version,updated_by,updated_at,last_ingest,source_repo_key,source_sha FROM wiki_page WHERE project_id=? AND path=?", pid, p).
		Scan(&body, &version, &by, &at, &last, &repo, &sha)
	if err == sql.ErrNoRows {
		return nil, &HubError{Status: 404, Code: "not_found", Message: "위키 페이지가 없어요: " + p, Detail: map[string]any{"path": p}}
	}
	if err != nil {
		return nil, err
	}
	nullable := func(v sql.NullString) any {
		if !v.Valid {
			return nil
		}
		return v.String
	}
	return map[string]any{"path": p, "body": body, "version": version, "updated_by": by, "updated_at": at,
		"last_ingest": nullable(last), "source": map[string]any{"repo_key": nullable(repo), "sha": nullable(sha)}}, nil
}

func (s *Store) renderWikiLog(pid string) (string, error) {
	rows, err := s.pool.Query("SELECT id,callsign,at,log_line,pages_json FROM wiki_ingest WHERE project_id=? ORDER BY seq", pid)
	if err != nil {
		return "", err
	}
	defer rows.Close()
	out := []string{"# Wiki Ingest Log", "", "- 허브가 ingest 기록에서 생성한다 — 손으로 고치지 않는다.", ""}
	for rows.Next() {
		var id, cs, at, line, raw string
		if err := rows.Scan(&id, &cs, &at, &line, &raw); err != nil {
			return "", err
		}
		var pages []map[string]any
		if err := json.Unmarshal([]byte(raw), &pages); err != nil {
			return "", err
		}
		labels := []string{}
		for _, page := range pages {
			v := "삭제"
			if page["deleted"] != true {
				v = fmt.Sprintf("v%v", page["version"])
			}
			labels = append(labels, fmt.Sprintf("%v (%s)", page["path"], v))
		}
		out = append(out, line, "", fmt.Sprintf("- %s · %s · %s", id, cs, at), "- "+strings.Join(labels, ", "), "")
	}
	if err := rows.Err(); err != nil {
		return "", err
	}
	return strings.TrimRight(strings.Join(out, "\n"), "\n") + "\n", nil
}

func wikiSlug(s string) string {
	var b strings.Builder
	dash := false
	for _, r := range strings.ToLower(s) {
		if r >= 'a' && r <= 'z' || r >= '0' && r <= '9' {
			b.WriteRune(r)
			dash = false
		} else if !dash && b.Len() > 0 {
			b.WriteByte('-')
			dash = true
		}
	}
	if v := strings.Trim(b.String(), "-"); v != "" {
		return v
	}
	return "page"
}

func renderWikiIndex(paths []string) string {
	stems := make([]string, 0, len(paths))
	for _, p := range paths {
		stems = append(stems, strings.TrimSuffix(p, ".md"))
	}
	sort.Strings(stems)
	counts := map[string]int{}
	for _, st := range stems {
		counts[wikiSlug(path.Base(st))]++
	}
	sections := map[string][]string{}
	for _, st := range stems {
		anchor := wikiSlug(path.Base(st))
		if counts[anchor] > 1 {
			anchor = wikiSlug(st)
		}
		top := ""
		if i := strings.IndexByte(st, '/'); i >= 0 {
			top = st[:i]
		}
		sections[top] = append(sections[top], "### [["+st+"]] {#"+anchor+"}")
	}
	rank := func(k string) int {
		if k == "" {
			return len(wikiSectionOrder) + 1
		}
		for i, v := range wikiSectionOrder {
			if v == k {
				return i
			}
		}
		return len(wikiSectionOrder)
	}
	keys := make([]string, 0, len(sections))
	for k := range sections {
		keys = append(keys, k)
	}
	sort.Slice(keys, func(i, j int) bool {
		if rank(keys[i]) != rank(keys[j]) {
			return rank(keys[i]) < rank(keys[j])
		}
		return keys[i] < keys[j]
	})
	out := []string{"# Master Knowledge Index", ""}
	for _, k := range keys {
		title := k
		if k == "" {
			title = "Meta"
		} else if rank(k) < len(wikiSectionOrder) {
			title = strings.ToUpper(k[:1]) + k[1:]
		}
		out = append(out, "## "+title, "")
		out = append(out, sections[k]...)
		out = append(out, "")
	}
	return strings.TrimRight(strings.Join(out, "\n"), "\n") + "\n"
}
