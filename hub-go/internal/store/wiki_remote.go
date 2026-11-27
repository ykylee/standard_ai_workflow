package store

import (
	"database/sql"
	"regexp"
	"strings"
)

// WikiBody is one wiki page with the source commit it was written from.
type WikiBody struct{ Path, Body, SourceSHA string }

// WikiBodies returns every page of an already authorized project, in path order.
func (s *Store) WikiBodies(projectID string) ([]WikiBody, error) {
	rows, err := s.pool.Query("SELECT path,body_md,source_sha FROM wiki_page WHERE project_id=? ORDER BY path", projectID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	out := []WikiBody{}
	for rows.Next() {
		var b WikiBody
		if err := rows.Scan(&b.Path, &b.Body, &b.SourceSHA); err != nil {
			return nil, err
		}
		out = append(out, b)
	}
	return out, rows.Err()
}

// git 원격 도우미(ext:: · fd::)는 명령 실행이 되므로 막는다.
var wikiFetchURL = regexp.MustCompile(`^(?:https://\S+|ssh://\S+|git@[A-Za-z0-9.-]+:\S+|file:///\S+)$`)

// WikiRemoteSet turns the read-only fetch of the project's repository on or off; only an owner may.
func (s *Store) WikiRemoteSet(ctx Ctx, fetchURL string) (map[string]any, error) {
	p, err := NeedCallsign(ctx)
	if err != nil {
		return nil, err
	}
	if p.Role != "owner" {
		return nil, Forbidden("위키 원격 읽기는 소유자만 켜고 꺼요 — 허브가 외부에 접속하는 유일한 설정이에요 (R3.7 · R8.4)")
	}
	if fetchURL != "" && !s.WikiRemoteAllowed {
		return nil, &HubError{Status: 403, Code: "wiki_remote_disabled", Message: "바깥에 노출된 허브라 위키 원격 읽기가 꺼져 있어요 — 운영자가 serve --allow-wiki-remote 로 켜요"}
	}
	if fetchURL != "" && (!wikiFetchURL.MatchString(fetchURL) || strings.HasPrefix(fetchURL, "-")) {
		return nil, InvalidField("fetch_url", "https:// · ssh:// · git@host:path · file:/// 만 (git 원격 도우미 주소는 거절)")
	}
	return s.withWriteTx(func(tx *sql.Tx) (map[string]any, error) {
		settings, err := projectSettings(tx, p.ProjectID)
		if err != nil {
			return nil, err
		}
		before := settings["wiki_remote"]
		delete(settings, "wiki_remote")
		if fetchURL != "" {
			settings["wiki_remote"] = map[string]any{"fetch_url": fetchURL}
		}
		if _, err := tx.Exec("UPDATE project SET settings_json=? WHERE id=?", MustJSON(settings), p.ProjectID); err != nil {
			return nil, err
		}
		if err := s.RecordEvent(tx, ctx, &p.ProjectID, "project", p.ProjectID, "wiki_remote", before, settings["wiki_remote"], nil); err != nil {
			return nil, err
		}
		return map[string]any{"wiki_remote": settings["wiki_remote"], "enabled": fetchURL != ""}, nil
	})
}
