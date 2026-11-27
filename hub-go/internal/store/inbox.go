package store

import (
	"crypto/rand"
	"database/sql"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"regexp"
	"strings"
	"time"

	"github.com/ykylee/standard_ai_workflow/hub-go/internal/db"
)

var messageIDPattern = regexp.MustCompile(`^MSG-\d{8}-[0-9a-f]{12}$`)

const (
	inboxBodyMax        = 8192
	inboxRedeliverWait  = time.Minute
	inboxPiggybackMax   = 3
	inboxPiggybackSize  = 8192
	inboxUnacknowledged = 10 * time.Minute
)

type inboxMessage struct {
	id, toKind, toID, fromCallsign, fromSession, kind string
	fromOrchestrator                                  bool
	body                                              any // 객체가 아닐 수 있다 (문자열 · 배열 메시지)
	refTask, state, deliveredVia, ackBySession        string
	deliveredAt, lastDeliveredAt, createdAt           sql.NullString
	deliveryCount                                     int
}

func scanInboxMessage(row interface{ Scan(...any) error }) (inboxMessage, error) {
	var m inboxMessage
	var orchestrator int
	var body string
	err := row.Scan(&m.id, &m.toKind, &m.toID, &m.fromCallsign, &m.fromSession, &orchestrator, &m.kind, &body,
		&m.refTask, &m.state, &m.deliveredVia, &m.deliveredAt, &m.lastDeliveredAt, &m.deliveryCount, &m.ackBySession, &m.createdAt)
	if err != nil {
		return m, err
	}
	m.fromOrchestrator = orchestrator != 0
	if err := json.Unmarshal([]byte(body), &m.body); err != nil {
		return m, err
	}
	return m, nil
}

const inboxSelect = `SELECT id,to_kind,to_id,from_callsign,from_session,from_orchestrator,kind,body_json,ref_task,state,
	delivered_via,delivered_at,last_delivered_at,delivery_count,ack_by_session,created_at FROM inbox_message`

func inboxView(m inboxMessage) map[string]any {
	from := map[string]any{"callsign": m.fromCallsign, "orchestrator": m.fromOrchestrator}
	if m.fromSession != "" {
		from["session"] = m.fromSession
	} else {
		from["session"] = nil
	}
	out := map[string]any{"id": m.id, "kind": m.kind, "from": from, "body": m.body, "ack_with": "hub_inbox_ack"}
	if m.refTask != "" {
		out["task_id"] = m.refTask
	}
	if m.deliveryCount > 0 {
		out["redelivery"] = true
	}
	return out
}

// EnqueueMessage adds an inbox item inside the caller's transaction.
func (s *Store) EnqueueMessage(tx *sql.Tx, ctx Ctx, projectID, toKind, toID, kind string, body map[string]any,
	fromCallsign, fromSession string, fromOrchestrator bool, refTask string) (string, error) {
	if (toKind != "session" && toKind != "callsign") || (kind != "assignment" && kind != "note" && kind != "release" && kind != "report" && kind != "approval") {
		return "", InvalidField("to/kind", "모르는 주소 종류 · 메시지 종류")
	}
	if err := ScanSecrets(body, "body"); err != nil {
		return "", err
	}
	bodyJSON, err := json.Marshal(body)
	if err != nil {
		return "", err
	}
	if len(bodyJSON) > inboxBodyMax {
		return "", &HubError{Status: 413, Code: "payload_too_large", Message: fmt.Sprintf("메시지 본문 상한 %d 바이트", inboxBodyMax), Detail: map[string]any{"limit": inboxBodyMax}}
	}
	var random [6]byte
	if _, err := rand.Read(random[:]); err != nil {
		return "", err
	}
	id := "MSG-" + ctx.Now.Format("20060102") + "-" + hex.EncodeToString(random[:])
	_, err = tx.Exec(`INSERT INTO inbox_message (project_id,id,to_kind,to_id,from_callsign,from_session,from_orchestrator,kind,
		body_json,ref_task,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)`, projectID, id, toKind, toID, fromCallsign,
		fromSession, boolInt(fromOrchestrator), kind, string(bodyJSON), refTask, db.FormatISO(ctx.Now))
	if err != nil {
		return "", err
	}
	if err := s.RecordEvent(tx, ctx, &projectID, "inbox_message", id, "enqueue", nil,
		map[string]any{"to": toKind + ":" + toID, "kind": kind}, &fromCallsign); err != nil {
		return "", err
	}
	return id, nil
}

