package store

import (
	"database/sql"
	"encoding/json"
	"errors"
	"reflect"
	"sort"
	"time"

	"github.com/ykylee/standard_ai_workflow/hub-go/internal/db"
)

// 사람이 웹에서 로그인해 여는 실행 승인 — Python hub/approval_grants.py 와 같은 계약.
// 대상에 묶이고 만료되며 한 번 쓰면 끝난다. 받은편지함 상태는 권한 근거가 아니다.

const approvalActionForm = "{type: migrate_import, migration_id, kinds} · {type: migrate_marker, migration_id, marker: issue|revert}"

var approvalKinds = []string{"tasks", "archive", "handoff", "roadmap", "wiki", "memory_index", "checkpoint", "guide_draft", "plan_responses", "project_docs"}

func prepareApproval(tx *sql.Tx, projectID string, raw any) (map[string]any, map[string]any, error) {
	action, ok := raw.(map[string]any)
	mig, okMig := action["migration_id"].(string)
	kind, _ := action["type"].(string)
	extra := map[string]string{"migrate_import": "kinds", "migrate_marker": "marker"}[kind]
	_, okExtra := action[extra]
	if !ok || !okMig || extra == "" || !okExtra || len(action) != 3 {
		return nil, nil, InvalidField("action", approvalActionForm)
	}
	var status, planRaw, plannedBy string
	err := tx.QueryRow("SELECT status,plan_json,callsign FROM migration_1x WHERE project_id=? AND id=?", projectID, mig).Scan(&status, &planRaw, &plannedBy)
	if errors.Is(err, sql.ErrNoRows) {
		return nil, nil, NotFound("전환 계획이 없다: " + mig)
	}
	if err != nil {
		return nil, nil, err
	}
	var plan struct {
		Detected struct {
			Branch      string         `json:"branch"`
			Head        string         `json:"head"`
			Uncommitted []any          `json:"uncommitted"`
			Counts      map[string]int `json:"counts"`
		} `json:"detected"`
	}
	if err := json.Unmarshal([]byte(planRaw), &plan); err != nil {
		return nil, nil, err
	}
	d := plan.Detected
	summary := map[string]any{"migration_id": mig, "planned_by": plannedBy, "branch": d.Branch, "head": d.Head, "uncommitted": len(d.Uncommitted)}
	if kind == "migrate_import" {
		list, _ := action["kinds"].([]any)
		set := map[string]bool{}
		valid := len(list) > 0
		for _, item := range list {
			name, _ := item.(string)
			known := false
			for _, k := range approvalKinds {
				known = known || k == name
			}
			valid = valid && known
			set[name] = true
		}
		if !valid {
			return nil, nil, InvalidField("action.kinds", "전환 종류 가운데 하나 이상")
		}
		if status == "done" {
			return nil, nil, &HubError{Status: 409, Code: "already_done", Message: mig + " 는 이미 끝난 전환이다"}
		}
		kinds, files := []string{}, map[string]any{}
		for k := range set {
			kinds = append(kinds, k)
			files[k] = d.Counts[k]
		}
		sort.Strings(kinds)
		summary["files"] = files
		return map[string]any{"type": kind, "migration_id": mig, "kinds": kinds}, summary, nil
	}
	marker, _ := action["marker"].(string)
	if marker != "issue" && marker != "revert" {
		return nil, nil, InvalidField("action.marker", "issue · revert")
	}
	if status != "done" {
		return nil, nil, &HubError{Status: 409, Code: "migration_not_done", Message: mig + " 가 아직 끝나지 않았다"}
	}
	summary["marker"] = marker
	return map[string]any{"type": kind, "migration_id": mig, "marker": marker}, summary, nil
}

