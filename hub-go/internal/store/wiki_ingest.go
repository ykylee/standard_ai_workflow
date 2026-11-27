package store

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"regexp"
	"strings"

	"github.com/ykylee/standard_ai_workflow/hub-go/internal/db"
)

var wikiPagePath = regexp.MustCompile(`^(?:[A-Za-z0-9_][A-Za-z0-9_.-]*/)*[A-Za-z0-9_][A-Za-z0-9_.-]*\.md$`)

type wikiWrite struct {
	path, body, repo, sha string
	expected              int
	delete                bool
}

func (s *Store) WikiIngest(ctx Ctx, rawPages any, summary, requestID string) (map[string]any, error) {
	p, err := NeedCallsign(ctx)
	if err != nil {
		return nil, err
	}
	pid := p.ProjectID
	if strings.TrimSpace(summary) == "" || strings.ContainsAny(strings.TrimSpace(summary), "\r\n") {
		return nil, InvalidField("summary", "한 줄 요약이 필요해요")
	}
	if err = ScanSecrets(summary, "summary"); err != nil {
		return nil, err
	}
	items, ok := rawPages.([]any)
	if !ok || len(items) == 0 || len(items) > 200 {
		return nil, InvalidField("pages", "페이지가 1~200개 필요해요")
	}
	pages := []wikiWrite{}
	seen := map[string]bool{}
	for i, raw := range items {
		m, ok := raw.(map[string]any)
		if !ok {
			return nil, InvalidField(fmt.Sprintf("pages[%d]", i), "객체여야 해요")
		}
		for key := range m {
			switch key {
			case "path", "body", "expected_version", "delete", "source":
			default:
				return nil, InvalidField(fmt.Sprintf("pages[%d]", i), "칸은 path · body · expected_version · delete · source")
			}
		}
		path, _ := m["path"].(string)
		if !wikiPagePath.MatchString(path) || path == "index.md" || path == "log.md" || containsPathTraversal(path) {
			return nil, InvalidField("path", "안전한 위키 상대 .md 경로가 필요해요")
		}
		if seen[path] {
			return nil, InvalidField("path", "묶음 안에서 경로가 중복됐어요")
		}
		seen[path] = true
		body, _ := m["body"].(string)
		del, _ := m["delete"].(bool)
		expected := 0
		if v, exists := m["expected_version"]; exists {
			n, ok := v.(int)
			if !ok {
				if n64, ok64 := v.(int64); ok64 {
					n = int(n64)
					ok = true
				}
			}
			if !ok || n < 0 {
				return nil, InvalidField("expected_version", "0 이상 정수")
			}
			expected = n
		}
		if del {
			if _, has := m["body"]; has {
				return nil, InvalidField("body", "delete 와 body 를 같이 줄 수 없어요")
			}
		} else if strings.TrimSpace(body) == "" || len(body) > 192*1024 {
			return nil, InvalidField("body", "본문이 비었거나 192KB를 넘어요")
		}
		if !del {
			if err = ScanSecrets(body, "body"); err != nil {
				return nil, err
			}
		}
		repo, sha := "", ""
		if src, exists := m["source"]; exists && src != nil {
			if del {
				return nil, InvalidField("source", "삭제에는 줄 수 없어요")
			}
			sm, ok := src.(map[string]any)
			if !ok || len(sm) != 2 {
				return nil, InvalidField("source", "repo_key · sha 객체여야 해요")
			}
			repo, _ = sm["repo_key"].(string)
			sha, _ = sm["sha"].(string)
			if repo == "" || !ShaPattern.MatchString(strings.ToLower(sha)) {
				return nil, InvalidField("source", "등록된 repo_key · 16진 sha가 필요해요")
			}
			var n int
			if err = s.DB().QueryRow("SELECT COUNT(*) FROM project_alias WHERE project_id=? AND key=?", pid, repo).Scan(&n); err != nil {
				return nil, err
			}
			if n == 0 {
				return nil, InvalidField("source.repo_key", "이 프로젝트에 등록된 저장소 키가 아니에요")
			}
		}
		pages = append(pages, wikiWrite{path: path, body: body, repo: repo, sha: strings.ToLower(sha), expected: expected, delete: del})
	}
	summary = strings.TrimSpace(summary)
	return s.Idempotent(ctx, requestID, func(tx *sql.Tx) (map[string]any, error) {
		return s.wikiWritePages(tx, ctx, pid, p.Callsign, pages, summary)
	})
}

