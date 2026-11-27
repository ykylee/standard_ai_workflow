package store

import (
	"crypto/rand"
	"database/sql"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"time"
	"unicode/utf8"

	"github.com/ykylee/standard_ai_workflow/hub-go/internal/db"
	"github.com/ykylee/standard_ai_workflow/hub-go/internal/pytext"
)

const relayNameMax = 80

type RelayHost struct {
	ID, Name, OwnerCallsign string
	Projects, Harnesses     []string
}

// RelayRegister consumes a single-use relay invite and returns its bearer once.
func (s *Store) RelayRegister(now time.Time, raw any) (map[string]any, error) {
	a, ok := raw.(map[string]any)
	if !ok {
		return nil, InvalidField("arguments", "객체여야 해요")
	}
	allowed := map[string]bool{"invite": true, "name": true, "harnesses": true}
	unknown := false
	for k := range a {
		if !allowed[k] {
			unknown = true
		}
	}
	if unknown {
		return nil, &HubError{Status: 400, Code: "unknown_field", Message: "invite · name · harnesses 만 받아요"}
	}
	code, ok := a["invite"].(string)
	if !ok || code == "" {
		return nil, InvalidField("invite", "필수")
	}
	name, ok := a["name"].(string)
	if !ok || pytext.Strip(name) == "" || utf8.RuneCountInString(name) > relayNameMax {
		return nil, InvalidField("name", fmt.Sprintf("1~%d자", relayNameMax))
	}
	harnesses := []string{}
	if rawH, exists := a["harnesses"]; exists && rawH != nil {
		values, valid := rawH.([]any)
		if !valid {
			return nil, InvalidField("harnesses", "하네스 이름 목록")
		}
		for _, v := range values {
			h, ok := v.(string)
			if !ok || h == "" {
				return nil, InvalidField("harnesses", "하네스 이름 목록")
			}
			harnesses = append(harnesses, h)
		}
	}
	if err := ScanSecrets(map[string]any{"name": name, "harnesses": stringSliceAny(harnesses)}, ""); err != nil {
		return nil, err
	}
	token, err := NewToken()
	if err != nil {
		return nil, err
	}
	var random [4]byte
	if _, err := rand.Read(random[:]); err != nil {
		return nil, err
	}
	hostID := fmt.Sprintf("H-%s-%s", now.UTC().Format("20060102"), hex.EncodeToString(random[:]))
	ctx := Ctx{Now: now, Via: "relay"}
	var projectID, owner string
	_, err = s.withWriteTx(func(tx *sql.Tx) (map[string]any, error) {
		var used sql.NullString
		var expires string
		var host string
		var cp, co string
		err := tx.QueryRow("SELECT for_project,owner_callsign,used_at,expires_at,host_id FROM relay_invite WHERE code_hash=?", HashToken(code)).Scan(&cp, &co, &used, &expires, &host)
		if err == sql.ErrNoRows {
			return nil, &HubError{Status: 403, Code: "invite_invalid", Message: "초대 코드가 없거나 · 썼거나 · 만료됐어요"}
		}
		if err != nil {
			return nil, err
		}
		if used.Valid || expires <= db.FormatISO(now) {
			return nil, &HubError{Status: 403, Code: "invite_invalid", Message: "초대 코드가 없거나 · 썼거나 · 만료됐어요"}
		}
		projectID, owner = cp, co
		if _, err := tx.Exec("UPDATE relay_invite SET used_at=?,host_id=? WHERE code_hash=?", db.FormatISO(now), hostID, HashToken(code)); err != nil {
			return nil, err
		}
		if _, err := tx.Exec("INSERT INTO relay_host(host_id,name,token_hash,owner_callsign,projects_json,harnesses_json,last_seen_at) VALUES(?,?,?,?,?,?,?)", hostID, pytext.Strip(name), HashToken(token), owner, MustJSON([]string{projectID}), MustJSON(harnesses), db.FormatISO(now)); err != nil {
			return nil, err
		}
		if err := s.RecordEvent(tx, ctx, &projectID, "relay_host", hostID, "register", nil, map[string]any{"name": pytext.Strip(name), "harnesses": harnesses}, &owner); err != nil {
			return nil, err
		}
		return map[string]any{}, nil
	})
	if err != nil {
		return nil, err
	}
	return map[string]any{"host_id": hostID, "token": token, "project_id": projectID}, nil
}

