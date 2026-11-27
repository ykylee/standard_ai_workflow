package store

import (
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"regexp"
	"strings"
	"time"

	"github.com/ykylee/standard_ai_workflow/hub-go/internal/db"
)

const orchestratorLeaseTTL = 15 * time.Minute

var orchestratorSessionID = regexp.MustCompile(`^S-\d{8}-[0-9a-f]{8}$`)

func needOwner(ctx Ctx) (*Principal, error) {
	p, err := NeedCallsign(ctx)
	if err != nil {
		return nil, err
	}
	if p.Role != "owner" || p.CallsignKind != "human" || !p.HumanApproved {
		return nil, Forbidden("승인된 human 소유자(owner)만 — 오케스트레이터 지정 · 인계 · 정지는 사람이 해요 (요구 R19.1)")
	}
	return p, nil
}

func (s *Store) activeSession(tx *sql.Tx, projectID string, raw any) (map[string]any, error) {
	id, ok := raw.(string)
	if !ok || !orchestratorSessionID.MatchString(id) {
		return nil, InvalidField("session", "S-YYYYMMDD-xxxxxxxx 꼴이어야 해요")
	}
	var callsign, delivery, status string
	err := tx.QueryRow(`SELECT callsign,delivery_json,status FROM session WHERE project_id=? AND id=?`, projectID, id).Scan(&callsign, &delivery, &status)
	if errors.Is(err, sql.ErrNoRows) {
		return nil, NotFound("세션이 없어요: " + id)
	}
	if err != nil {
		return nil, err
	}
	if status == "ended" {
		return nil, &HubError{Status: 410, Code: "session_ended", Message: "끝난 세션이에요", Detail: map[string]any{"session": id}}
	}
	return map[string]any{"id": id, "callsign": callsign, "delivery_json": delivery, "status": status}, nil
}

