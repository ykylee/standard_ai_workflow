package store

import (
	"database/sql"
	"encoding/json"
	"fmt"

	"github.com/ykylee/standard_ai_workflow/hub-go/internal/db"
)

func (s *Store) nextSessionRequestID(tx *sql.Tx, projectID string) (string, error) {
	var n int
	if err := tx.QueryRow("SELECT COUNT(*) FROM session_request WHERE project_id=?", projectID).Scan(&n); err != nil {
		return "", err
	}
	return fmt.Sprintf("SR-%04d", n+1), nil
}

func (s *Store) relayHost(tx *sql.Tx, projectID, hostID string) (string, string, error) {
	var name, projects, harnesses string
	err := tx.QueryRow("SELECT name,projects_json,harnesses_json FROM relay_host WHERE host_id=? AND revoked_at IS NULL", hostID).Scan(&name, &projects, &harnesses)
	if err == sql.ErrNoRows {
		return "", "", NotFound("이 프로젝트의 중계가 아니에요: " + hostID)
	}
	if err != nil {
		return "", "", err
	}
	var pids []string
	if err := json.Unmarshal([]byte(projects), &pids); err != nil {
		return "", "", err
	}
	for _, id := range pids {
		if id == projectID {
			return name, harnesses, nil
		}
	}
	return "", "", NotFound("이 프로젝트의 중계가 아니에요: " + hostID)
}

func (s *Store) relayRequestCounter(tx *sql.Tx, ctx Ctx, projectID, name string, limit int) error {
	day := ctx.Now.UTC().Format("2006-01-02")
	if _, err := tx.Exec("INSERT INTO orch_counter(project_id,day,name,n) VALUES(?,?,?,0) ON CONFLICT(project_id,day,name) DO NOTHING", projectID, day, name); err != nil {
		return err
	}
	var n int
	if err := tx.QueryRow("SELECT n FROM orch_counter WHERE project_id=? AND day=? AND name=?", projectID, day, name).Scan(&n); err != nil {
		return err
	}
	if n >= limit {
		return &HubError{Status: 429, Code: "limit_reached", Message: fmt.Sprintf("오늘 %s 상한 %d — 사람에게 알려요", name, limit), Detail: map[string]any{"limit": limit, "name": name}}
	}
	_, err := tx.Exec("UPDATE orch_counter SET n=n+1 WHERE project_id=? AND day=? AND name=?", projectID, day, name)
	return err
}

func (s *Store) approvalNote(tx *sql.Tx, ctx Ctx, projectID, requestID string, body map[string]any) error {
	var owner string
	if err := tx.QueryRow("SELECT owner_callsign FROM project WHERE id=?", projectID).Scan(&owner); err != nil {
		return err
	}
	body["decide_with"] = "hub_approval_decide"
	_, err := s.EnqueueMessage(tx, ctx, projectID, "callsign", owner, "approval", body, "hub", "", false, "")
	return err
}

