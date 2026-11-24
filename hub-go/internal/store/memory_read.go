package store

import (
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"regexp"
	"sort"
	"strings"

	"github.com/ykylee/standard_ai_workflow/hub-go/internal/db"
)

// 콜사인 작업 기억 · 프로젝트 문서 — Python hub/memory.py 의 읽기 · 쓰기 (session_end 는 memory.go).

const projectDocMax = 192 * 1024

var (
	memoryIdentRe  = regexp.MustCompile("`([^`]{2,80})`")
	memoryTaskIDRe = regexp.MustCompile(`TASK-\d{4}-\d{2}-\d{2}(?:-[A-Za-z0-9._-]+?)?-\d{3}`)
	checkpointKeys = []string{"branch", "next", "rejected", "tasks", "unverified", "verified"}
)

func checkDocName(name string) error {
	if name != "purpose" && name != "profile" {
		return InvalidField("name", "purpose · profile")
	}
	return nil
}

func checkDoc(name, body string) error {
	if err := checkDocName(name); err != nil {
		return err
	}
	if strings.TrimSpace(body) == "" || len(body) > projectDocMax {
		return InvalidField("body", "비지 않은 문자열 · 192KB 이하")
	}
	return nil
}

// ProjectDocGet reads purpose or profile; a missing document has version 0.
func (s *Store) ProjectDocGet(ctx Ctx, name string) (map[string]any, error) {
	p, err := NeedReader(ctx)
	if err != nil {
		return nil, err
	}
	if err := checkDocName(name); err != nil {
		return nil, err
	}
	var body, by, at string
	var version int
	err = s.pool.QueryRow("SELECT body_md,version,updated_by,updated_at FROM project_doc WHERE project_id=? AND name=?", p.ProjectID, name).Scan(&body, &version, &by, &at)
	if errors.Is(err, sql.ErrNoRows) {
		return map[string]any{"name": name, "body": nil, "version": 0}, nil
	}
	if err != nil {
		return nil, err
	}
	return map[string]any{"name": name, "body": body, "version": version, "updated_by": by, "updated_at": at}, nil
}

// ProjectDocPut writes a project document; an approved human may, or a callsign holding a login approval for this body and version.
func (s *Store) ProjectDocPut(ctx Ctx, name, body string, expected *int, approvalID string) (map[string]any, error) {
	p, err := NeedCallsign(ctx)
	if err != nil {
		return nil, err
	}
	if err := checkDoc(name, body); err != nil {
		return nil, err
	}
	if approvalID != "" {
		var version any
		if expected != nil {
			version = *expected
		}
		if _, err := s.ApprovalAuthorize(ctx, approvalID, "project_doc_put", map[string]any{"name": name, "expected_version": version, "sha256": docSHA(body)}); err != nil {
			return nil, err
		}
	} else if p.CallsignKind != "human" || !p.HumanApproved {
		return nil, Forbidden("프로젝트 문서는 승인된 human 콜사인이 쓰거나, action=project_doc_put 으로 로그인 승인받은 approval_id 가 필요하다")
	}
	return s.putProjectDoc(ctx, p, name, body, expected, approvalID)
}

// ProjectDocImport writes a new document for an already authorized migration (owner or login approval).
func (s *Store) ProjectDocImport(ctx Ctx, name, body string) (map[string]any, error) {
	p, err := NeedCallsign(ctx)
	if err != nil {
		return nil, err
	}
	zero := 0
	return s.putProjectDoc(ctx, p, name, body, &zero, "")
}