func (s *Store) returnOfferedAssignment(tx *sql.Tx, ctx Ctx, projectID, taskID, reason string) error {
	var sessionID, state string
	err := tx.QueryRow("SELECT session_id,state FROM assignment WHERE project_id=? AND task_id=? AND state IN ('offered','accepted')", projectID, taskID).Scan(&sessionID, &state)
	if errors.Is(err, sql.ErrNoRows) {
		return nil
	}
	if err != nil {
		return err
	}
	if _, err := tx.Exec("UPDATE assignment SET state='returned',return_reason=?,version=version+1 WHERE project_id=? AND task_id=? AND state IN ('offered','accepted')", reason, projectID, taskID); err != nil {
		return err
	}
	if err := s.RecordEvent(tx, ctx, &projectID, "assignment", taskID, "return", map[string]any{"state": state}, map[string]any{"state": "returned", "reason": reason}, nil); err != nil {
		return err
	}
	toKind, toID := "callsign", ""
	err = tx.QueryRow("SELECT session_id FROM orchestrator_lease WHERE project_id=? AND expires_at>?", projectID, db.FormatISO(ctx.Now)).Scan(&toID)
	if err == nil {
		toKind = "session"
	} else if errors.Is(err, sql.ErrNoRows) {
		if err := tx.QueryRow("SELECT owner_callsign FROM project WHERE id=?", projectID).Scan(&toID); err != nil {
			return err
		}
	} else {
		return err
	}
	_, err = s.EnqueueMessage(tx, ctx, projectID, toKind, toID, "note", map[string]any{"event": "assignment_returned", "task_id": taskID, "session": sessionID, "reason": reason}, "hub", "", false, taskID)
	return err
}

func (s *Store) expireInbox(tx *sql.Tx, ctx Ctx, projectID string) error {
	if err := s.expireSessions(tx, ctx, projectID); err != nil {
		return err
	}
	rows, err := tx.Query("SELECT id FROM inbox_message WHERE project_id=? AND state='delivered' AND delivered_at<=?", projectID, db.FormatISO(ctx.Now.Add(-inboxUnacknowledged)))
	if err != nil {
		return err
	}
	ids := []string{}
	for rows.Next() {
		var id string
		if err := rows.Scan(&id); err != nil {
			_ = rows.Close()
			return err
		}
		ids = append(ids, id)
	}
	if err := rows.Err(); err != nil {
		_ = rows.Close()
		return err
	}
	if err := rows.Close(); err != nil {
		return err
	}
	for _, id := range ids {
		if _, err := tx.Exec("UPDATE inbox_message SET state='unacknowledged',version=version+1 WHERE project_id=? AND id=?", projectID, id); err != nil {
			return err
		}
		if err := s.RecordEvent(tx, ctx, &projectID, "inbox_message", id, "unacknowledged", nil, nil, nil); err != nil {
			return err
		}
		var taskID string
		err := tx.QueryRow("SELECT task_id FROM assignment WHERE project_id=? AND message_id=? AND state='offered'", projectID, id).Scan(&taskID)
		if err == nil {
			if err := s.returnOfferedAssignment(tx, ctx, projectID, taskID, "unacknowledged"); err != nil {
				return err
			}
		} else if !errors.Is(err, sql.ErrNoRows) {
			return err
		}
	}
	return nil
}

func boolInt(v bool) int {
	if v {
		return 1
	}
	return 0
}