func (s *Store) OrchRequestSession(ctx Ctx, session, hostID, dirAlias, harness, permissionMode, prompt, requestID string) (map[string]any, error) {
	if permissionMode == "" {
		permissionMode = "default"
	}
	if permissionMode != "default" && permissionMode != "acceptEdits" && permissionMode != "plan" {
		return nil, InvalidField("permission_mode", "default · acceptEdits · plan 중 하나 (bypass 계열은 받지 않아요)")
	}
	if err := ScanSecrets(map[string]any{"prompt": prompt, "dir_alias": dirAlias}, ""); err != nil {
		return nil, err
	}
	return s.Idempotent(ctx, requestID, func(tx *sql.Tx) (map[string]any, error) {
		p, l, err := s.needOrchestrator(tx, ctx, session)
		if err != nil {
			return nil, err
		}
		if l["halted"].(bool) {
			return nil, &HubError{Status: 423, Code: "halted", Message: "오케스트레이션이 정지돼 있어요"}
		}
		hostName, harnessJSON, err := s.relayHost(tx, p.ProjectID, hostID)
		if err != nil {
			return nil, err
		}
		var allowed []string
		if err := json.Unmarshal([]byte(harnessJSON), &allowed); err != nil {
			return nil, err
		}
		found := false
		for _, h := range allowed {
			if h == harness {
				found = true
			}
		}
		if !found {
			return nil, &HubError{Status: 409, Code: "harness_not_on_host", Message: fmt.Sprintf("그 중계에 %s 어댑터가 없어요", harness), Detail: map[string]any{"harnesses": allowed}}
		}
		if err := s.relayRequestCounter(tx, ctx, p.ProjectID, "session_requests", 10); err != nil {
			return nil, err
		}
		rid, err := s.nextSessionRequestID(tx, p.ProjectID)
		if err != nil {
			return nil, err
		}
		target := map[string]any{"dir_alias": dirAlias, "harness": harness, "permission_mode": permissionMode, "prompt": prompt}
		if _, err := tx.Exec("INSERT INTO session_request(project_id,id,kind,host_id,target_json,requested_by,state,created_at) VALUES(?,?,'spawn',?,?,?,'pending_approval',?)", p.ProjectID, rid, hostID, MustJSON(target), session, db.FormatISO(ctx.Now)); err != nil {
			return nil, err
		}
		if err := s.RecordEvent(tx, ctx, &p.ProjectID, "session_request", rid, "request", nil, map[string]any{"kind": "spawn", "dir_alias": dirAlias, "harness": harness, "permission_mode": permissionMode, "prompt": prompt}, nil); err != nil {
			return nil, err
		}
		body := map[string]any{"request": rid, "kind": "spawn", "host": hostName, "dir_alias": dirAlias, "harness": harness, "permission_mode": permissionMode, "prompt": prompt}
		if err := s.approvalNote(tx, ctx, p.ProjectID, rid, body); err != nil {
			return nil, err
		}
		return map[string]any{"request": map[string]any{"id": rid, "state": "pending_approval", "kind": "spawn"}}, nil
	})
}

func (s *Store) OrchRequestStop(ctx Ctx, session, targetSession, reason string) (map[string]any, error) {
	if err := ScanSecrets(reason, "reason"); err != nil {
		return nil, err
	}
	return s.withWriteTx(func(tx *sql.Tx) (map[string]any, error) {
		p, _, err := s.needOrchestrator(tx, ctx, session)
		if err != nil {
			return nil, err
		}
		target, err := s.activeSession(tx, p.ProjectID, targetSession)
		if err != nil {
			return nil, err
		}
		var host sql.NullString
		if err := tx.QueryRow("SELECT host_id FROM session WHERE project_id=? AND id=?", p.ProjectID, targetSession).Scan(&host); err != nil {
			return nil, err
		}
		if !host.Valid || host.String == "" {
			return nil, &HubError{Status: 409, Code: "not_relay_session", Message: "중계가 띄운 세션이 아니에요 — 사람이 보는 세션은 멈출 수 없어요 (메시지로 release)"}
		}
		rid, err := s.nextSessionRequestID(tx, p.ProjectID)
		if err != nil {
			return nil, err
		}
		targetBody := map[string]any{"session": targetSession, "reason": reason}
		if _, err := tx.Exec("INSERT INTO session_request(project_id,id,kind,host_id,target_json,requested_by,state,created_at) VALUES(?,?,'stop',?,?,?,'pending_approval',?)", p.ProjectID, rid, host.String, MustJSON(targetBody), session, db.FormatISO(ctx.Now)); err != nil {
			return nil, err
		}
		if err := s.RecordEvent(tx, ctx, &p.ProjectID, "session_request", rid, "request", nil, map[string]any{"kind": "stop", "session": target["id"]}, nil); err != nil {
			return nil, err
		}
		if err := s.approvalNote(tx, ctx, p.ProjectID, rid, map[string]any{"request": rid, "kind": "stop", "session": targetSession, "reason": reason}); err != nil {
			return nil, err
		}
		return map[string]any{"request": map[string]any{"id": rid, "state": "pending_approval", "kind": "stop"}}, nil
	})
}