func (s *Store) orchestratorLease(tx *sql.Tx, ctx Ctx, projectID string) (map[string]any, error) {
	var sessionID, callsign, expires string
	var halted int
	err := tx.QueryRow("SELECT session_id,callsign,expires_at,halted FROM orchestrator_lease WHERE project_id=?", projectID).Scan(&sessionID, &callsign, &expires, &halted)
	if errors.Is(err, sql.ErrNoRows) {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	if expires > db.FormatISO(ctx.Now) {
		return map[string]any{"session_id": sessionID, "callsign": callsign, "expires_at": expires, "halted": halted != 0}, nil
	}
	if _, err := tx.Exec("DELETE FROM orchestrator_lease WHERE project_id=?", projectID); err != nil {
		return nil, err
	}
	if err := s.RecordEvent(tx, ctx, &projectID, "orchestrator_lease", sessionID, "expire", map[string]any{"session": sessionID, "expires_at": expires}, nil, nil); err != nil {
		return nil, err
	}
	var owner string
	if err := tx.QueryRow("SELECT owner_callsign FROM project WHERE id=?", projectID).Scan(&owner); err != nil {
		return nil, err
	}
	_, err = s.EnqueueMessage(tx, ctx, projectID, "callsign", owner, "note", map[string]any{"event": "orchestrator_lease_expired", "session": sessionID, "text": "오케스트레이터 lease 가 만료됐다 — 작업 세션의 배정은 그대로다. 다시 지정하려면 hub_orch_declare"}, "hub", "", false, "")
	return nil, err
}

func (s *Store) orchestratorAddress(tx *sql.Tx, ctx Ctx, pid string) (string, string, error) {
	l, err := s.orchestratorLease(tx, ctx, pid)
	if err != nil {
		return "", "", err
	}
	if l != nil {
		return "session", l["session_id"].(string), nil
	}
	var owner string
	err = tx.QueryRow("SELECT owner_callsign FROM project WHERE id=?", pid).Scan(&owner)
	return "callsign", owner, err
}

func (s *Store) needOrchestrator(tx *sql.Tx, ctx Ctx, session any) (*Principal, map[string]any, error) {
	p, err := NeedCallsign(ctx)
	if err != nil {
		return nil, nil, err
	}
	l, err := s.orchestratorLease(tx, ctx, p.ProjectID)
	if err != nil {
		return nil, nil, err
	}
	sid, ok := session.(string)
	if l == nil || !ok || l["session_id"] != sid || l["callsign"] != p.Callsign {
		return nil, nil, &HubError{Status: 403, Code: "not_orchestrator", Message: "지정된 오케스트레이터 세션만 — session 인자에 그 세션 ID 를 실어요"}
	}
	return p, l, nil
}

func (s *Store) OrchDeclare(ctx Ctx, session string) (map[string]any, error) {
	p, err := needOwner(ctx)
	if err != nil {
		return nil, err
	}
	return s.withWriteTx(func(tx *sql.Tx) (map[string]any, error) {
		target, err := s.activeSession(tx, p.ProjectID, session)
		if err != nil {
			return nil, err
		}
		lease, err := s.orchestratorLease(tx, ctx, p.ProjectID)
		if err != nil {
			return nil, err
		}
		if lease != nil {
			return nil, &HubError{Status: 409, Code: "orchestrator_exists", Message: "오케스트레이터가 이미 있어요 — 바꾸려면 hub_orch_transfer"}
		}
		expires := db.FormatISO(ctx.Now.Add(orchestratorLeaseTTL))
		sid := target["id"].(string)
		call := target["callsign"].(string)
		if _, err := tx.Exec("INSERT INTO orchestrator_lease(project_id,session_id,callsign,declared_by,declared_at,expires_at) VALUES(?,?,?,?,?,?)", p.ProjectID, sid, call, p.Callsign, db.FormatISO(ctx.Now), expires); err != nil {
			return nil, err
		}
		if err := s.RecordEvent(tx, ctx, &p.ProjectID, "orchestrator_lease", sid, "declare", nil, map[string]any{"session": sid, "callsign": call}, nil); err != nil {
			return nil, err
		}
		if _, err := s.EnqueueMessage(tx, ctx, p.ProjectID, "session", sid, "note", map[string]any{"event": "orchestrator_declared", "text": "이 세션이 프로젝트 오케스트레이터로 지정됐다 — hub_session_list 로 세션을 보고 hub_orch_assign 으로 배정한다"}, p.Callsign, "", false, ""); err != nil {
			return nil, err
		}
		return map[string]any{"orchestrator": map[string]any{"session": sid, "callsign": call, "expires_at": expires}}, nil
	})
}

func (s *Store) OrchTransfer(ctx Ctx, session string) (map[string]any, error) {
	p, err := needOwner(ctx)
	if err != nil {
		return nil, err
	}
	return s.withWriteTx(func(tx *sql.Tx) (map[string]any, error) {
		target, err := s.activeSession(tx, p.ProjectID, session)
		if err != nil {
			return nil, err
		}
		old, err := s.orchestratorLease(tx, ctx, p.ProjectID)
		if err != nil {
			return nil, err
		}
		if old == nil {
			return nil, &HubError{Status: 409, Code: "no_orchestrator", Message: "지금 오케스트레이터가 없어요 — hub_orch_declare 로 지정해요"}
		}
		sid := target["id"].(string)
		call := target["callsign"].(string)
		expiry := db.FormatISO(ctx.Now.Add(orchestratorLeaseTTL))
		if _, err := tx.Exec("UPDATE orchestrator_lease SET session_id=?,callsign=?,expires_at=?,version=version+1 WHERE project_id=?", sid, call, expiry, p.ProjectID); err != nil {
			return nil, err
		}
		if err := s.RecordEvent(tx, ctx, &p.ProjectID, "orchestrator_lease", sid, "transfer", map[string]any{"session": old["session_id"]}, map[string]any{"session": sid}, nil); err != nil {
			return nil, err
		}
		var n int
		if err := tx.QueryRow("SELECT COUNT(*) FROM assignment WHERE project_id=? AND state IN ('offered','accepted')", p.ProjectID).Scan(&n); err != nil {
			return nil, err
		}
		for _, x := range []struct{ id, msg string }{{sid, fmt.Sprintf("오케스트레이터를 넘겨받았다 — 열린 배정 %d건", n)}, {old["session_id"].(string), "오케스트레이터가 다른 세션으로 넘어갔다 — 배정 · 메시지를 더 보내지 않는다"}} {
			if _, err := s.EnqueueMessage(tx, ctx, p.ProjectID, "session", x.id, "note", map[string]any{"event": "orchestrator_transfer", "text": x.msg}, p.Callsign, "", false, ""); err != nil {
				return nil, err
			}
		}
		return map[string]any{"orchestrator": map[string]any{"session": sid, "callsign": call}, "open_assignments": n}, nil
	})
}

func (s *Store) OrchRelease(ctx Ctx, session string) (map[string]any, error) {
	p, err := NeedCallsign(ctx)
	if err != nil {
		return nil, err
	}
	return s.withWriteTx(func(tx *sql.Tx) (map[string]any, error) {
		l, err := s.orchestratorLease(tx, ctx, p.ProjectID)
		if err != nil {
			return nil, err
		}
		if l == nil {
			return map[string]any{"released": false, "note": "오케스트레이터가 없다"}, nil
		}
		owner := p.Role == "owner" && p.CallsignKind == "human" && p.HumanApproved
		if !owner && session != l["session_id"] {
			return nil, Forbidden("owner 나 오케스트레이터 세션 자신만 lease 를 풀어요")
		}
		if _, err := tx.Exec("DELETE FROM orchestrator_lease WHERE project_id=?", p.ProjectID); err != nil {
			return nil, err
		}
		if err := s.RecordEvent(tx, ctx, &p.ProjectID, "orchestrator_lease", l["session_id"].(string), "release", map[string]any{"session": l["session_id"]}, nil, nil); err != nil {
			return nil, err
		}
		return map[string]any{"released": true}, nil
	})
}

func (s *Store) OrchHalt(ctx Ctx, on bool) (map[string]any, error) {
	p, err := needOwner(ctx)
	if err != nil {
		return nil, err
	}
	return s.withWriteTx(func(tx *sql.Tx) (map[string]any, error) {
		l, err := s.orchestratorLease(tx, ctx, p.ProjectID)
		if err != nil {
			return nil, err
		}
		if l == nil {
			return nil, &HubError{Status: 409, Code: "no_orchestrator", Message: "지금 오케스트레이터가 없어요 — 멈출 것이 없어요"}
		}
		if _, err := tx.Exec("UPDATE orchestrator_lease SET halted=?,version=version+1 WHERE project_id=?", boolInt(on), p.ProjectID); err != nil {
			return nil, err
		}
		op := "resume"
		if on {
			op = "halt"
		}
		if err := s.RecordEvent(tx, ctx, &p.ProjectID, "orchestrator_lease", p.ProjectID, op, nil, map[string]any{"halted": on}, nil); err != nil {
			return nil, err
		}
		woke := []string{}
		if on {
			rows, err := tx.Query("SELECT id FROM session WHERE project_id=? AND waiting_since IS NOT NULL AND status='active'", p.ProjectID)
			if err != nil {
				return nil, err
			}
			for rows.Next() {
				var id string
				if err := rows.Scan(&id); err != nil {
					rows.Close()
					return nil, err
				}
				woke = append(woke, id)
			}
			if err := rows.Close(); err != nil {
				return nil, err
			}
			for _, id := range woke {
				if _, err := s.EnqueueMessage(tx, ctx, p.ProjectID, "session", id, "release", map[string]any{"event": "halted", "text": "오케스트레이션이 정지됐다 — 지금 일을 마무리하고 턴을 끝낸다"}, p.Callsign, "", false, ""); err != nil {
					return nil, err
				}
			}
		}
		return map[string]any{"halted": on, "released_waiting": woke}, nil
	})
}

func (s *Store) OrchAssign(ctx Ctx, session, taskID, toSession, note, requestID string) (map[string]any, error) {
	if err := ScanSecrets(note, "note"); err != nil {
		return nil, err
	}
	return s.Idempotent(ctx, requestID, func(tx *sql.Tx) (map[string]any, error) {
		p, l, err := s.needOrchestrator(tx, ctx, session)
		if err != nil {
			return nil, err
		}
		if l["halted"].(bool) {
			return nil, &HubError{Status: 423, Code: "halted", Message: "오케스트레이션이 정지돼 있어요 (hub_orch_halt)"}
		}
		task, err := s.GetTask(tx, p.ProjectID, taskID)
		if err != nil {
			return nil, err
		}
		if task["status"] == "done" {
			return nil, &HubError{Status: 409, Code: "task_done", Message: "닫힌 task 는 배정할 수 없어요"}
		}
		target, err := s.activeSession(tx, p.ProjectID, toSession)
		if err != nil {
			return nil, err
		}
		if target["id"] == l["session_id"] {
			return nil, &HubError{Status: 409, Code: "self_assignment", Message: "오케스트레이터는 자기에게 배정하지 않아요 — 직접 hub_task_claim (Q3)"}
		}
		var delivery string
		if err := tx.QueryRow("SELECT delivery_json FROM session WHERE project_id=? AND id=?", p.ProjectID, toSession).Scan(&delivery); err != nil {
			return nil, err
		}
		var paths []string
		if err := json.Unmarshal([]byte(delivery), &paths); err != nil {
			return nil, err
		}
		if len(paths) == 0 {
			return nil, &HubError{Status: 409, Code: "no_delivery_path", Message: "그 세션에 전달 경로가 없어요", Detail: map[string]any{"session": toSession}}
		}
		assignee, _ := task["assignee"].(string)
		if assignee != "" && assignee != target["callsign"] {
			return nil, &HubError{Status: 409, Code: "already_claimed", Message: assignee + " 가 맡고 있어요 — 그 콜사인의 세션에만 배정해요", Detail: map[string]any{"assignee": assignee}}
		}
		var title string
		if err := tx.QueryRow("SELECT title FROM task WHERE project_id=? AND id=?", p.ProjectID, taskID).Scan(&title); err != nil {
			return nil, err
		}
		mid, err := s.EnqueueMessage(tx, ctx, p.ProjectID, "session", toSession, "assignment", map[string]any{"task_id": taskID, "title": title, "note": note, "do": "hub_inbox_ack(accept) 로 받고 수행 — 끝나면 hub_report"}, p.Callsign, session, true, taskID)
		if err != nil {
			return nil, err
		}
		if _, err := tx.Exec("INSERT INTO assignment(project_id,task_id,session_id,callsign,message_id,state,offered_at) VALUES(?,?,?,?,?,'offered',?)", p.ProjectID, taskID, toSession, target["callsign"], mid, db.FormatISO(ctx.Now)); err != nil {
			if strings.Contains(strings.ToLower(err.Error()), "unique") {
				return nil, &HubError{Status: 409, Code: "assignment_taken", Message: "이 task 에는 열린 배정이 있어요 — 회수(hub_orch_recall) 뒤 다시", Detail: map[string]any{"task_id": taskID}}
			}
			return nil, err
		}
		if err := s.RecordEvent(tx, ctx, &p.ProjectID, "assignment", taskID, "offer", nil, map[string]any{"session": toSession, "message_id": mid}, nil); err != nil {
			return nil, err
		}
		return map[string]any{"assignment": map[string]any{"task_id": taskID, "session": toSession, "state": "offered", "message_id": mid}}, nil
	})
}

func (s *Store) OrchRecall(ctx Ctx, session, taskID, reason string) (map[string]any, error) {
	return s.withWriteTx(func(tx *sql.Tx) (map[string]any, error) {
		p, _, err := s.needOrchestrator(tx, ctx, session)
		if err != nil {
			return nil, err
		}
		var sid string
		err = tx.QueryRow("SELECT session_id FROM assignment WHERE project_id=? AND task_id=? AND state IN ('offered','accepted')", p.ProjectID, taskID).Scan(&sid)
		if errors.Is(err, sql.ErrNoRows) {
			return nil, &HubError{Status: 409, Code: "assignment_not_open", Message: "열린 배정이 없어요", Detail: map[string]any{"task_id": taskID}}
		}
		if err != nil {
			return nil, err
		}
		if err := s.returnOfferedAssignment(tx, ctx, p.ProjectID, taskID, "recall: "+reason); err != nil {
			return nil, err
		}
		if _, err := s.EnqueueMessage(tx, ctx, p.ProjectID, "session", sid, "release", map[string]any{"event": "assignment_recalled", "task_id": taskID, "reason": reason, "text": "배정이 회수됐다 — 이 task 의 일을 멈춘다 (맡은 것은 hub_task_release 로 놓는다)"}, p.Callsign, session, true, taskID); err != nil {
			return nil, err
		}
		return map[string]any{"task_id": taskID, "state": "returned"}, nil
	})
}

func (s *Store) OrchMessage(ctx Ctx, session, to, kind string, body any, requestID string) (map[string]any, error) {
	if kind == "" {
		kind = "note"
	}
	if kind != "note" && kind != "release" {
		return nil, InvalidField("kind", "note · release 중 하나 (배정은 hub_orch_assign)")
	}
	var b map[string]any
	switch v := body.(type) {
	case map[string]any:
		b = v
	case string:
		b = map[string]any{"text": v}
	default:
		return nil, InvalidField("body", "문자열 또는 객체")
	}
	return s.Idempotent(ctx, requestID, func(tx *sql.Tx) (map[string]any, error) {
		p, l, err := s.needOrchestrator(tx, ctx, session)
		if err != nil {
			return nil, err
		}
		if l["halted"].(bool) && kind != "release" {
			return nil, &HubError{Status: 423, Code: "halted", Message: "오케스트레이션이 정지돼 있어요 — release 만 보낼 수 있어요"}
		}
		toKind := "callsign"
		if orchestratorSessionID.MatchString(to) {
			if _, err := s.activeSession(tx, p.ProjectID, to); err != nil {
				return nil, err
			}
			toKind = "session"
		} else {
			var n int
			err := tx.QueryRow("SELECT COUNT(*) FROM callsign WHERE project_id=? AND id=? AND revoked_at IS NULL", p.ProjectID, to).Scan(&n)
			if err != nil {
				return nil, err
			}
			if n == 0 {
				return nil, NotFound("세션 · 콜사인이 없어요: " + to)
			}
		}
		mid, err := s.EnqueueMessage(tx, ctx, p.ProjectID, toKind, to, kind, b, p.Callsign, session, true, "")
		if err != nil {
			return nil, err
		}
		return map[string]any{"message_id": mid, "to": toKind + ":" + to}, nil
	})
}