func (s *Store) putProjectDoc(ctx Ctx, p *Principal, name, body string, expected *int, approvalID string) (map[string]any, error) {
	if err := checkDoc(name, body); err != nil {
		return nil, err
	}
	if err := ScanSecrets(body, "body"); err != nil {
		return nil, err
	}
	return s.withWriteTx(func(tx *sql.Tx) (map[string]any, error) {
		var current int
		err := tx.QueryRow("SELECT version FROM project_doc WHERE project_id=? AND name=?", p.ProjectID, name).Scan(&current)
		if err != nil && !errors.Is(err, sql.ErrNoRows) {
			return nil, err
		}
		if expected != nil && *expected != current {
			return nil, &HubError{Status: 409, Code: "version_conflict", Message: fmt.Sprintf("version 이 다르다 — 지금 %d", current), Detail: map[string]any{"current_version": current}}
		}
		if _, err := tx.Exec("INSERT INTO project_doc (project_id,name,body_md,version,updated_by,updated_at) VALUES (?,?,?,1,?,?) ON CONFLICT(project_id,name) DO UPDATE SET body_md=excluded.body_md,version=project_doc.version+1,updated_by=excluded.updated_by,updated_at=excluded.updated_at", p.ProjectID, name, body, p.Callsign, db.FormatISO(ctx.Now)); err != nil {
			return nil, err
		}
		after := map[string]any{"version": current + 1}
		if approvalID != "" {
			if err := ApprovalConsume(tx, ctx, p.ProjectID, approvalID); err != nil {
				return nil, err
			}
			after["approval_id"] = approvalID
		}
		if err := s.RecordEvent(tx, ctx, &p.ProjectID, "project_doc", name, "put", map[string]any{"version": current}, after, nil); err != nil {
			return nil, err
		}
		return map[string]any{"name": name, "version": current + 1}, nil
	})
}

// HandoffGet reads a callsign's handoff (default: the caller's own).
func (s *Store) HandoffGet(ctx Ctx, callsign string) (map[string]any, error) {
	p, err := NeedReader(ctx)
	if err != nil {
		return nil, err
	}
	who := callsign
	if who == "" {
		who = p.Callsign
	}
	if who == "" {
		return nil, InvalidField("callsign", "필수 (화면에서 읽을 때)")
	}
	var revoked sql.NullString
	err = s.pool.QueryRow("SELECT revoked_at FROM callsign WHERE project_id=? AND id=?", p.ProjectID, who).Scan(&revoked)
	if errors.Is(err, sql.ErrNoRows) {
		return nil, NotFound("콜사인이 없다: " + who)
	}
	if err != nil {
		return nil, err
	}
	var raw, at string
	var version int
	err = s.pool.QueryRow("SELECT sections_json,version,updated_at FROM handoff WHERE project_id=? AND callsign=?", p.ProjectID, who).Scan(&raw, &version, &at)
	if errors.Is(err, sql.ErrNoRows) {
		return map[string]any{"callsign": who, "handoff": nil, "version": 0, "archived": revoked.Valid}, nil
	}
	if err != nil {
		return nil, err
	}
	var sections map[string]any
	if err := json.Unmarshal([]byte(raw), &sections); err != nil {
		return nil, err
	}
	return map[string]any{"callsign": who, "handoff": sections, "version": version, "updated_at": at, "archived": revoked.Valid}, nil
}

// HandoffPut replaces the caller's handoff.
func (s *Store) HandoffPut(ctx Ctx, expected *int, handoff map[string]any) (map[string]any, error) {
	p, err := NeedCallsign(ctx)
	if err != nil {
		return nil, err
	}
	clean, err := validateHandoff(handoff)
	if err != nil {
		return nil, err
	}
	return s.withWriteTx(func(tx *sql.Tx) (map[string]any, error) { return putHandoff(tx, ctx, p, expected, clean) })
}

// CheckpointPut stores the pre-compaction checkpoint.
func (s *Store) CheckpointPut(ctx Ctx, raw any) (map[string]any, error) {
	p, err := NeedCallsign(ctx)
	if err != nil {
		return nil, err
	}
	body, ok := raw.(map[string]any)
	keys := []string{}
	for k := range body {
		known := false
		for _, a := range checkpointKeys {
			known = known || a == k
		}
		ok = ok && known
		keys = append(keys, k)
	}
	if !ok {
		return nil, InvalidField("body", "칸은 "+strings.Join(checkpointKeys, ", ")+" (compact_relay_spec §3)")
	}
	sort.Strings(keys)
	if err := ScanSecrets(body, "checkpoint"); err != nil {
		return nil, err
	}
	encoded, err := EncodeJSON(body)
	if err != nil {
		return nil, err
	}
	return s.withWriteTx(func(tx *sql.Tx) (map[string]any, error) {
		at := db.FormatISO(ctx.Now)
		if _, err := tx.Exec("INSERT INTO checkpoint (project_id,callsign,created_at,body_json) VALUES (?,?,?,?)", p.ProjectID, p.Callsign, at, encoded); err != nil {
			return nil, err
		}
		if err := s.RecordEvent(tx, ctx, &p.ProjectID, "checkpoint", p.Callsign, "put", nil, map[string]any{"keys": keys}, nil); err != nil {
			return nil, err
		}
		return map[string]any{"callsign": p.Callsign, "created_at": at}, nil
	})
}