func (s *Store) ApprovalDecide(ctx Ctx, requestID, decision, note string) (map[string]any, error) {
	p, err := needOwner(ctx)
	if err != nil {
		return nil, err
	}
	if decision != "approve" && decision != "reject" {
		return nil, InvalidField("decision", "approve · reject 중 하나")
	}
	state := map[bool]string{true: "approved", false: "rejected"}[decision == "approve"]
	if err := ScanSecrets(note, "note"); err != nil {
		return nil, err
	}
	return s.withWriteTx(func(tx *sql.Tx) (map[string]any, error) {
		var old string
		err := tx.QueryRow("SELECT state FROM session_request WHERE project_id=? AND id=?", p.ProjectID, requestID).Scan(&old)
		if err == sql.ErrNoRows {
			return nil, NotFound("요청이 없어요: " + requestID)
		}
		if err != nil {
			return nil, err
		}
		if old != "pending_approval" {
			return nil, &HubError{Status: 409, Code: "request_not_pending", Message: "이미 " + old + " 인 요청이에요", Detail: map[string]any{"state": old}}
		}
		if _, err := tx.Exec("UPDATE session_request SET state=?,decided_by=?,decided_at=?,version=version+1 WHERE project_id=? AND id=?", state, p.Callsign, db.FormatISO(ctx.Now), p.ProjectID, requestID); err != nil {
			return nil, err
		}
		if err := s.RecordEvent(tx, ctx, &p.ProjectID, "session_request", requestID, decision, map[string]any{"state": old}, map[string]any{"state": state, "note": note}, nil); err != nil {
			return nil, err
		}
		toKind, to, err := s.orchestratorAddress(tx, ctx, p.ProjectID)
		if err != nil {
			return nil, err
		}
		if _, err := s.EnqueueMessage(tx, ctx, p.ProjectID, toKind, to, "note", map[string]any{"event": "request_" + state, "request": requestID, "note": note}, p.Callsign, "", false, requestID); err != nil {
			return nil, err
		}
		return map[string]any{"request": map[string]any{"id": requestID, "state": state}}, nil
	})
}

func (s *Store) LinkSpawnRequest(tx *sql.Tx, ctx Ctx, p *Principal, sessionID string, requestID any) error {
	rid, ok := requestID.(string)
	if !ok {
		return InvalidField("session.spawn_request", "SR-NNNN")
	}
	var state, host, result string
	err := tx.QueryRow("SELECT state,host_id,result_json FROM session_request WHERE project_id=? AND id=? AND kind='spawn'", p.ProjectID, rid).Scan(&state, &host, &result)
	if err == sql.ErrNoRows || (err == nil && state != "dispatched" && state != "done") {
		return &HubError{Status: 409, Code: "spawn_request_invalid", Message: "실행 중인 세션 요청이 아니에요", Detail: map[string]any{"request": rid}}
	}
	if err != nil {
		return err
	}
	var resultMap map[string]any
	if err := json.Unmarshal([]byte(result), &resultMap); err != nil {
		return err
	}
	if resultMap["session"] != "" && resultMap["session"] != nil {
		return &HubError{Status: 409, Code: "spawn_request_used", Message: "이미 세션이 묶인 요청이에요", Detail: map[string]any{"request": rid}}
	}
	if _, err := tx.Exec("UPDATE session SET host_id=?,kind='worker',allow_wait=1 WHERE project_id=? AND id=?", host, p.ProjectID, sessionID); err != nil {
		return err
	}
	resultMap["session"] = sessionID
	if _, err := tx.Exec("UPDATE session_request SET result_json=?,version=version+1 WHERE project_id=? AND id=?", MustJSON(resultMap), p.ProjectID, rid); err != nil {
		return err
	}
	return s.RecordEvent(tx, ctx, &p.ProjectID, "session", sessionID, "link_spawn", nil, map[string]any{"request": rid, "host": host}, nil)
}
