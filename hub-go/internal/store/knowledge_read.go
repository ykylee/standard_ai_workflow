package store

import (
	"database/sql"
	"encoding/json"
	"strconv"
	"strings"
)

func (s *Store) KnowledgeGet(ctx Ctx, ref string) (map[string]any, error) {
	_, pid, err := knowledgeReader(ctx)
	if err != nil {
		return nil, err
	}
	if strings.HasPrefix(ref, "hub-dcr:") {
		v := strings.TrimPrefix(ref, "hub-dcr:")
		i := strings.LastIndex(v, "@")
		if i < 0 {
			return nil, InvalidField("ref", "hub-dcr:id@version 형식")
		}
		version, parseErr := strconv.Atoi(v[i+1:])
		if parseErr != nil {
			return nil, InvalidField("ref", "hub-dcr:id@version 형식")
		}
		result, getErr := s.DCRGet(ctx, v[:i])
		if getErr != nil {
			return nil, getErr
		}
		if result["version"] != version {
			return nil, NotFound("knowledge ref가 없다: " + ref)
		}
		return result, nil
	}
	if strings.HasPrefix(ref, "hub-memory:") {
		v := strings.TrimPrefix(ref, "hub-memory:")
		i := strings.LastIndex(v, "@")
		if i < 0 {
			return nil, InvalidField("ref", "hub-memory:id@version 형식")
		}
		version, parseErr := strconv.Atoi(v[i+1:])
		if parseErr != nil {
			return nil, InvalidField("ref", "hub-memory:id@version 형식")
		}
		var body, updated, by string
		err = s.DB().QueryRow("SELECT body_json,updated_at,updated_by FROM memory_entry WHERE project_id=? AND id=? AND version=?", pid, v[:i], version).Scan(&body, &updated, &by)
		if err == sql.ErrNoRows {
			return nil, NotFound("knowledge ref가 없다: " + ref)
		}
		if err != nil {
			return nil, err
		}
		var decoded any
		if err = json.Unmarshal([]byte(body), &decoded); err != nil {
			return nil, err
		}
		return map[string]any{"ref": ref, "kind": "memory", "id": v[:i], "body": decoded, "authority": "hub", "revision": version, "updated_by": by, "updated_at": updated}, nil
	}
	if strings.HasPrefix(ref, "hub-wiki:") {
		v := strings.TrimPrefix(ref, "hub-wiki:")
		i := strings.LastIndex(v, "@")
		if i < 0 {
			return nil, InvalidField("ref", "hub-wiki:path@revision 형식")
		}
		var body, status, at string
		var revision int
		err = s.DB().QueryRow("SELECT body_md,status,updated_at,revision FROM wiki_page_revision WHERE project_id=? AND path=? AND revision=?", pid, v[:i], v[i+1:]).Scan(&body, &status, &at, &revision)
		if err == sql.ErrNoRows || status == "tombstone" {
			return nil, NotFound("knowledge ref가 없다: " + ref)
		}
		if err != nil {
			return nil, err
		}
		return map[string]any{"ref": ref, "kind": "wiki", "path": v[:i], "body": body, "revision": revision, "authority": "hub", "updated_at": at}, nil
	}
	if !strings.HasPrefix(ref, "git:") {
		return nil, InvalidField("ref", "git:repo_key:path@commit 또는 hub-wiki:path@revision 형식")
	}
	v := strings.TrimPrefix(ref, "git:")
	i := strings.Index(v, ":")
	j := strings.LastIndex(v, "@")
	if i < 1 || j <= i {
		return nil, InvalidField("ref", "git:repo_key:path@commit 형식")
	}
	var body, title, status, digest string
	var revision int
	err = s.DB().QueryRow("SELECT r.body_md,r.title,r.status,r.content_sha256,r.revision FROM knowledge_revision r JOIN knowledge_source s ON s.project_id=r.project_id AND s.id=r.source_id WHERE r.project_id=? AND s.repo_key=? AND r.path=? AND r.commit_sha=? ORDER BY r.revision DESC LIMIT 1", pid, v[:i], v[i+1:j], v[j+1:]).Scan(&body, &title, &status, &digest, &revision)
	if err == sql.ErrNoRows {
		return nil, NotFound("knowledge ref가 없다: " + ref)
	}
	if err != nil {
		return nil, err
	}
	return map[string]any{"ref": ref, "kind": "design_doc", "path": v[i+1 : j], "title": title, "body": body, "authority": "git", "revision": revision, "source_sha": v[j+1:], "content_sha256": digest, "status": status}, nil
}

func (s *Store) DCRList(ctx Ctx, status string) (map[string]any, error) {
	_, pid, err := knowledgeReader(ctx)
	if err != nil {
		return nil, err
	}
	q := "SELECT id,title,status,version,author,reviewer,created_at,updated_at FROM decision_change WHERE project_id=?"
	args := []any{pid}
	if status != "" {
		q += " AND status=?"
		args = append(args, status)
	}
	q += " ORDER BY created_at DESC"
	rows, err := s.DB().Query(q, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	out := []map[string]any{}
	for rows.Next() {
		var id, title, st, author, created, updated string
		var reviewer sql.NullString
		var version int
		if err = rows.Scan(&id, &title, &st, &version, &author, &reviewer, &created, &updated); err != nil {
			return nil, err
		}
		out = append(out, map[string]any{"id": id, "title": title, "status": st, "version": version, "author": author, "reviewer": reviewer.String, "created_at": created, "updated_at": updated})
	}
	return map[string]any{"dcrs": out}, rows.Err()
}

func (s *Store) DCRGet(ctx Ctx, id string) (map[string]any, error) {
	_, pid, err := knowledgeReader(ctx)
	if err != nil {
		return nil, err
	}
	var title, rationale, proposal, targets, bases, status, author, created, updated string
	var reviewer, decision, adrPath, adrHash sql.NullString
	var version int
	err = s.DB().QueryRow("SELECT title,rationale,proposal_md,target_refs_json,base_revisions_json,status,version,author,reviewer,decision_rationale,adr_path,adr_sha256,created_at,updated_at FROM decision_change WHERE project_id=? AND id=?", pid, id).Scan(&title, &rationale, &proposal, &targets, &bases, &status, &version, &author, &reviewer, &decision, &adrPath, &adrHash, &created, &updated)
	if err == sql.ErrNoRows {
		return nil, NotFound("DCR이 없다: " + id)
	}
	if err != nil {
		return nil, err
	}
	var refs, base any
	_ = json.Unmarshal([]byte(targets), &refs)
	_ = json.Unmarshal([]byte(bases), &base)
	events, err := s.DB().Query("SELECT at,actor,op,before_json,after_json FROM decision_event WHERE project_id=? AND dcr_id=? ORDER BY seq", pid, id)
	if err != nil {
		return nil, err
	}
	defer events.Close()
	timeline := []map[string]any{}
	for events.Next() {
		var at, actor, op string
		var before, after sql.NullString
		if err = events.Scan(&at, &actor, &op, &before, &after); err != nil {
			return nil, err
		}
		timeline = append(timeline, map[string]any{"at": at, "actor": actor, "op": op, "before_json": before.String, "after_json": after.String})
	}
	return map[string]any{"id": id, "title": title, "rationale": rationale, "proposal_md": proposal, "target_refs": refs, "base_revisions": base, "status": status, "version": version, "author": author, "reviewer": reviewer.String, "decision_rationale": decision.String, "adr_path": adrPath.String, "adr_sha256": adrHash.String, "created_at": created, "updated_at": updated, "timeline": timeline}, events.Err()
}