func scanMaps(rows *sql.Rows) ([]map[string]any, error) {
	defer rows.Close()
	cols, err := rows.Columns()
	if err != nil {
		return nil, err
	}
	out := []map[string]any{}
	for rows.Next() {
		vals, ptrs := make([]any, len(cols)), make([]any, len(cols))
		for i := range vals {
			ptrs[i] = &vals[i]
		}
		if err := rows.Scan(ptrs...); err != nil {
			return nil, err
		}
		m := map[string]any{}
		for i, c := range cols {
			if b, ok := vals[i].([]byte); ok {
				m[c] = string(b)
			} else {
				m[c] = vals[i]
			}
		}
		out = append(out, m)
	}
	return out, rows.Err()
}

// CompactResume returns the checkpoint, my open tasks and what others changed since.
func (s *Store) CompactResume(ctx Ctx, rawIDs any) (map[string]any, error) {
	p, err := NeedCallsign(ctx)
	if err != nil {
		return nil, err
	}
	var have map[string]bool
	if rawIDs != nil {
		list, ok := rawIDs.([]any)
		if !ok {
			return nil, InvalidField("summary_ids", "문자열 목록")
		}
		have = map[string]bool{}
		for _, item := range list {
			if text, ok := item.(string); ok {
				have[text] = true
			}
		}
	}
	rows, err := s.pool.Query("SELECT id,title,status,version,progress_note FROM task WHERE project_id=? AND assignee=? AND status!='done'", p.ProjectID, p.Callsign)
	if err != nil {
		return nil, err
	}
	mine, err := scanMaps(rows)
	if err != nil {
		return nil, err
	}
	var at, raw string
	err = s.pool.QueryRow("SELECT created_at,body_json FROM checkpoint WHERE project_id=? AND callsign=? ORDER BY created_at DESC,rowid DESC LIMIT 1", p.ProjectID, p.Callsign).Scan(&at, &raw)
	if errors.Is(err, sql.ErrNoRows) {
		return map[string]any{"checkpoint": nil, "my_tasks": mine, "changed_by_others": []any{}, "missing_from_summary": nil,
			"note": "체크포인트가 없다 — 진행 기록과 내 task 에서 잇는다"}, nil
	}
	if err != nil {
		return nil, err
	}
	var mark sql.NullInt64
	if err := s.pool.QueryRow("SELECT MAX(seq) FROM event WHERE project_id=? AND target_kind='checkpoint' AND callsign=?", p.ProjectID, p.Callsign).Scan(&mark); err != nil {
		return nil, err
	}
	rows, err = s.pool.Query("SELECT seq,at,callsign,target_id,op FROM event WHERE project_id=? AND target_kind='task' AND seq>? AND (callsign IS NULL OR callsign!=?) AND target_id IN (SELECT id FROM task WHERE project_id=? AND assignee=?) ORDER BY seq", p.ProjectID, mark.Int64, p.Callsign, p.ProjectID, p.Callsign)
	if err != nil {
		return nil, err
	}
	others, err := scanMaps(rows)
	if err != nil {
		return nil, err
	}
	body := map[string]any{}
	if err := json.Unmarshal([]byte(raw), &body); err != nil {
		return nil, err
	}
	idents := map[string]bool{}
	for _, m := range memoryTaskIDRe.FindAllString(raw, -1) {
		idents[m] = true
	}
	for _, m := range memoryIdentRe.FindAllStringSubmatch(raw, -1) {
		idents[m[1]] = true
	}
	checkpoint := map[string]any{"created_at": at}
	for k, v := range body {
		checkpoint[k] = v
	}
	var missing any
	compare := "대조 불가 — 요약 식별자를 받지 못했다"
	if have != nil {
		list := []string{}
		for id := range idents {
			if !have[id] {
				list = append(list, id)
			}
		}
		sort.Strings(list)
		missing, compare = list, "대조함"
	}
	return map[string]any{"checkpoint": checkpoint, "my_tasks": mine, "changed_by_others": others, "missing_from_summary": missing,
		"compare": compare, "rule": "끝난 것으로 기록된 일을 다시 하지 않고, unverified 는 미검증으로 보고한다"}, nil
}
