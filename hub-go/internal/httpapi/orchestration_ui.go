package httpapi

import (
	"database/sql"
	"encoding/json"
	"net/http"
	"time"

	"github.com/ykylee/standard_ai_workflow/hub-go/internal/store"
)

func (s *Server) screenOrchestration(pid string, principal *store.Principal, now time.Time, r *http.Request) (map[string]any, error) {
	viewer := &store.Principal{Kind: "viewer", ProjectID: pid, Callsign: principal.Callsign, CallsignKind: principal.CallsignKind, HumanApproved: principal.HumanApproved, Role: principal.Role, Name: principal.Name}
	ctx := store.Ctx{Now: now, Via: "ui", Principal: viewer}
	sessionResult, err := s.cfg.Store.SessionList(ctx, "", r.URL.Query().Get("status"))
	if err != nil {
		return nil, err
	}
	dbConn := s.cfg.Store.DB()
	metaRows, err := dbConn.Query("SELECT id,host_id,guide_version FROM session WHERE project_id=?", pid)
	if err != nil {
		return nil, err
	}
	meta := map[string]map[string]any{}
	for metaRows.Next() {
		var id string
		var host, guide sql.NullString
		if err := metaRows.Scan(&id, &host, &guide); err != nil {
			metaRows.Close()
			return nil, err
		}
		meta[id] = map[string]any{"host_id": nullableString(host.String), "guide_version": nullableString(guide.String)}
	}
	if err := metaRows.Err(); err != nil {
		metaRows.Close()
		return nil, err
	}
	if err := metaRows.Close(); err != nil {
		return nil, err
	}
	sessions := []map[string]any{}
	for _, raw := range sessionResult["sessions"].([]map[string]any) {
		item := map[string]any{}
		for k, v := range raw {
			item[k] = v
		}
		if extra, ok := meta[raw["id"].(string)]; ok {
			item["host_id"] = extra["host_id"]
			item["guide_version"] = extra["guide_version"]
		} else {
			item["host_id"] = nil
			item["guide_version"] = nil
		}
		sessions = append(sessions, item)
	}
	assignmentRows, err := dbConn.Query(`SELECT a.task_id,COALESCE(t.title,''),COALESCE(t.status,''),COALESCE(t.progress_note,''),a.session_id,a.callsign,a.message_id,a.state,a.return_reason,a.offered_at,a.accepted_at,a.reported_at,a.report_json,m.state,m.delivered_via,m.delivered_at,m.last_delivered_at,m.delivery_count FROM assignment a LEFT JOIN task t ON t.project_id=a.project_id AND t.id=a.task_id LEFT JOIN inbox_message m ON m.project_id=a.project_id AND m.id=a.message_id WHERE a.project_id=? ORDER BY a.offered_at DESC,a.rowid DESC LIMIT 200`, pid)
	if err != nil {
		return nil, err
	}
	assignments := []map[string]any{}
	for assignmentRows.Next() {
		var taskID, title, taskStatus, progress, sessionID, callsign, messageID, state, returnReason, offered string
		var accepted, reported, messageState, deliveredVia, deliveredAt, lastDelivered sql.NullString
		var reportJSON string
		var deliveryCount sql.NullInt64
		if err := assignmentRows.Scan(&taskID, &title, &taskStatus, &progress, &sessionID, &callsign, &messageID, &state, &returnReason, &offered, &accepted, &reported, &reportJSON, &messageState, &deliveredVia, &deliveredAt, &lastDelivered, &deliveryCount); err != nil {
			assignmentRows.Close()
			return nil, err
		}
		var report map[string]any
		if err := json.Unmarshal([]byte(reportJSON), &report); err != nil {
			assignmentRows.Close()
			return nil, err
		}
		if report == nil {
			report = map[string]any{}
		}
		assignments = append(assignments, map[string]any{"task_id": taskID, "task_title": title, "task_status": taskStatus, "progress_note": progress, "session_id": sessionID, "callsign": callsign, "message_id": messageID, "state": state, "return_reason": nullableString(returnReason), "offered_at": offered, "accepted_at": nullableString(accepted.String), "reported_at": nullableString(reported.String), "report": report, "message_state": nullableString(messageState.String), "delivered_via": nullableString(deliveredVia.String), "delivered_at": nullableString(deliveredAt.String), "last_delivered_at": nullableString(lastDelivered.String), "delivery_count": int(deliveryCount.Int64)})
	}
	if err := assignmentRows.Err(); err != nil {
		assignmentRows.Close()
		return nil, err
	}
	if err := assignmentRows.Close(); err != nil {
		return nil, err
	}
	unackRows, err := dbConn.Query("SELECT id,to_kind,to_id,kind,ref_task,delivered_via,delivered_at,created_at,body_json FROM inbox_message WHERE project_id=? AND state='unacknowledged' ORDER BY created_at DESC,rowid DESC LIMIT 100", pid)
	if err != nil {
		return nil, err
	}
	unack := []map[string]any{}
	for unackRows.Next() {
		var id, toKind, toID, kind, created, bodyJSON string
		var refTask, deliveredVia, deliveredAt sql.NullString
		if err := unackRows.Scan(&id, &toKind, &toID, &kind, &refTask, &deliveredVia, &deliveredAt, &created, &bodyJSON); err != nil {
			unackRows.Close()
			return nil, err
		}
		var body any // 본문은 객체가 아닐 수 있다 (옛 문자열 메시지)
		if err := json.Unmarshal([]byte(bodyJSON), &body); err != nil {
			unackRows.Close()
			return nil, err
		}
		unack = append(unack, map[string]any{"id": id, "to_kind": toKind, "to_id": toID, "kind": kind, "ref_task": nullableString(refTask.String), "delivered_via": nullableString(deliveredVia.String), "delivered_at": nullableString(deliveredAt.String), "created_at": created, "body": body})
	}
	if err := unackRows.Err(); err != nil {
		unackRows.Close()
		return nil, err
	}
	if err := unackRows.Close(); err != nil {
		return nil, err
	}
	requestRows, err := dbConn.Query("SELECT id,kind,host_id,target_json,requested_by,state,decided_by,decided_at,result_json,created_at FROM session_request WHERE project_id=? ORDER BY created_at DESC,rowid DESC LIMIT 100", pid)
	if err != nil {
		return nil, err
	}
	requests := []map[string]any{}
	for requestRows.Next() {
		var id, kind, host, targetJSON, requested, state, resultJSON, created string
		var decidedBy, decidedAt sql.NullString
		if err := requestRows.Scan(&id, &kind, &host, &targetJSON, &requested, &state, &decidedBy, &decidedAt, &resultJSON, &created); err != nil {
			requestRows.Close()
			return nil, err
		}
		var target, result map[string]any
		if err := json.Unmarshal([]byte(targetJSON), &target); err != nil {
			requestRows.Close()
			return nil, err
		}
		if err := json.Unmarshal([]byte(resultJSON), &result); err != nil {
			requestRows.Close()
			return nil, err
		}
		if result == nil {
			result = map[string]any{}
		}
		requests = append(requests, map[string]any{"id": id, "kind": kind, "host_id": host, "target": target, "requested_by": requested, "state": state, "decided_by": nullableString(decidedBy.String), "decided_at": nullableString(decidedAt.String), "result": result, "created_at": created})
	}
	if err := requestRows.Err(); err != nil {
		requestRows.Close()
		return nil, err
	}
	if err := requestRows.Close(); err != nil {
		return nil, err
	}
	hosts, err := screenRelayHosts(dbConn, pid)
	if err != nil {
		return nil, err
	}
	me := principalSummary(principal)
	me["can_answer"] = me["can_answer"] == true && principal.ProjectID == pid
	me["can_manage"] = me["can_manage"] == true && principal.ProjectID == pid
	return map[string]any{"principal": me, "orchestrator": sessionResult["orchestrator"], "sessions": sessions, "session_counts": sessionResult["counts"], "unknown_sessions": sessionResult["unknown"], "assignments": assignments, "unacknowledged": unack, "requests": requests, "hosts": hosts}, nil
}

func screenRelayHosts(dbConn *sql.DB, projectID string) ([]map[string]any, error) {
	rows, err := dbConn.Query("SELECT host_id,name,projects_json,harnesses_json,allow_digest,last_seen_at FROM relay_host WHERE revoked_at IS NULL ORDER BY host_id")
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	out := []map[string]any{}
	for rows.Next() {
		var id, name, projectsJSON, harnessesJSON, digest string
		var last sql.NullString
		if err := rows.Scan(&id, &name, &projectsJSON, &harnessesJSON, &digest, &last); err != nil {
			return nil, err
		}
		var projects, harnesses []string
		if err := json.Unmarshal([]byte(projectsJSON), &projects); err != nil {
			return nil, err
		}
		if err := json.Unmarshal([]byte(harnessesJSON), &harnesses); err != nil {
			return nil, err
		}
		allowed := false
		for _, pid := range projects {
			if pid == projectID {
				allowed = true
				break
			}
		}
		if allowed {
			out = append(out, map[string]any{"host_id": id, "name": name, "harnesses": harnesses, "allow_digest": nullableString(digest), "last_seen_at": nullableString(last.String)})
		}
	}
	return out, rows.Err()
}