// decideApproval records the decision for a request that carries an action.
// Approving needs an account login: an owner callsign token may also be held by an agent.
func decideApproval(tx *sql.Tx, ctx Ctx, p *Principal, requestID string, approve bool) error {
	var state string
	err := tx.QueryRow("SELECT state FROM approval_grant WHERE project_id=? AND id=?", p.ProjectID, requestID).Scan(&state)
	if errors.Is(err, sql.ErrNoRows) {
		return nil
	}
	if err != nil {
		return err
	}
	if approve && (ctx.Via != "ui" || p.AuthMode != "account") {
		return &HubError{Status: 403, Code: "account_login_required", Message: "실행을 여는 승인은 허브 계정으로 로그인한 화면에서만 한다"}
	}
	if state != "pending" {
		return &HubError{Status: 409, Code: "already_decided", Message: "이미 결정한 실행 승인이다", Detail: map[string]any{"state": state}}
	}
	next := "rejected"
	var expires, account any
	if approve {
		next, expires = "approved", db.FormatISO(ctx.Now.Add(24*time.Hour))
	}
	if p.AccountName != "" {
		account = p.AccountName
	}
	_, err = tx.Exec("UPDATE approval_grant SET state=?,decided_by=?,decided_account=?,decided_at=?,expires_at=? WHERE project_id=? AND id=?",
		next, p.Callsign, account, db.FormatISO(ctx.Now), expires, p.ProjectID, requestID)
	return err
}

func (s *Store) pendingApprovals(projectID string) (map[string]any, error) {
	rows, err := s.pool.Query("SELECT id,action,params_json,summary_json FROM approval_grant WHERE project_id=? AND state='pending'", projectID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	out := map[string]any{}
	for rows.Next() {
		var id, action, params, summary string
		if err := rows.Scan(&id, &action, &params, &summary); err != nil {
			return nil, err
		}
		out[id] = map[string]any{"type": action, "params": json.RawMessage(params), "summary": json.RawMessage(summary)}
	}
	return out, rows.Err()
}

// ApprovalAuthorize checks that an approved grant covers exactly this call by this callsign.
func (s *Store) ApprovalAuthorize(ctx Ctx, approvalID, action string, want map[string]any) (*Principal, error) {
	p, err := NeedCallsign(ctx)
	if err != nil {
		return nil, err
	}
	var kind, raw, by, state string
	var decidedBy, expires sql.NullString
	err = s.pool.QueryRow("SELECT action,params_json,requested_by,state,decided_by,expires_at FROM approval_grant WHERE project_id=? AND id=?", p.ProjectID, approvalID).
		Scan(&kind, &raw, &by, &state, &decidedBy, &expires)
	if errors.Is(err, sql.ErrNoRows) {
		return nil, NotFound("실행 승인 요청이 없다: " + approvalID)
	}
	if err != nil {
		return nil, err
	}
	var params, expect map[string]any
	if err := json.Unmarshal([]byte(raw), &params); err != nil {
		return nil, err
	}
	want["type"] = action
	if err := json.Unmarshal([]byte(MustJSON(want)), &expect); err != nil {
		return nil, err
	}
	if by != p.Callsign || kind != action || !reflect.DeepEqual(params, expect) {
		return nil, &HubError{Status: 403, Code: "approval_mismatch", Message: "승인한 콜사인 · 실행 · 대상과 다르다", Detail: map[string]any{"approved": params}}
	}
	if state != "approved" {
		return nil, &HubError{Status: 403, Code: "approval_" + state, Message: "실행 승인 상태: " + state, Detail: map[string]any{"state": state}}
	}
	if expires.String <= db.FormatISO(ctx.Now) {
		return nil, &HubError{Status: 403, Code: "approval_expired", Message: "승인한 지 24시간이 지났다 — 다시 요청한다"}
	}
	var n int
	if err := s.pool.QueryRow("SELECT COUNT(*) FROM callsign WHERE project_id=? AND id=? AND revoked_at IS NULL AND role='owner' AND kind='human' AND human_approved=1", p.ProjectID, decidedBy.String).Scan(&n); err != nil {
		return nil, err
	}
	if n == 0 {
		return nil, &HubError{Status: 403, Code: "approval_revoked", Message: "승인한 사람이 더 이상 프로젝트 소유자가 아니다"}
	}
	return p, nil
}

// ApprovalConsume closes a used grant.
func ApprovalConsume(tx *sql.Tx, ctx Ctx, projectID, approvalID string) error {
	_, err := tx.Exec("UPDATE approval_grant SET state='used',used_at=? WHERE project_id=? AND id=?", db.FormatISO(ctx.Now), projectID, approvalID)
	return err
}
