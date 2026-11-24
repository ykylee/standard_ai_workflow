package store

import (
	"crypto/rand"
	"database/sql"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"sort"
	"strconv"
	"strings"
	"time"

	"github.com/ykylee/standard_ai_workflow/hub-go/internal/db"
)

// A2A(Agent2Agent) 1.0 승인 Task — Python hub/a2a.py 와 같은 계약.
// 상태는 저장하지 않고 확인 요청에서 파생한다. 상태는 권한이 아니다 — 실행 권한은 approval_grant 뿐이다.

// A2AError is a protocol error; the HTTP layer renders it as a JSON-RPC error object.
type A2AError struct{ Reason, Message string }

func (e *A2AError) Error() string { return e.Reason + ": " + e.Message }

func a2aBad(message string) error { return &A2AError{"INVALID_PARAMS", message} }

var a2aStates = map[string]bool{"SUBMITTED": true, "WORKING": true, "COMPLETED": true, "FAILED": true, "CANCELED": true, "INPUT_REQUIRED": true, "REJECTED": true, "AUTH_REQUIRED": true}

type a2aRow struct {
	id, context, message, created, request, inbox                  string
	canceled, acked, note, grant, action, params, summary, expires sql.NullString
}

func (r a2aRow) state() (string, string) {
	switch {
	case r.canceled.String != "":
		return "CANCELED", r.canceled.String
	case r.inbox == "acked":
		return "COMPLETED", r.acked.String
	case r.inbox == "declined":
		return "REJECTED", r.acked.String
	case r.inbox == "expired":
		return "FAILED", r.created
	}
	return "AUTH_REQUIRED", r.created
}

type a2aQuery interface {
	Query(query string, args ...any) (*sql.Rows, error)
}