func (s *Store) InboxList(ctx Ctx, sessionID, state string) (map[string]any, error) {
	p, err := NeedCallsign(ctx)
	if err != nil {
		return nil, err
	}
	if sessionID != "" {
		if err := s.withSessionCheck(p, sessionID); err != nil {
			return nil, err
		}
	}
	query := inboxSelect + ` WHERE project_id=? AND ((to_kind='callsign' AND to_id=?)`
	args := []any{p.ProjectID, p.Callsign}
	if sessionID != "" {
		query += ` OR (to_kind='session' AND to_id=?)`
		args = append(args, sessionID)
	}
	query += ")"
	if state != "" {
		query += " AND state=?"
		args = append(args, state)
	}
	query += " ORDER BY created_at,rowid"
	rows, err := s.pool.Query(query, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	messages := []map[string]any{}
	for rows.Next() {
		m, err := scanInboxMessage(rows)
		if err != nil {
			return nil, err
		}
		v := inboxView(m)
		v["state"] = m.state
		if m.deliveredVia != "" {
			v["delivered_via"] = m.deliveredVia
		} else {
			v["delivered_via"] = nil
		}
		messages = append(messages, v)
	}
	if err := rows.Err(); err != nil {
		return nil, err
	}
	return map[string]any{"messages": messages}, nil
}

func (s *Store) withSessionCheck(p *Principal, sessionID string) error {
	if !sessionIDPattern.MatchString(sessionID) {
		return InvalidField("session", "S-YYYYMMDD-xxxxxxxx 꼴이어야 해요")
	}
	var owner, status string
	err := s.pool.QueryRow("SELECT callsign,status FROM session WHERE project_id=? AND id=?", p.ProjectID, sessionID).Scan(&owner, &status)
	if errors.Is(err, sql.ErrNoRows) {
		return NotFound("세션이 없어요: " + sessionID)
	}
	if err != nil {
		return err
	}
	if owner != p.Callsign {
		return &HubError{Status: 403, Code: "session_not_yours", Message: "이 콜사인의 세션이 아니에요", Detail: map[string]any{"session": sessionID}}
	}
	if status == "ended" {
		return &HubError{Status: 410, Code: "session_ended", Message: "끝난 세션이에요 — 세션 시작으로 새 세션을 열어요", Detail: map[string]any{"session": sessionID}}
	}
	return nil
}

// InboxAck marks a message seen, accepted, or declined. Assignment acceptance and task claim share a transaction.
func (s *Store) InboxAck(ctx Ctx, sessionID, messageID, decision, reason, requestID string) (map[string]any, error) {
	p, err := NeedCallsign(ctx)
	if err != nil {
		return nil, err
	}
	target := map[string]string{"accept": "acked", "seen": "acked", "decline": "declined"}[decision]
	if target == "" {
		return nil, InvalidField("decision", "accept · decline · seen 중 하나")
	}
	if !messageIDPattern.MatchString(messageID) {
		return nil, InvalidField("message_id", "MSG-YYYYMMDD-xxxxxxxxxxxx 꼴이어야 해요")
	}
	if err := ScanSecrets(reason, "reason"); err != nil {
		return nil, err
	}
	return s.Idempotent(ctx, requestID, func(tx *sql.Tx) (map[string]any, error) {
		if err := s.checkOwnSession(tx, p, sessionID); err != nil {
			return nil, err
		}
		m, err := scanInboxMessage(tx.QueryRow(inboxSelect+" WHERE project_id=? AND id=?", p.ProjectID, messageID))
		if errors.Is(err, sql.ErrNoRows) {
			return nil, NotFound("메시지가 없어요: " + messageID)
		}
		if err != nil {
			return nil, err
		}
		mine := (m.toKind == "session" && m.toID == sessionID) || (m.toKind == "callsign" && m.toID == p.Callsign)
		tidy := m.state == "unacknowledged" && decision == "seen"
		if !mine && tidy && m.toKind == "session" {
			// 받은 세션이 끝났으면 같은 콜사인의 다른 세션이 정리한다.
			var n int
			if err := tx.QueryRow("SELECT COUNT(*) FROM session WHERE project_id=? AND id=? AND callsign=? AND status='ended'", p.ProjectID, m.toID, p.Callsign).Scan(&n); err != nil {
				return nil, err
			}
			mine = n > 0
		}
		if !mine {
			return nil, &HubError{Status: 403, Code: "message_not_yours", Message: "이 세션 · 콜사인 앞 메시지가 아니에요"}
		}
		if doc, ok := m.body.(map[string]any); ok && m.kind == "approval" && doc["request_type"] == "agent_confirmation" {
			return nil, &HubError{Status: 403, Code: "human_decision_required", Message: "사람이 웹 허브 확인 요청 메뉴에서 결정해야 해요"}
		}
		if m.state == "acked" || m.state == "declined" {
			if m.state == target && m.ackBySession == sessionID {
				return map[string]any{"message_id": messageID, "state": m.state, "unchanged": true}, nil
			}
			return nil, &HubError{Status: 409, Code: "already_acked", Message: "이미 확인한 메시지예요", Detail: map[string]any{"state": m.state, "by_session": m.ackBySession}}
		}
		if (m.state == "unacknowledged" || m.state == "expired") && !tidy {
			return nil, &HubError{Status: 409, Code: "ack_too_late", Message: "확인 상한(10분)이 지난 메시지예요 — 수락 · 거절은 못 하고 decision=seen 으로 정리만 해요", Detail: map[string]any{"state": m.state}}
		}
		if m.kind == "assignment" && (decision == "accept" || decision == "decline") {
			var taskID, assignmentSession, assignmentState string
			err := tx.QueryRow("SELECT task_id,session_id,state FROM assignment WHERE project_id=? AND message_id=?", p.ProjectID, messageID).Scan(&taskID, &assignmentSession, &assignmentState)
			if errors.Is(err, sql.ErrNoRows) {
				return nil, &HubError{Status: 409, Code: "assignment_not_open", Message: "열린 배정이 아니에요", Detail: map[string]any{"message_id": messageID}}
			}
			if err != nil {
				return nil, err
			}
			if assignmentSession != sessionID || assignmentState != "offered" {
				return nil, &HubError{Status: 409, Code: "assignment_not_open", Message: "이 세션 앞의 열린 배정이 아니에요 (회수 · 되돌림 · 다른 세션)", Detail: map[string]any{"message_id": messageID}}
			}
			if decision == "accept" {
				if _, err := s.versionedUpdateIn(tx, ctx, p, taskID, nil, "claim", func(before map[string]any, principal *Principal, _ *sql.Tx) (map[string]any, error) {
					return ClaimMutate(before, principal)
				}); err != nil {
					return nil, err
				}
				if _, err := tx.Exec("UPDATE assignment SET state='accepted',accepted_at=?,version=version+1 WHERE project_id=? AND task_id=? AND state='offered'", db.FormatISO(ctx.Now), p.ProjectID, taskID); err != nil {
					return nil, err
				}
				if err := s.RecordEvent(tx, ctx, &p.ProjectID, "assignment", taskID, "accept", map[string]any{"state": "offered"}, map[string]any{"state": "accepted"}, nil); err != nil {
					return nil, err
				}
			} else {
				if err := s.returnOfferedAssignment(tx, ctx, p.ProjectID, taskID, "declined: "+reason); err != nil {
					return nil, err
				}
			}
		}
		if _, err := tx.Exec("UPDATE inbox_message SET state=?,acked_at=?,ack_by_session=?,ack_reason=?,version=version+1 WHERE project_id=? AND id=?", target, db.FormatISO(ctx.Now), sessionID, reason, p.ProjectID, messageID); err != nil {
			return nil, err
		}
		if _, err := tx.Exec("UPDATE session SET last_signal_at=?,idle_waits=0 WHERE project_id=? AND id=?", db.FormatISO(ctx.Now), p.ProjectID, sessionID); err != nil {
			return nil, err
		}
		if err := s.RecordEvent(tx, ctx, &p.ProjectID, "inbox_message", messageID, "ack:"+decision, map[string]any{"state": m.state}, map[string]any{"state": target, "reason": reason}, nil); err != nil {
			return nil, err
		}
		return map[string]any{"message_id": messageID, "state": target}, nil
	})
}

// CloseMessage lets the owner tidy an unacknowledged message; assignments and approvals keep their state.
func (s *Store) CloseMessage(ctx Ctx, messageID string) (map[string]any, error) {
	p, err := needOwner(ctx)
	if err != nil {
		return nil, err
	}
	return s.withWriteTx(func(tx *sql.Tx) (map[string]any, error) {
		var kind, state, raw string
		err := tx.QueryRow("SELECT kind,state,body_json FROM inbox_message WHERE project_id=? AND id=?", p.ProjectID, messageID).Scan(&kind, &state, &raw)
		if errors.Is(err, sql.ErrNoRows) {
			return nil, NotFound("메시지가 없어요: " + messageID)
		}
		if err != nil {
			return nil, err
		}
		var body any // 본문은 객체가 아닐 수 있다 (옛 문자열 메시지)
		if err := json.Unmarshal([]byte(raw), &body); err != nil {
			return nil, err
		}
		if doc, ok := body.(map[string]any); ok && kind == "approval" && doc["request_type"] == "agent_confirmation" {
			return nil, &HubError{Status: 403, Code: "human_decision_required", Message: "사람이 웹 허브의 확인 요청 메뉴에서 결정해야 해요"}
		}
		if state != "unacknowledged" {
			return nil, &HubError{Status: 409, Code: "not_unacknowledged", Message: "미확인 상태의 메시지만 정리해요", Detail: map[string]any{"state": state}}
		}
		if _, err := tx.Exec("UPDATE inbox_message SET state='acked',acked_at=?,ack_by_session=?,ack_reason=?,version=version+1 WHERE project_id=? AND id=?", db.FormatISO(ctx.Now), "web:"+p.Callsign, "소유자 정리", p.ProjectID, messageID); err != nil {
			return nil, err
		}
		if err := s.RecordEvent(tx, ctx, &p.ProjectID, "inbox_message", messageID, "close", map[string]any{"state": state}, map[string]any{"state": "acked"}, nil); err != nil {
			return nil, err
		}
		return map[string]any{"message_id": messageID, "state": "acked"}, nil
	})
}

// InboxTake marks queued or due-for-redelivery messages delivered without consuming them.
func (s *Store) InboxTake(ctx Ctx, sessionID, via string) (map[string]any, error) {
	p, err := NeedCallsign(ctx)
	if err != nil {
		return nil, err
	}
	if sessionID != "" {
		if err := s.withSessionCheck(p, sessionID); err != nil {
			return nil, err
		}
	}
	return s.withWriteTx(func(tx *sql.Tx) (map[string]any, error) {
		if err := s.expireInbox(tx, ctx, p.ProjectID); err != nil {
			return nil, err
		}
		targets := []string{"(to_kind='callsign' AND to_id=?)"}
		args := []any{p.ProjectID, p.Callsign}
		if sessionID != "" {
			targets = append(targets, "(to_kind='session' AND to_id=?)")
			args = append(args, sessionID)
		}
		var halted int
		_ = tx.QueryRow("SELECT halted FROM orchestrator_lease WHERE project_id=?", p.ProjectID).Scan(&halted)
		query := inboxSelect + " WHERE project_id=? AND (" + joinOr(targets) + ") AND (state='queued' OR (state='delivered' AND last_delivered_at<=?))"
		args = append(args, db.FormatISO(ctx.Now.Add(-inboxRedeliverWait)))
		if halted != 0 {
			query += " AND kind='release'"
		}
		query += " ORDER BY created_at,rowid"
		rows, err := tx.Query(query, args...)
		if err != nil {
			return nil, err
		}
		defer rows.Close()
		picked := []map[string]any{}
		pickedIDs := []string{}
		size := 0
		remaining := 0
		for rows.Next() {
			m, err := scanInboxMessage(rows)
			if err != nil {
				return nil, err
			}
			v := inboxView(m)
			encoded, err := json.Marshal(v)
			if err != nil {
				return nil, err
			}
			if len(picked) >= inboxPiggybackMax || (len(picked) > 0 && size+len(encoded) > inboxPiggybackSize) {
				remaining++
				continue
			}
			picked = append(picked, v)
			pickedIDs = append(pickedIDs, m.id)
			size += len(encoded)
		}
		if err := rows.Err(); err != nil {
			return nil, err
		}
		if err := rows.Close(); err != nil {
			return nil, err
		}
		for _, id := range pickedIDs {
			if _, err := tx.Exec("UPDATE inbox_message SET state='delivered',delivered_via=?,delivered_at=COALESCE(delivered_at,?),last_delivered_at=?,delivery_count=delivery_count+1,version=version+1 WHERE project_id=? AND id=?", via, db.FormatISO(ctx.Now), db.FormatISO(ctx.Now), p.ProjectID, id); err != nil {
				return nil, err
			}
		}
		return map[string]any{"messages": picked, "remaining": remaining}, nil
	})
}

// Wait polls the worker inbox once; HTTP/MCP adapters can repeat this until the caller's timeout.
func (s *Store) Wait(ctx Ctx, sessionID string) (map[string]any, error) {
	got, err := s.WaitPoll(ctx, sessionID, true)
	if err != nil {
		return nil, err
	}
	if got != nil {
		return got, nil
	}
	return s.WaitTimeout(ctx, sessionID, 0)
}

func (s *Store) WaitPoll(ctx Ctx, sessionID string, first bool) (map[string]any, error) {
	p, err := NeedCallsign(ctx)
	if err != nil {
		return nil, err
	}
	if err := s.withSessionCheck(p, sessionID); err != nil {
		return nil, err
	}
	var allowWait, idleWaits, reviewIdeas int
	err = s.pool.QueryRow("SELECT allow_wait,idle_waits,review_ideas FROM session WHERE project_id=? AND id=? AND callsign=? AND status='active'", p.ProjectID, sessionID, p.Callsign).Scan(&allowWait, &idleWaits, &reviewIdeas)
	if errors.Is(err, sql.ErrNoRows) {
		return nil, &HubError{Status: 404, Code: "not_found", Message: "세션이 없어요: " + sessionID}
	}
	if err != nil {
		return nil, err
	}
	if allowWait == 0 {
		return nil, &HubError{Status: 409, Code: "wait_disabled", Message: "이 세션은 대기 도구가 꺼져 있어요 — 사람이 보는 세션은 편승(M1)만 써요 (Q1). 일하는 세션은 kind=worker 로 시작해요", Detail: map[string]any{"session": sessionID}}
	}
	if first && idleWaits >= 70 {
		return nil, &HubError{Status: 409, Code: "wait_budget", Message: "일 없이 70번 연속 기다렸어요 — 턴을 끝내요", Detail: map[string]any{"session": sessionID, "idle_waits": idleWaits}}
	}
	if _, err := s.pool.Exec("UPDATE session SET waiting_since=COALESCE(waiting_since,?),last_signal_at=? WHERE project_id=? AND id=?", db.FormatISO(ctx.Now), db.FormatISO(ctx.Now), p.ProjectID, sessionID); err != nil {
		return nil, err
	}
	inbox, err := s.InboxTake(ctx, sessionID, "wait")
	if err != nil {
		return nil, err
	}
	messages, _ := inbox["messages"].([]map[string]any)
	if len(messages) == 0 && reviewIdeas != 0 {
		// 검토 전용 세션 (I3) — 배정이 없을 때 검토 대기 아이디어 하나를 일감으로 준다. 집기(claim)는 세션이 한다.
		if messages, err = s.IdeaReviewWork(ctx); err != nil {
			return nil, err
		}
	}
	if len(messages) > 0 {
		if _, err := s.pool.Exec("UPDATE session SET waiting_since=NULL,idle_waits=0 WHERE project_id=? AND id=?", p.ProjectID, sessionID); err != nil {
			return nil, err
		}
		return map[string]any{"work": messages, "remaining": inbox["remaining"], "call_again": false}, nil
	}
	return nil, nil
}

func (s *Store) WaitTimeout(ctx Ctx, sessionID string, waitedS int) (map[string]any, error) {
	p, err := NeedCallsign(ctx)
	if err != nil {
		return nil, err
	}
	if _, err := s.pool.Exec("UPDATE session SET waiting_since=NULL,idle_waits=idle_waits+1,last_signal_at=? WHERE project_id=? AND id=?", db.FormatISO(ctx.Now), p.ProjectID, sessionID); err != nil {
		return nil, err
	}
	return map[string]any{"work": []map[string]any{}, "call_again": true, "waited_s": waitedS, "note": "일이 아직 없다 — hub_wait 를 다시 부른다 (release 를 받으면 턴을 끝낸다)"}, nil
}

func (s *Store) WaitClear(ctx Ctx, sessionID string) error {
	p, err := NeedCallsign(ctx)
	if err != nil {
		return err
	}
	_, err = s.pool.Exec("UPDATE session SET waiting_since=NULL WHERE project_id=? AND id=?", p.ProjectID, sessionID)
	return err
}

// Report closes an accepted assignment as reported and sends its result to the current orchestrator.
func (s *Store) Report(ctx Ctx, sessionID, taskID, summary, verification, requestID string) (map[string]any, error) {
	p, err := NeedCallsign(ctx)
	if err != nil {
		return nil, err
	}
	if strings.TrimSpace(summary) == "" {
		return nil, InvalidField("summary", "비었어요")
	}
	if err := ScanSecrets(map[string]any{"summary": summary, "verification": verification}, ""); err != nil {
		return nil, err
	}
	return s.Idempotent(ctx, requestID, func(tx *sql.Tx) (map[string]any, error) {
		if err := s.checkOwnSession(tx, p, sessionID); err != nil {
			return nil, err
		}
		var state string
		err := tx.QueryRow("SELECT state FROM assignment WHERE project_id=? AND task_id=? AND session_id=?", p.ProjectID, taskID, sessionID).Scan(&state)
		if errors.Is(err, sql.ErrNoRows) {
			return nil, &HubError{Status: 409, Code: "assignment_not_accepted", Message: "이 세션이 수락한 배정이 아니에요 — 먼저 hub_inbox_ack(accept)", Detail: map[string]any{"task_id": taskID}}
		}
		if err != nil {
			return nil, err
		}
		if state != "accepted" {
			return nil, &HubError{Status: 409, Code: "assignment_not_accepted", Message: "이 세션이 수락한 배정이 아니에요 — 먼저 hub_inbox_ack(accept)", Detail: map[string]any{"task_id": taskID}}
		}
		report := map[string]any{"summary": summary, "verification": verification}
		reportJSON, err := json.Marshal(report)
		if err != nil {
			return nil, err
		}
		if _, err := tx.Exec("UPDATE assignment SET state='reported',reported_at=?,report_json=?,version=version+1 WHERE project_id=? AND task_id=? AND state='accepted'", db.FormatISO(ctx.Now), string(reportJSON), p.ProjectID, taskID); err != nil {
			return nil, err
		}
		if err := s.RecordEvent(tx, ctx, &p.ProjectID, "assignment", taskID, "report", map[string]any{"state": "accepted"}, map[string]any{"state": "reported"}, nil); err != nil {
			return nil, err
		}
		toKind, toID := "callsign", ""
		err = tx.QueryRow("SELECT session_id FROM orchestrator_lease WHERE project_id=? AND expires_at>?", p.ProjectID, db.FormatISO(ctx.Now)).Scan(&toID)
		if err == nil {
			toKind = "session"
		} else if errors.Is(err, sql.ErrNoRows) {
			if err := tx.QueryRow("SELECT owner_callsign FROM project WHERE id=?", p.ProjectID).Scan(&toID); err != nil {
				return nil, err
			}
		} else {
			return nil, err
		}
		body := map[string]any{"task_id": taskID, "session": sessionID, "summary": summary, "verification": verification, "note": "done 은 hub_task_close 의 done 게이트가 판정한다 — 보고가 done 이 아니다"}
		if _, err := s.EnqueueMessage(tx, ctx, p.ProjectID, toKind, toID, "report", body, p.Callsign, sessionID, false, taskID); err != nil {
			return nil, err
		}
		return map[string]any{"task_id": taskID, "state": "reported"}, nil
	})
}

func joinOr(parts []string) string {
	if len(parts) == 0 {
		return ""
	}
	result := parts[0]
	for _, part := range parts[1:] {
		result += " OR " + part
	}
	return result
}