func stringSliceAny(values []string) []any {
	out := make([]any, len(values))
	for i, v := range values {
		out[i] = v
	}
	return out
}

// RelayAuthenticate validates a relay-only bearer; revoked and callsign tokens do not pass.
func (s *Store) RelayAuthenticate(token string) (*RelayHost, error) {
	if token == "" {
		return nil, nil
	}
	var h RelayHost
	var projectsJSON, harnessesJSON string
	err := s.pool.QueryRow("SELECT host_id,name,owner_callsign,projects_json,harnesses_json FROM relay_host WHERE token_hash=? AND revoked_at IS NULL", HashToken(token)).Scan(&h.ID, &h.Name, &h.OwnerCallsign, &projectsJSON, &harnessesJSON)
	if err == sql.ErrNoRows {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	if err := json.Unmarshal([]byte(projectsJSON), &h.Projects); err != nil {
		return nil, err
	}
	if err := json.Unmarshal([]byte(harnessesJSON), &h.Harnesses); err != nil {
		return nil, err
	}
	return &h, nil
}

type relaySession struct{ projectID, id, callsign string }

// RelayPollOnce updates host/session signals, dispatches approved requests, and delivers inbox work.
func (s *Store) RelayPollOnce(now time.Time, host *RelayHost, a map[string]any) (map[string]any, error) {
	if host == nil {
		return nil, Unauthorized("중계 토큰이 없거나 틀렸거나 거둔 토큰이에요")
	}
	projects := host.Projects
	dispatch := []map[string]any{}
	halted := []string{}
	sessions := []relaySession{}
	var digestValue any
	if digest, ok := a["allow_digest"].(string); ok {
		digestValue = digest
	}
	ctx := Ctx{Now: now, Via: "relay"}
	_, err := s.withWriteTx(func(tx *sql.Tx) (map[string]any, error) {
		if _, err := tx.Exec("UPDATE relay_host SET last_seen_at=?,allow_digest=COALESCE(?,allow_digest) WHERE host_id=? AND revoked_at IS NULL", db.FormatISO(now), digestValue, host.ID); err != nil {
			return nil, err
		}
		for _, pid := range projects {
			var isHalted int
			err := tx.QueryRow("SELECT halted FROM orchestrator_lease WHERE project_id=?", pid).Scan(&isHalted)
			if err != nil && err != sql.ErrNoRows {
				return nil, err
			}
			if isHalted != 0 {
				halted = append(halted, pid)
				continue
			}
			rows, err := tx.Query("SELECT id,kind,target_json FROM session_request WHERE project_id=? AND host_id=? AND state='approved' ORDER BY created_at,rowid", pid, host.ID)
			if err != nil {
				return nil, err
			}
			type req struct{ id, kind, target string }
			pending := []req{}
			for rows.Next() {
				var q req
				if err := rows.Scan(&q.id, &q.kind, &q.target); err != nil {
					rows.Close()
					return nil, err
				}
				pending = append(pending, q)
			}
			if err := rows.Err(); err != nil {
				rows.Close()
				return nil, err
			}
			if err := rows.Close(); err != nil {
				return nil, err
			}
			for _, q := range pending {
				if _, err := tx.Exec("UPDATE session_request SET state='dispatched',version=version+1 WHERE project_id=? AND id=?", pid, q.id); err != nil {
					return nil, err
				}
				if err := s.RecordEvent(tx, ctx, &pid, "session_request", q.id, "dispatch", nil, nil, ptr("hub")); err != nil {
					return nil, err
				}
				var target map[string]any
				if err := json.Unmarshal([]byte(q.target), &target); err != nil {
					return nil, err
				}
				dispatch = append(dispatch, map[string]any{"project_id": pid, "request": q.id, "kind": q.kind, "target": target})
			}
		}
		rows, err := tx.Query("SELECT project_id,id,callsign FROM session WHERE host_id=? AND status='active'", host.ID)
		if err != nil {
			return nil, err
		}
		for rows.Next() {
			var v relaySession
			if err := rows.Scan(&v.projectID, &v.id, &v.callsign); err != nil {
				rows.Close()
				return nil, err
			}
			sessions = append(sessions, v)
		}
		if err := rows.Err(); err != nil {
			rows.Close()
			return nil, err
		}
		return map[string]any{}, rows.Close()
	})
	if err != nil {
		return nil, err
	}
	reported := map[string]string{}
	if values, ok := a["sessions"].([]any); ok {
		for _, raw := range values {
			if item, ok := raw.(map[string]any); ok {
				sid, _ := item["session"].(string)
				status, _ := item["status"].(string)
				if sid != "" {
					reported[sid] = status
				}
			}
		}
	}
	deliver := []map[string]any{}
	for _, session := range sessions {
		if reported[session.id] == "ended" {
			if err := s.relayEndSession(ctx, session.projectID, session.id, session.callsign); err != nil {
				return nil, err
			}
			continue
		}
		if reported[session.id] == "idle" || reported[session.id] == "busy" {
			if _, err := s.pool.Exec("UPDATE session SET last_signal_at=? WHERE project_id=? AND id=?", db.FormatISO(now), session.projectID, session.id); err != nil {
				return nil, err
			}
		}
		p := &Principal{Kind: "callsign", ProjectID: session.projectID, Callsign: session.callsign}
		got, err := s.InboxTake(Ctx{Now: now, Via: "relay", Principal: p}, session.id, "adapter")
		if err != nil {
			return nil, err
		}
		messages, _ := got["messages"].([]map[string]any)
		if len(messages) > 0 {
			deliver = append(deliver, map[string]any{"session": session.id, "project_id": session.projectID, "messages": messages, "remaining": got["remaining"]})
		}
	}
	linked := []map[string]any{}
	for _, session := range sessions {
		rows, err := s.pool.Query("SELECT id,result_json FROM session_request WHERE project_id=? AND host_id=? AND kind='spawn' ORDER BY created_at DESC,rowid DESC", session.projectID, host.ID)
		if err != nil {
			return nil, err
		}
		for rows.Next() {
			var rid, resultJSON string
			if err := rows.Scan(&rid, &resultJSON); err != nil {
				rows.Close()
				return nil, err
			}
			var result map[string]any
			if err := json.Unmarshal([]byte(resultJSON), &result); err != nil {
				rows.Close()
				return nil, err
			}
			if result["session"] == session.id {
				linked = append(linked, map[string]any{"session": session.id, "request": rid, "project_id": session.projectID})
				break
			}
		}
		if err := rows.Err(); err != nil {
			rows.Close()
			return nil, err
		}
		if err := rows.Close(); err != nil {
			return nil, err
		}
	}
	return map[string]any{"dispatch": dispatch, "deliver": deliver, "halted": halted, "sessions": linked}, nil
}

func ptr(s string) *string { return &s }

func (s *Store) relayEndSession(ctx Ctx, projectID, sessionID, callsign string) error {
	_, err := s.withWriteTx(func(tx *sql.Tx) (map[string]any, error) {
		var status string
		if err := tx.QueryRow("SELECT status FROM session WHERE project_id=? AND id=? AND callsign=?", projectID, sessionID, callsign).Scan(&status); err != nil {
			return nil, err
		}
		if status != "ended" {
			if _, err := tx.Exec("UPDATE session SET status='ended',ended_at=?,waiting_since=NULL,version=version+1 WHERE project_id=? AND id=?", db.FormatISO(ctx.Now), projectID, sessionID); err != nil {
				return nil, err
			}
			if err := s.RecordEvent(tx, ctx, &projectID, "session", sessionID, "end", nil, nil, &callsign); err != nil {
				return nil, err
			}
		}
		rows, err := tx.Query("SELECT task_id FROM assignment WHERE project_id=? AND session_id=? AND state IN ('offered','accepted')", projectID, sessionID)
		if err != nil {
			return nil, err
		}
		tasks := []string{}
		for rows.Next() {
			var id string
			if err := rows.Scan(&id); err != nil {
				rows.Close()
				return nil, err
			}
			tasks = append(tasks, id)
		}
		if err := rows.Err(); err != nil {
			rows.Close()
			return nil, err
		}
		if err := rows.Close(); err != nil {
			return nil, err
		}
		for _, task := range tasks {
			if err := s.returnOfferedAssignment(tx, ctx, projectID, task, "session_ended"); err != nil {
				return nil, err
			}
		}
		return map[string]any{}, nil
	})
	return err
}

// RelayResult records a host's result for one of its dispatched requests.
func (s *Store) RelayResult(now time.Time, host *RelayHost, raw any) (map[string]any, error) {
	if host == nil {
		return nil, Unauthorized("중계 토큰이 없거나 틀렸거나 거둔 토큰이에요")
	}
	a, ok := raw.(map[string]any)
	if !ok {
		return nil, InvalidField("arguments", "객체여야 해요")
	}
	allowed := map[string]bool{"project_id": true, "request": true, "state": true, "result": true}
	unknown := false
	for k := range a {
		if !allowed[k] {
			unknown = true
		}
	}
	if unknown {
		return nil, &HubError{Status: 400, Code: "unknown_field", Message: "project_id · request · state · result 만 받아요"}
	}
	projectID, _ := a["project_id"].(string)
	requestID, _ := a["request"].(string)
	state, _ := a["state"].(string)
	if state != "done" && state != "refused_by_host" && state != "failed" {
		return nil, InvalidField("state", "done · refused_by_host · failed 중 하나")
	}
	result := map[string]any{}
	if rawResult, exists := a["result"]; exists && rawResult != nil {
		var ok bool
		result, ok = rawResult.(map[string]any)
		if !ok {
			return nil, InvalidField("result", "객체여야 해요")
		}
	}
	if err := ScanSecrets(result, "result"); err != nil {
		return nil, err
	}
	ctx := Ctx{Now: now, Via: "relay"}
	return s.withWriteTx(func(tx *sql.Tx) (map[string]any, error) {
		var hostID, oldState, oldResult string
		err := tx.QueryRow("SELECT host_id,state,result_json FROM session_request WHERE project_id=? AND id=?", projectID, requestID).Scan(&hostID, &oldState, &oldResult)
		if err == sql.ErrNoRows {
			return nil, NotFound("이 중계 앞 요청이 아니에요")
		}
		if err != nil {
			return nil, err
		}
		if hostID != host.ID {
			return nil, NotFound("이 중계 앞 요청이 아니에요")
		}
		if oldState != "dispatched" {
			return nil, &HubError{Status: 409, Code: "request_not_dispatched", Message: oldState + " 인 요청이에요", Detail: map[string]any{"state": oldState}}
		}
		merged := map[string]any{}
		if err := json.Unmarshal([]byte(oldResult), &merged); err != nil {
			return nil, err
		}
		for k, v := range result {
			merged[k] = v
		}
		if _, err := tx.Exec("UPDATE session_request SET state=?,result_json=?,version=version+1 WHERE project_id=? AND id=?", state, MustJSON(merged), projectID, requestID); err != nil {
			return nil, err
		}
		if err := s.RecordEvent(tx, ctx, &projectID, "session_request", requestID, "result:"+state, nil, merged, ptr("hub")); err != nil {
			return nil, err
		}
		toKind, to, err := s.orchestratorAddress(tx, ctx, projectID)
		if err != nil {
			return nil, err
		}
		if _, err := s.EnqueueMessage(tx, ctx, projectID, toKind, to, "note", map[string]any{"event": "request_" + state, "request": requestID, "result": merged}, "hub", "", false, requestID); err != nil {
			return nil, err
		}
		return map[string]any{"request": requestID, "state": state}, nil
	})
}
