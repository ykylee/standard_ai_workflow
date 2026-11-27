package store

import (
	"database/sql"
	"fmt"
	"strings"

	"github.com/ykylee/standard_ai_workflow/hub-go/internal/db"
)

// WikiImportDir takes a 1.x wiki directory: pages byte for byte in one ingest, generated
// index.md/log.md as archive notes, and non-markdown files listed as skipped.
func (s *Store) WikiImportDir(ctx Ctx, rawFiles any, summary string, overwrite bool, requestID string) (map[string]any, error) {
	p, err := NeedCallsign(ctx)
	if err != nil {
		return nil, err
	}
	items, ok := rawFiles.([]any)
	if !ok || len(items) == 0 {
		return nil, InvalidField("files", "[{path, content}] 하나 이상")
	}
	pages := []any{}
	archived := [][2]string{}
	archivedPaths, skipped := []string{}, []string{}
	for i, raw := range items {
		m, ok := raw.(map[string]any)
		content, okC := m["content"].(string)
		path, okP := m["path"].(string)
		if !ok || len(m) != 2 || !okC {
			return nil, InvalidField(fmt.Sprintf("files[%d]", i), "{path, content(문자열)}")
		}
		if !okP || strings.HasPrefix(path, "/") || containsPathTraversal(path) {
			return nil, InvalidField(fmt.Sprintf("files[%d].path", i), "위키 뿌리 상대 경로")
		}
		switch {
		case path == "index.md" || path == "log.md":
			archived = append(archived, [2]string{path, content})
			archivedPaths = append(archivedPaths, path)
		case !strings.HasSuffix(path, ".md"):
			skipped = append(skipped, path)
		default:
			pages = append(pages, map[string]any{"path": path, "body": content})
		}
	}
	if len(pages) == 0 && len(archived) == 0 {
		return nil, InvalidField("files", "들일 위키 페이지가 없어요")
	}
	if overwrite {
		current, err := s.wikiPages(p.ProjectID)
		if err != nil {
			return nil, err
		}
		versions := map[string]int{}
		for _, x := range current {
			versions[x.path] = x.version
		}
		for _, raw := range pages {
			page := raw.(map[string]any)
			page["expected_version"] = versions[page["path"].(string)]
		}
	}
	for _, a := range archived {
		if err := ScanSecrets(a[1], "files."+a[0]); err != nil {
			return nil, err
		}
	}
	result := map[string]any{"pages": []map[string]any{}, "archived_1x": archivedPaths, "skipped_non_page": skipped}
	if len(pages) > 0 {
		out, err := s.WikiIngest(ctx, pages, summary, requestID)
		if err != nil {
			return nil, err
		}
		for k, v := range out {
			result[k] = v
		}
	}
	if len(archived) == 0 {
		return result, nil
	}
	return s.withWriteTx(func(tx *sql.Tx) (map[string]any, error) {
		for _, a := range archived {
			if _, err := tx.Exec("INSERT INTO memory_note (project_id,callsign,kind,title,body_md,meta_json,created_at) VALUES (?,?,'archive_1x',?,?,?,?)",
				p.ProjectID, p.Callsign, "wiki/"+a[0]+" (1.x 원문)", a[1], MustJSON(map[string]any{"source": "hub_wiki_import_dir", "path": a[0]}), db.FormatISO(ctx.Now)); err != nil {
				return nil, err
			}
		}
		return result, nil
	})
}