func a2aRows(q a2aQuery, p *Principal, taskID string) ([]a2aRow, error) {
	query := "SELECT t.id,t.context_id,t.message_json,t.created_at,t.canceled_at,t.request_id,m.state,m.acked_at,m.ack_reason,g.state,g.action,g.params_json,g.summary_json,g.expires_at " +
		"FROM a2a_task t JOIN inbox_message m ON m.project_id=t.project_id AND m.id=t.request_id " +
		"LEFT JOIN approval_grant g ON g.project_id=t.project_id AND g.id=t.request_id WHERE t.project_id=? AND t.callsign=?"
	args := []any{p.ProjectID, p.Callsign}
	if taskID != "" {
		query, args = query+" AND t.id=?", append(args, taskID)
	}
	rows, err := q.Query(query, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	out := []a2aRow{}
	for rows.Next() {
		var r a2aRow
		if err := rows.Scan(&r.id, &r.context, &r.message, &r.created, &r.canceled, &r.request, &r.inbox, &r.acked, &r.note, &r.grant, &r.action, &r.params, &r.summary, &r.expires); err != nil {
			return nil, err
		}
		out = append(out, r)
	}
	return out, rows.Err()
}

func a2aOne(q a2aQuery, p *Principal, taskID string) (a2aRow, error) {
	if taskID != "" {
		rows, err := a2aRows(q, p, taskID)
		if err != nil {
			return a2aRow{}, err
		}
		if len(rows) == 1 {
			return rows[0], nil
		}
	}
	// 남의 Task 도 같은 답 — 존재를 드러내지 않는다.
	return a2aRow{}, &A2AError{"TASK_NOT_FOUND", "Task 가 없다: " + taskID}
}

func a2aMillis(iso string) string {
	t, err := time.Parse(time.RFC3339, iso)
	if err != nil {
		return iso
	}
	return t.UTC().Format("2006-01-02T15:04:05.000Z")
}

func a2aTask(ctx Ctx, r a2aRow, history *int, artifacts bool) map[string]any {
	state, at := r.state()
	text := map[string]string{"AUTH_REQUIRED": "사람이 허브 화면에서 로그인해 승인하거나 거절해야 한다.", "COMPLETED": "사람이 승인했다.",
		"REJECTED": "사람이 거절했다.", "CANCELED": "요청한 에이전트가 취소했다.", "FAILED": "요청이 만료됐다."}[state]
	data := map[string]any{"approval_url": strings.TrimRight(ctx.PublicURL, "/") + "/ui/#/p/" + ctx.Principal.ProjectID + "/confirmations"}
	if r.note.String != "" {
		data["note"] = r.note.String
	}
	if r.action.String != "" {
		summary, err := briefSummary(r.summary.String)
		if err != nil {
			summary = map[string]any{}
		}
		data["action"] = map[string]any{"params": json.RawMessage(r.params.String), "summary": summary}
	}
	task := map[string]any{"id": r.id, "contextId": r.context, "status": map[string]any{
		"state": "TASK_STATE_" + state, "timestamp": a2aMillis(at), "message": map[string]any{
			"messageId": r.id + "-status", "taskId": r.id, "contextId": r.context, "role": "ROLE_AGENT",
			"parts": []any{map[string]any{"text": text}, map[string]any{"data": data, "mediaType": "application/json"}}}}}
	if state == "COMPLETED" && artifacts {
		result := map[string]any{"decision": "approve", "note": r.note.String}
		if r.action.String != "" {
			result["approval_id"], result["approval_state"], result["action"] = r.request, r.grant.String, json.RawMessage(r.params.String)
			result["expires_at"] = nil
			if r.expires.Valid {
				result["expires_at"] = r.expires.String
			}
		}
		task["artifacts"] = []any{map[string]any{"artifactId": "approval", "name": "승인 결과",
			"parts": []any{map[string]any{"data": result, "mediaType": "application/json"}}}}
	}
	if history == nil || *history > 0 {
		task["history"] = []any{json.RawMessage(r.message)}
	}
	return task
}

func a2aInt(params map[string]any, key string, low, high int) (*int, error) {
	raw, ok := params[key]
	if !ok || raw == nil {
		return nil, nil
	}
	n, ok := raw.(int)
	if !ok || n < low || n > high {
		return nil, a2aBad(fmt.Sprintf("%s: %d~%d 정수", key, low, high))
	}
	return &n, nil
}

func a2aStr(params map[string]any, key string, limit int) (string, error) {
	raw, ok := params[key]
	if !ok || raw == nil {
		return "", nil
	}
	text, ok := raw.(string)
	if !ok || len([]rune(text)) > limit {
		return "", a2aBad(fmt.Sprintf("%s: %d자 이하 문자열", key, limit))
	}
	return text, nil
}

// A2AGet returns one of the caller's tasks.
func (s *Store) A2AGet(ctx Ctx, params map[string]any) (map[string]any, error) {
	history, err := a2aInt(params, "historyLength", 0, 1000)
	if err != nil {
		return nil, err
	}
	p, err := NeedCallsign(ctx)
	if err != nil {
		return nil, err
	}
	id, err := a2aStr(params, "id", 256)
	if err != nil {
		return nil, err
	}
	row, err := a2aOne(s.pool, p, id)
	if err != nil {
		return nil, err
	}
	return a2aTask(ctx, row, history, true), nil
}

// A2AList lists the caller's tasks, most recently updated first.
func (s *Store) A2AList(ctx Ctx, params map[string]any) (map[string]any, error) {
	p, err := NeedCallsign(ctx)
	if err != nil {
		return nil, err
	}
	size, err := a2aInt(params, "pageSize", 1, 100)
	if err != nil {
		return nil, err
	}
	history, err := a2aInt(params, "historyLength", 0, 1000)
	if err != nil {
		return nil, err
	}
	var text [4]string
	for i, key := range []string{"contextId", "status", "pageToken", "statusTimestampAfter"} {
		if text[i], err = a2aStr(params, key, 256); err != nil {
			return nil, err
		}
	}
	artifacts := false
	if raw, ok := params["includeArtifacts"]; ok {
		if artifacts, ok = raw.(bool); !ok {
			return nil, a2aBad("includeArtifacts: true · false")
		}
	}
	status := text[1]
	if status == "TASK_STATE_UNSPECIFIED" {
		status = ""
	}
	if status != "" && (!strings.HasPrefix(status, "TASK_STATE_") || !a2aStates[strings.TrimPrefix(status, "TASK_STATE_")]) {
		return nil, a2aBad("모르는 status: " + status)
	}
	start := 0
	if text[2] != "" {
		digits := len(text[2]) < 10
		for _, c := range text[2] {
			digits = digits && c >= '0' && c <= '9'
		}
		if !digits {
			return nil, a2aBad("pageToken 이 올바르지 않다")
		}
		start, _ = strconv.Atoi(text[2])
	}
	var since time.Time
	if text[3] != "" {
		if since, err = time.Parse(time.RFC3339, text[3]); err != nil {
			return nil, a2aBad("statusTimestampAfter: RFC 3339 시각")
		}
	}
	rows, err := a2aRows(s.pool, p, "")
	if err != nil {
		return nil, err
	}
	keep := []a2aRow{}
	for _, r := range rows {
		state, at := r.state()
		if (text[0] != "" && r.context != text[0]) || (status != "" && "TASK_STATE_"+state != status) {
			continue
		}
		if !since.IsZero() {
			if t, err := time.Parse(time.RFC3339, at); err != nil || !t.After(since) {
				continue
			}
		}
		keep = append(keep, r)
	}
	sort.Slice(keep, func(i, j int) bool {
		_, a := keep[i].state()
		_, b := keep[j].state()
		if a != b {
			return a > b
		}
		return keep[i].id > keep[j].id
	})
	limit := 50
	if size != nil {
		limit = *size
	}
	end := start + limit
	tasks := []map[string]any{}
	for i := start; i < end && i < len(keep); i++ {
		tasks = append(tasks, a2aTask(ctx, keep[i], history, artifacts))
	}
	next := ""
	if end < len(keep) {
		next = strconv.Itoa(end)
	}
	return map[string]any{"tasks": tasks, "nextPageToken": next, "pageSize": len(tasks), "totalSize": len(keep)}, nil
}

func a2aContent(message map[string]any) (map[string]any, error) {
	parts, ok := message["parts"].([]any)
	if !ok || len(parts) == 0 {
		return nil, a2aBad("message.parts: 하나 이상")
	}
	texts := []string{}
	var data map[string]any
	for _, raw := range parts {
		part, _ := raw.(map[string]any)
		kind, n := "", 0
		for _, k := range []string{"text", "raw", "url", "data"} {
			if _, ok := part[k]; ok {
				kind, n = k, n+1
			}
		}
		if n != 1 {
			return nil, a2aBad("part 는 text · raw · url · data 가운데 정확히 하나")
		}
		switch kind {
		case "raw", "url":
			return nil, &A2AError{"CONTENT_TYPE_NOT_SUPPORTED", "파일 part 는 받지 않는다 — text 또는 data"}
		case "text":
			text, ok := part["text"].(string)
			if !ok {
				return nil, a2aBad("part.text: 문자열")
			}
			texts = append(texts, text)
		default:
			object, ok := part["data"].(map[string]any)
			if !ok || data != nil {
				return nil, a2aBad("data part 는 객체 하나")
			}
			data = object
		}
	}
	out, unknown := map[string]any{}, []string{}
	for k, v := range data {
		if k != "title" && k != "question" && k != "details" && k != "action" {
			unknown = append(unknown, k)
		}
		out[k] = v
	}
	if len(unknown) > 0 {
		sort.Strings(unknown)
		return nil, a2aBad("data 의 모르는 칸: " + strings.Join(unknown, ", "))
	}
	text := strings.TrimSpace(strings.Join(texts, "\n"))
	if _, ok := out["question"]; !ok {
		out["question"] = text
	}
	if _, ok := out["title"]; !ok {
		first := strings.TrimSpace(strings.SplitN(text, "\n", 2)[0])
		if first == "" {
			first = strings.SplitN(strings.TrimSpace(fmt.Sprint(out["question"])), "\n", 2)[0]
		}
		if r := []rune(first); len(r) > 160 {
			first = string(r[:160])
		}
		out["title"] = first
	}
	return out, nil
}

func a2aRandom(prefix string) (string, error) {
	var b [8]byte
	if _, err := rand.Read(b[:]); err != nil {
		return "", err
	}
	return prefix + hex.EncodeToString(b[:]), nil
}

// A2ASend creates an approval task; the same messageId from the same callsign returns the same task.
func (s *Store) A2ASend(ctx Ctx, params map[string]any) (map[string]any, error) {
	p, err := NeedCallsign(ctx)
	if err != nil {
		return nil, err
	}
	message, ok := params["message"].(map[string]any)
	if !ok {
		return nil, a2aBad("message: 객체")
	}
	config := map[string]any{}
	if raw, has := params["configuration"]; has && raw != nil {
		if config, ok = raw.(map[string]any); !ok {
			return nil, a2aBad("configuration: 객체")
		}
	}
	if raw, has := config["taskPushNotificationConfig"]; has && raw != nil {
		return nil, &A2AError{"PUSH_NOTIFICATION_NOT_SUPPORTED", "푸시 알림은 제공하지 않는다"}
	}
	history, err := a2aInt(config, "historyLength", 0, 1000)
	if err != nil {
		return nil, err
	}
	var ids [3]string
	for i, key := range []string{"messageId", "contextId", "taskId"} {
		if ids[i], err = a2aStr(message, key, 128); err != nil {
			return nil, err
		}
	}
	if ids[0] == "" {
		return nil, a2aBad("message.messageId: 필수")
	}
	if message["role"] != "ROLE_USER" {
		return nil, a2aBad("message.role: ROLE_USER")
	}
	if ids[2] != "" {
		row, err := a2aOne(s.pool, p, ids[2])
		if err != nil {
			return nil, err
		}
		if ids[1] != "" && ids[1] != row.context {
			return nil, a2aBad("contextId 가 그 Task 의 것과 다르다")
		}
		return nil, &A2AError{"UNSUPPORTED_OPERATION", "승인 Task 에는 이어서 보낼 수 없다 — 사람이 화면에서 결정한다. 거두려면 CancelTask"}
	}
	fields, err := a2aContent(message)
	if err != nil {
		return nil, err
	}
	str := func(key string) (string, error) {
		raw, has := fields[key]
		if !has || (raw == nil && key == "details") {
			return "", nil
		}
		text, ok := raw.(string)
		if !ok {
			return "", InvalidField(key, "문자열")
		}
		return text, nil
	}
	var texts [3]string
	for i, key := range []string{"title", "question", "details"} {
		if texts[i], err = str(key); err != nil {
			return nil, err
		}
	}
	title, question, details, err := ValidateConfirmation(texts[0], texts[1], texts[2])
	if err != nil {
		return nil, err
	}
	canon, err := EncodeJSON(message)
	if err != nil {
		return nil, err
	}
	return s.withWriteTx(func(tx *sql.Tx) (map[string]any, error) {
		var seen, source string
		err := tx.QueryRow("SELECT id,source_json FROM a2a_task WHERE project_id=? AND callsign=? AND message_id=?", p.ProjectID, p.Callsign, ids[0]).Scan(&seen, &source)
		if err != nil && !errors.Is(err, sql.ErrNoRows) {
			return nil, err
		}
		if err == nil && source != canon {
			return nil, a2aBad("같은 messageId 를 다른 내용으로 다시 보냈다")
		}
		if err != nil {
			requestID, _, err := s.createConfirmation(tx, ctx, p, title, question, details, fields["action"], "")
			if err != nil {
				return nil, err
			}
			if seen, err = a2aRandom("A2A-" + ctx.Now.Format("20060102") + "-"); err != nil {
				return nil, err
			}
			contextID := ids[1]
			if contextID == "" {
				if contextID, err = a2aRandom("CTX-"); err != nil {
					return nil, err
				}
			}
			stored := map[string]any{}
			for k, v := range message {
				stored[k] = v
			}
			stored["taskId"], stored["contextId"] = seen, contextID
			encoded, err := EncodeJSON(stored)
			if err != nil {
				return nil, err
			}
			if _, err := tx.Exec("INSERT INTO a2a_task (project_id,id,context_id,callsign,message_id,request_id,source_json,message_json,created_at) VALUES (?,?,?,?,?,?,?,?,?)",
				p.ProjectID, seen, contextID, p.Callsign, ids[0], requestID, canon, encoded, db.FormatISO(ctx.Now)); err != nil {
				return nil, err
			}
			if err := s.RecordEvent(tx, ctx, &p.ProjectID, "a2a_task", seen, "create", nil, map[string]any{"request_id": requestID, "context_id": contextID}, nil); err != nil {
				return nil, err
			}
		}
		row, err := a2aOne(tx, p, seen)
		if err != nil {
			return nil, err
		}
		return map[string]any{"task": a2aTask(ctx, row, history, true)}, nil
	})
}

// A2ACancel withdraws a pending request and closes its approval record.
func (s *Store) A2ACancel(ctx Ctx, params map[string]any) (map[string]any, error) {
	p, err := NeedCallsign(ctx)
	if err != nil {
		return nil, err
	}
	id, err := a2aStr(params, "id", 256)
	if err != nil {
		return nil, err
	}
	return s.withWriteTx(func(tx *sql.Tx) (map[string]any, error) {
		row, err := a2aOne(tx, p, id)
		if err != nil {
			return nil, err
		}
		if state, _ := row.state(); state != "AUTH_REQUIRED" {
			return nil, &A2AError{"TASK_NOT_CANCELABLE", "이미 끝난 Task 다"}
		}
		now := db.FormatISO(ctx.Now)
		for _, q := range []struct {
			sql  string
			args []any
		}{
			{"UPDATE a2a_task SET canceled_at=? WHERE project_id=? AND id=?", []any{now, p.ProjectID, id}},
			{"UPDATE inbox_message SET state='expired',version=version+1 WHERE project_id=? AND id=?", []any{p.ProjectID, row.request}},
			{"UPDATE approval_grant SET state='rejected',decided_at=? WHERE project_id=? AND id=? AND state='pending'", []any{now, p.ProjectID, row.request}},
		} {
			if _, err := tx.Exec(q.sql, q.args...); err != nil {
				return nil, err
			}
		}
		if err := s.RecordEvent(tx, ctx, &p.ProjectID, "a2a_task", id, "cancel", nil, map[string]any{"request_id": row.request}, nil); err != nil {
			return nil, err
		}
		if row, err = a2aOne(tx, p, id); err != nil {
			return nil, err
		}
		none := 0
		return a2aTask(ctx, row, &none, true), nil
	})
}