// wikiWritePages writes an already validated batch inside an open write transaction — wiki ingest and DCR approval
// (the ADR page) take the same path. One stale version rejects the whole batch with 409.
func (s *Store) wikiWritePages(tx *sql.Tx, ctx Ctx, pid, callsign string, pages []wikiWrite, summary string) (map[string]any, error) {
	now := db.FormatISO(ctx.Now)
	versions := map[string]int{}
	conflicts := []map[string]any{}
	for _, pg := range pages {
		var current int
		e := tx.QueryRow("SELECT version FROM wiki_page WHERE project_id=? AND path=?", pid, pg.path).Scan(&current)
		if e != nil && e != sql.ErrNoRows {
			return nil, e
		}
		versions[pg.path] = current
		if current != pg.expected || (pg.delete && current == 0) {
			conflicts = append(conflicts, map[string]any{"path": pg.path, "expected_version": pg.expected, "current_version": current})
		}
	}
	if len(conflicts) > 0 {
		return nil, &HubError{Status: 409, Code: "version_conflict", Message: "위키 page version이 달라요 — 묶음 전체를 거절했어요", Detail: map[string]any{"conflicts": conflicts}}
	}
	var seq int
	if err := tx.QueryRow("SELECT COALESCE(MAX(seq),0)+1 FROM wiki_ingest WHERE project_id=?", pid).Scan(&seq); err != nil {
		return nil, err
	}
	ingestID := fmt.Sprintf("ING-%05d", seq)
	written := []map[string]any{}
	for _, pg := range pages {
		revision := versions[pg.path] + 1
		if pg.delete {
			if _, err := tx.Exec("INSERT INTO wiki_page_revision(project_id,path,revision,body_md,status,updated_by,updated_at) VALUES(?,?,?,'','tombstone',?,?)", pid, pg.path, revision, callsign, now); err != nil {
				return nil, err
			}
			if _, err := tx.Exec("DELETE FROM wiki_page WHERE project_id=? AND path=?", pid, pg.path); err != nil {
				return nil, err
			}
			written = append(written, map[string]any{"path": pg.path, "version": revision, "deleted": true})
			continue
		}
		if _, err := tx.Exec("INSERT INTO wiki_page(project_id,path,body_md,source_repo_key,source_sha,version,updated_by,updated_at,last_ingest) VALUES(?,?,?,?,?,1,?,?,?) ON CONFLICT(project_id,path) DO UPDATE SET body_md=excluded.body_md,source_repo_key=excluded.source_repo_key,source_sha=excluded.source_sha,version=wiki_page.version+1,updated_by=excluded.updated_by,updated_at=excluded.updated_at,last_ingest=excluded.last_ingest", pid, pg.path, pg.body, pg.repo, pg.sha, callsign, now, ingestID); err != nil {
			return nil, err
		}
		if _, err := tx.Exec("INSERT INTO wiki_page_revision(project_id,path,revision,body_md,status,updated_by,updated_at) VALUES(?,?,?,?,'active',?,?)", pid, pg.path, revision, pg.body, callsign, now); err != nil {
			return nil, err
		}
		written = append(written, map[string]any{"path": pg.path, "version": revision})
	}
	logLine := fmt.Sprintf("## [%s] ingest | %s", ctx.Now.Format("2006-01-02"), summary)
	blob, _ := json.Marshal(written)
	if _, err := tx.Exec("INSERT INTO wiki_ingest(project_id,id,seq,callsign,at,log_line,pages_json) VALUES(?,?,?,?,?,?,?)", pid, ingestID, seq, callsign, now, logLine, string(blob)); err != nil {
		return nil, err
	}
	projectID := pid
	if err := s.RecordEvent(tx, ctx, &projectID, "wiki_ingest", ingestID, "ingest", nil, map[string]any{"pages": written}, nil); err != nil {
		return nil, err
	}
	return map[string]any{"ingest_id": ingestID, "log_line": logLine, "pages": written}, nil
}
