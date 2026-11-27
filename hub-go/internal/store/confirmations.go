package store

import (
	"database/sql"
	"encoding/json"
	"errors"

	"github.com/ykylee/standard_ai_workflow/hub-go/internal/db"
	"github.com/ykylee/standard_ai_workflow/hub-go/internal/pytext"
)

// ValidateConfirmation checks the human question an agent wants answered.
func ValidateConfirmation(title, question, details string) (string, string, string, error) {
	title, question, details = pytext.Strip(title), pytext.Strip(question), pytext.Strip(details)
	if title == "" || len([]rune(title)) > 160 {
		return "", "", "", InvalidField("title", "1~160자 문자열")
	}
	if question == "" || len([]rune(question)) > 2000 {
		return "", "", "", InvalidField("question", "1~2000자 문자열")
	}
	if len([]rune(details)) > 4000 {
		return "", "", "", InvalidField("details", "4000자 이하 문자열")
	}
	return title, question, details, ScanSecrets(map[string]any{"title": title, "question": question, "details": details}, "confirmation")
}

// createConfirmation stores one confirmation request; the MCP tool and A2A share it (a session is optional).
func (s *Store) createConfirmation(tx *sql.Tx, ctx Ctx, p *Principal, title, question, details string, action any, sessionID string) (string, map[string]any, error) {
	var owner string
	if err := tx.QueryRow("SELECT owner_callsign FROM project WHERE id=?", p.ProjectID).Scan(&owner); err != nil {
		return "", nil, err
	}
	var params, summary map[string]any
	var err error
	if action != nil {
		if params, summary, err = prepareApproval(tx, p.ProjectID, action); err != nil {
			return "", nil, err
		}
	}
	body := map[string]any{"request_type": "agent_confirmation", "title": title, "question": question,
		"details": details, "requested_by": p.Callsign, "requested_by_session": sessionID, "state": "pending"}
	id, err := s.EnqueueMessage(tx, ctx, p.ProjectID, "callsign", owner, "approval", body, p.Callsign, sessionID, false, "")
	if err != nil {
		return "", nil, err
	}
	var logged any
	if params != nil {
		logged = params
		if _, err := tx.Exec("INSERT INTO approval_grant (id,project_id,action,params_json,summary_json,requested_by,state,created_at) VALUES (?,?,?,?,?,?,'pending',?)",
			id, p.ProjectID, params["type"], MustJSON(params), MustJSON(summary), p.Callsign, db.FormatISO(ctx.Now)); err != nil {
			return "", nil, err
		}
	}
	return id, params, s.RecordEvent(tx, ctx, &p.ProjectID, "confirmation_request", id, "request", nil,
		map[string]any{"state": "pending", "requested_by": p.Callsign, "action": logged}, nil)
}

func (s *Store) ConfirmationRequest(ctx Ctx, sessionID, title, question, details string, action any) (map[string]any, error) {
	p, err := NeedCallsign(ctx)
	if err != nil {
		return nil, err
	}
	if title, question, details, err = ValidateConfirmation(title, question, details); err != nil {
		return nil, err
	}
	return s.withWriteTx(func(tx *sql.Tx) (map[string]any, error) {
		active, err := s.activeSession(tx, p.ProjectID, sessionID)
		if err != nil {
			return nil, err
		}
		if active["callsign"] != p.Callsign {
			return nil, &HubError{Status: 403, Code: "session_not_yours", Message: "이 콜사인의 세션이 아니에요"}
		}
		id, params, err := s.createConfirmation(tx, ctx, p, title, question, details, action, sessionID)
		if err != nil {
			return nil, err
		}
		if params != nil {
			return map[string]any{"request": map[string]any{"id": id, "state": "pending", "title": title, "action": params}, "approval_id": id,
				"next": "사람이 허브 계정으로 로그인해 확인 요청에서 승인하면, 같은 콜사인으로 실행 도구에 approval_id 를 싣는다 (승인 뒤 24시간)."}, nil
		}
		return map[string]any{"request": map[string]any{"id": id, "state": "pending", "title": title},
			"next": "사람이 웹 허브 확인 요청 메뉴에서 결정할 때까지 대기한다. 결과는 허브 받은편지함으로 온다."}, nil
	})
}

func (s *Store) ConfirmationList(ctx Ctx) (map[string]any, error) {
	p, err := needOwner(ctx)
	if err != nil {
		return nil, err
	}
	actions, err := s.pendingApprovals(p.ProjectID)
	if err != nil {
		return nil, err
	}
	rows, err := s.DB().Query("SELECT id,from_callsign,from_session,body_json,created_at FROM inbox_message WHERE project_id=? AND to_kind='callsign' AND to_id=? AND kind='approval' AND state IN ('queued','delivered','unacknowledged') ORDER BY created_at DESC LIMIT 200", p.ProjectID, p.Callsign)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	requests := []map[string]any{}
	for rows.Next() {
		var id, fromCallsign, fromSession, raw, created string
		if err := rows.Scan(&id, &fromCallsign, &fromSession, &raw, &created); err != nil {
			return nil, err
		}
		var parsed any
		if err := json.Unmarshal([]byte(raw), &parsed); err != nil {
			return nil, err
		}
		body, _ := parsed.(map[string]any) // 객체가 아니면 확인 요청이 아니다
		if body["request_type"] != "agent_confirmation" {
			continue
		}
		requests = append(requests, map[string]any{"id": id, "requested_by": fromCallsign,
			"requested_by_session": fromSession, "created_at": created, "title": body["title"],
			"question": body["question"], "details": body["details"], "action": actions[id]})
	}
	return map[string]any{"requests": requests}, rows.Err()
}

func (s *Store) ConfirmationDecide(ctx Ctx, requestID, decision, note string) (map[string]any, error) {
	p, err := needOwner(ctx)
	if err != nil {
		return nil, err
	}
	if decision != "approve" && decision != "reject" {
		return nil, InvalidField("decision", "approve · reject")
	}
	if len(note) > 1000 {
		return nil, InvalidField("note", "1000자 이하 문자열")
	}
	if err := ScanSecrets(note, "note"); err != nil {
		return nil, err
	}
	target := "acked"
	state := "approved"
	if decision == "reject" {
		target, state = "declined", "rejected"
	}
	var replyID string
	result, err := s.withWriteTx(func(tx *sql.Tx) (map[string]any, error) {
		var from, raw, old string
		err := tx.QueryRow("SELECT from_callsign,body_json,state FROM inbox_message WHERE project_id=? AND id=? AND to_kind='callsign' AND to_id=? AND kind='approval'",
			p.ProjectID, requestID, p.Callsign).Scan(&from, &raw, &old)
		if errors.Is(err, sql.ErrNoRows) {
			return nil, NotFound("확인 요청이 없어요: " + requestID)
		}
		if err != nil {
			return nil, err
		}
		var parsed any
		if err := json.Unmarshal([]byte(raw), &parsed); err != nil {
			return nil, err
		}
		body, _ := parsed.(map[string]any) // 객체가 아니면 확인 요청이 아니다
		if body["request_type"] != "agent_confirmation" {
			return nil, NotFound("에이전트 확인 요청이 아니에요: " + requestID)
		}
		if old == "acked" || old == "declined" {
			if old == target {
				return map[string]any{"request": map[string]any{"id": requestID, "state": state}, "unchanged": true}, nil
			}
			return nil, &HubError{Status: 409, Code: "already_decided", Message: "이미 다른 결정을 내린 요청이에요", Detail: map[string]any{"state": old}}
		}
		if old == "expired" {
			return nil, &HubError{Status: 409, Code: "request_expired", Message: "만료된 확인 요청이에요"}
		}
		if err := decideApproval(tx, ctx, p, requestID, decision == "approve"); err != nil {
			return nil, err
		}
		if _, err := tx.Exec("UPDATE inbox_message SET state=?,acked_at=?,ack_by_session=?,ack_reason=?,version=version+1 WHERE project_id=? AND id=?",
			target, db.FormatISO(ctx.Now), "web:"+p.Callsign, note, p.ProjectID, requestID); err != nil {
			return nil, err
		}
		if err := s.RecordEvent(tx, ctx, &p.ProjectID, "confirmation_request", requestID, decision, map[string]any{"state": "pending"}, map[string]any{"state": state, "note": note}, nil); err != nil {
			return nil, err
		}
		message, err := s.EnqueueMessage(tx, ctx, p.ProjectID, "callsign", from, "note",
			map[string]any{"event": "confirmation_result", "request_id": requestID, "decision": decision,
				"state": state, "title": body["title"], "note": note}, p.Callsign, "", false, "")
		if err != nil {
			return nil, err
		}
		replyID = message
		return map[string]any{"request": map[string]any{"id": requestID, "state": state}}, nil
	})
	if err != nil {
		return nil, err
	}
	if _, ok := result["unchanged"]; !ok {
		result["message_id"] = replyID
	}
	return result, nil
}
