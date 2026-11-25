package store

import (
	"crypto/rand"
	"database/sql"
	"encoding/hex"
	"encoding/json"
	"errors"
	"regexp"
	"time"

	"github.com/ykylee/standard_ai_workflow/hub-go/internal/db"
)

var sessionIDPattern = regexp.MustCompile(`^S-\d{8}-[0-9a-f]{8}$`)

const sessionSignalStale = 15 * time.Minute

func sessionStatus(status, waiting string, lastSignal sql.NullString, now time.Time, openAssignments int) string {
	if status == "ended" {
		return "ended"
	}
	if waiting != "" {
		return "waiting"
	}
	if !lastSignal.Valid {
		return "unknown"
	}
	last, err := time.Parse(time.RFC3339, lastSignal.String)
	if err != nil || now.Sub(last) > sessionSignalStale {
		return "unknown"
	}
	if openAssignments > 0 {
		return "working"
	}
	return "idle"
}

// RegisterSession creates or resumes a harness session from hub_session_start's session object.
func (s *Store) RegisterSession(ctx Ctx, spec map[string]any) (map[string]any, error) {
	p, err := NeedCallsign(ctx)
	if err != nil {
		return nil, err
	}
	allowed := map[string]bool{"harness": true, "harness_session_id": true, "kind": true, "delivery": true, "resume": true, "guide_version": true, "spawn_request": true}
	extra := []string{}
	for key := range spec {
		if !allowed[key] {
			extra = append(extra, "session."+key)
		}
	}
	if len(extra) > 0 {
		return nil, UnknownField(extra)
	}
	if err := ScanSecrets(spec, "session"); err != nil {
		return nil, err
	}
	harness, ok := spec["harness"].(string)
	if !ok || harness == "" {
		return nil, InvalidField("session.harness", "필수 (예: claude-code · codex)")
	}
	harnessSession := ""
	if value, exists := spec["harness_session_id"]; exists {
		var valid bool
		harnessSession, valid = value.(string)
		if !valid || len(harnessSession) > 200 {
			return nil, InvalidField("session.harness_session_id", "200자 이하 문자열")
		}
	}
	kind := "interactive"
	if value, exists := spec["kind"]; exists {
		var valid bool
		kind, valid = value.(string)
		if !valid || (kind != "interactive" && kind != "worker") {
			return nil, InvalidField("session.kind", "interactive · worker 중 하나")
		}
	}
	delivery := []string{"piggyback"}
	if value, exists := spec["delivery"]; exists {
		delivery = nil
		validPaths := map[string]bool{"piggyback": true, "wait": true, "file": true, "adapter": true, "hook": true}
		switch list := value.(type) {
		case []any:
			for _, v := range list {
				path, ok := v.(string)
				if !ok || !validPaths[path] {
					return nil, InvalidField("session.delivery", "piggyback · wait · file · adapter · hook 의 목록")
				}
				delivery = append(delivery, path)
			}
		case []string:
			delivery = append(delivery, list...)
		default:
			return nil, InvalidField("session.delivery", "piggyback · wait · file · adapter · hook 의 목록")
		}
		for _, path := range delivery {
			if !validPaths[path] {
				return nil, InvalidField("session.delivery", "piggyback · wait · file · adapter · hook 의 목록")
			}
		}
	}
	resume := ""
	if value, exists := spec["resume"]; exists && value != nil {
		var valid bool
		resume, valid = value.(string)
		if !valid {
			return nil, InvalidField("session.resume", "문자열 세션 ID 이어야 한다")
		}
	}
	guideVersion, _ := spec["guide_version"].(string)
	var random [4]byte
	if _, err := rand.Read(random[:]); err != nil {
		return nil, err
	}
	newID := "S-" + ctx.Now.Format("20060102") + "-" + hex.EncodeToString(random[:])
	var out map[string]any
	out, err = s.withWriteTx(func(tx *sql.Tx) (map[string]any, error) {
		var existingID string
		if resume != "" {
			if err := s.checkOwnSession(tx, p, resume); err != nil {
				return nil, err
			}
			existingID = resume
		} else if harnessSession != "" {
			err := tx.QueryRow("SELECT id FROM session WHERE project_id=? AND callsign=? AND harness=? AND harness_session_id=? AND status='active'", p.ProjectID, p.Callsign, harness, harnessSession).Scan(&existingID)
			if err != nil && !errors.Is(err, sql.ErrNoRows) {
				return nil, err
			}
		}
		resumed := existingID != ""
		var sid string
		if resumed {
			sid = existingID
			if _, err := tx.Exec("UPDATE session SET last_signal_at=?,delivery_json=?,guide_version=?,idle_waits=0,waiting_since=NULL,version=version+1 WHERE project_id=? AND id=?", db.FormatISO(ctx.Now), MustJSON(delivery), chooseSessionGuideVersion(tx, p.ProjectID, sid, guideVersion), p.ProjectID, sid); err != nil {
				return nil, err
			}
		} else {
			sid = newID
			allowWait := 0
			if kind == "worker" {
				allowWait = 1
			}
			if _, err := tx.Exec("INSERT INTO session (project_id,id,callsign,harness,harness_session_id,kind,allow_wait,delivery_json,guide_version,last_signal_at,started_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)", p.ProjectID, sid, p.Callsign, harness, harnessSession, kind, allowWait, MustJSON(delivery), guideVersion, db.FormatISO(ctx.Now), db.FormatISO(ctx.Now)); err != nil {
				return nil, err
			}
		}
		verb := "start"
		if resumed {
			verb = "resume"
		}
		if err := s.RecordEvent(tx, ctx, &p.ProjectID, "session", sid, verb, nil, map[string]any{"harness": harness, "kind": kind, "delivery": delivery}, nil); err != nil {
			return nil, err
		}
		if value, ok := spec["spawn_request"]; ok && value != nil && !resumed {
			if err := s.LinkSpawnRequest(tx, ctx, p, sid, value); err != nil {
				return nil, err
			}
		}
		view, err := sessionView(tx, p.ProjectID, sid, ctx.Now)
		if err != nil {
			return nil, err
		}
		view["resumed"] = resumed
		return view, nil
	})
	return out, err
}

func chooseSessionGuideVersion(tx *sql.Tx, projectID, sessionID, requested string) string {
	if requested != "" {
		return requested
	}
	var current string
	_ = tx.QueryRow("SELECT guide_version FROM session WHERE project_id=? AND id=?", projectID, sessionID).Scan(&current)
	return current
}

func sessionView(q interface {
	QueryRow(string, ...any) *sql.Row
}, projectID, sessionID string, now time.Time) (map[string]any, error) {
	var callsign, harness, harnessSession, kind, deliveryJSON, status, lastSignal, waiting, started string
	var allowWait int
	err := q.QueryRow(`SELECT callsign, harness, harness_session_id, kind, allow_wait, delivery_json,
		status, last_signal_at, COALESCE(waiting_since, ''), started_at FROM session WHERE project_id=? AND id=?`,
		projectID, sessionID).Scan(&callsign, &harness, &harnessSession, &kind, &allowWait, &deliveryJSON,
		&status, &lastSignal, &waiting, &started)
	if err != nil {
		return nil, err
	}
	var delivery []string
	if err := json.Unmarshal([]byte(deliveryJSON), &delivery); err != nil {
		return nil, err
	}
	var open int
	if err := q.QueryRow(`SELECT COUNT(*) FROM assignment WHERE project_id=? AND session_id=? AND state IN ('offered','accepted')`,
		projectID, sessionID).Scan(&open); err != nil {
		return nil, err
	}
	view := map[string]any{
		"id": sessionID, "callsign": callsign, "harness": harness, "kind": kind, "allow_wait": allowWait != 0,
		"delivery": delivery, "status": sessionStatus(status, waiting, sql.NullString{String: lastSignal, Valid: lastSignal != ""}, now, open),
		"last_signal_at": lastSignal, "open_assignments": open, "started_at": started,
	}
	if harnessSession != "" {
		view["harness_session_id"] = harnessSession
	} else {
		view["harness_session_id"] = nil
	}
	return view, nil
}

func (s *Store) checkOwnSession(tx *sql.Tx, p *Principal, id string) error {
	if !sessionIDPattern.MatchString(id) {
		return InvalidField("session", "S-YYYYMMDD-xxxxxxxx 꼴이어야 한다")
	}
	var owner, status string
	err := tx.QueryRow("SELECT callsign, status FROM session WHERE project_id=? AND id=?", p.ProjectID, id).Scan(&owner, &status)
	if err == sql.ErrNoRows {
		return NotFound("세션이 없다: " + id)
	}
	if err != nil {
		return err
	}
	if owner != p.Callsign {
		return &HubError{Status: 403, Code: "session_not_yours", Message: "이 콜사인의 세션이 아니다", Detail: map[string]any{"session": id}}
	}
	if status == "ended" {
		return &HubError{Status: 410, Code: "session_ended", Message: "끝난 세션이다 — 세션 시작으로 새 세션을 연다", Detail: map[string]any{"session": id}}
	}
	return nil
}

// Signal refreshes a session heartbeat and extends its active orchestrator lease.
func (s *Store) Signal(ctx Ctx, id string) error {
	p, err := NeedCallsign(ctx)
	if err != nil {
		return err
	}
	_, err = s.withWriteTx(func(tx *sql.Tx) (map[string]any, error) {
		if err := s.checkOwnSession(tx, p, id); err != nil {
			return nil, err
		}
		now := db.FormatISO(ctx.Now)
		if _, err := tx.Exec("UPDATE session SET last_signal_at=?, idle_waits=0 WHERE project_id=? AND id=?", now, p.ProjectID, id); err != nil {
			return nil, err
		}
		_, err := tx.Exec("UPDATE orchestrator_lease SET expires_at=? WHERE project_id=? AND session_id=? AND expires_at>?",
			db.FormatISO(ctx.Now.Add(15*time.Minute)), p.ProjectID, id, now)
		return nil, err
	})
	return err
}

// SessionUpdate changes the caller's session settings and records one event.
func (s *Store) SessionUpdate(ctx Ctx, id string, values map[string]any) (map[string]any, error) {
	p, err := NeedCallsign(ctx)
	if err != nil {
		return nil, err
	}
	if len(values) == 0 {
		return nil, InvalidField("session", "고칠 칸이 없다 (kind · allow_wait · delivery · harness_session_id)")
	}
	allowed := map[string]bool{"interactive": true, "worker": true}
	if v, ok := values["kind"]; ok {
		kind, valid := v.(string)
		if !valid || !allowed[kind] {
			return nil, InvalidField("kind", "interactive · worker 중 하나")
		}
	}
	if v, ok := values["allow_wait"]; ok {
		allow, valid := v.(bool)
		if !valid {
			return nil, InvalidField("allow_wait", "boolean 이어야 한다")
		}
		if allow && !(p.CallsignKind == "human" && p.HumanApproved) {
			return nil, Forbidden("대기 도구 켜기는 승인된 human 콜사인만 — 일하는 세션은 kind=worker 로 시작한다")
		}
	}
	if v, ok := values["delivery"]; ok {
		list, valid := v.([]any)
		if !valid {
			if stringsList, ok := v.([]string); ok {
				list = make([]any, len(stringsList))
				for i := range stringsList {
					list[i] = stringsList[i]
				}
				valid = true
			}
		}
		paths := map[string]bool{"piggyback": true, "wait": true, "file": true, "adapter": true, "hook": true}
		if !valid {
			return nil, InvalidField("delivery", "piggyback · wait · file · adapter · hook 의 목록")
		}
		for _, raw := range list {
			path, ok := raw.(string)
			if !ok || !paths[path] {
				return nil, InvalidField("delivery", "piggyback · wait · file · adapter · hook 의 목록")
			}
		}
	}
	if v, ok := values["harness_session_id"]; ok {
		id, valid := v.(string)
		if !valid || len(id) > 200 {
			return nil, InvalidField("harness_session_id", "200자 이하 문자열")
		}
	}
	if err := ScanSecrets(values, ""); err != nil {
		return nil, err
	}
	out, err := s.withWriteTx(func(tx *sql.Tx) (map[string]any, error) {
		if err := s.checkOwnSession(tx, p, id); err != nil {
			return nil, err
		}
		var kind, delivery, harnessSession string
		var allowWait int
		if err := tx.QueryRow("SELECT kind,allow_wait,delivery_json,harness_session_id FROM session WHERE project_id=? AND id=?", p.ProjectID, id).Scan(&kind, &allowWait, &delivery, &harnessSession); err != nil {
			return nil, err
		}
		before := map[string]any{"kind": kind, "allow_wait": allowWait != 0, "delivery_json": delivery, "harness_session_id": harnessSession}
		if v, ok := values["kind"]; ok {
			kind = v.(string)
		}
		if v, ok := values["allow_wait"]; ok {
			if v.(bool) {
				allowWait = 1
			} else {
				allowWait = 0
			}
		}
		if v, ok := values["delivery"]; ok {
			raw, _ := json.Marshal(v)
			delivery = string(raw)
		}
		if v, ok := values["harness_session_id"]; ok {
			harnessSession = v.(string)
		}
		now := db.FormatISO(ctx.Now)
		if _, err := tx.Exec("UPDATE session SET kind=?,allow_wait=?,delivery_json=?,harness_session_id=?,last_signal_at=?,version=version+1 WHERE project_id=? AND id=?", kind, allowWait, delivery, harnessSession, now, p.ProjectID, id); err != nil {
			return nil, err
		}
		after := map[string]any{"kind": kind, "allow_wait": allowWait != 0, "delivery_json": delivery, "harness_session_id": harnessSession}
		if err := s.RecordEvent(tx, ctx, &p.ProjectID, "session", id, "update", before, after, nil); err != nil {
			return nil, err
		}
		view, err := sessionView(tx, p.ProjectID, id, ctx.Now)
		if err != nil {
			return nil, err
		}
		return map[string]any{"session": view}, nil
	})
	return out, err
}

// SessionList returns this project's session snapshots and status counts.
func (s *Store) SessionList(ctx Ctx, callsign, statusFilter string) (map[string]any, error) {
	p, err := NeedReader(ctx)
	if err != nil {
		return nil, err
	}
	query := "SELECT id, callsign FROM session WHERE project_id=?"
	args := []any{p.ProjectID}
	if callsign != "" {
		query += " AND callsign=?"
		args = append(args, callsign)
	}
	query += " ORDER BY started_at, id"
	rows, err := s.pool.Query(query, args...)
	if err != nil {
		return nil, err
	}
	ids := []string{}
	for rows.Next() {
		var id, owner string
		if err := rows.Scan(&id, &owner); err != nil {
			_ = rows.Close()
			return nil, err
		}
		ids = append(ids, id)
	}
	if err := rows.Err(); err != nil {
		_ = rows.Close()
		return nil, err
	}
	if err := rows.Close(); err != nil {
		return nil, err
	}
	views := []map[string]any{}
	counts := map[string]int{}
	for _, id := range ids {
		v, err := sessionView(s.pool, p.ProjectID, id, ctx.Now)
		if err != nil {
			return nil, err
		}
		state := v["status"].(string)
		if statusFilter == "" || statusFilter == state {
			counts[state]++
			views = append(views, v)
		}
	}
	leaseResult, err := s.withWriteTx(func(tx *sql.Tx) (map[string]any, error) {
		return s.orchestratorLease(tx, ctx, p.ProjectID)
	})
	if err != nil {
		return nil, err
	}
	var lease any
	leaseSession := ""
	if leaseResult != nil {
		leaseSession = leaseResult["session_id"].(string)
		lease = map[string]any{"session": leaseSession, "callsign": leaseResult["callsign"], "expires_at": leaseResult["expires_at"], "halted": leaseResult["halted"]}
	}
	for _, v := range views {
		v["orchestrator"] = lease != nil && v["id"] == leaseSession
	}
	unknown := counts["unknown"]
	return map[string]any{"sessions": views, "counts": counts, "unknown": unknown, "orchestrator": lease}, nil
}

// SessionKind returns the registered kind, or "" for an unknown session.
func (s *Store) SessionKind(ctx Ctx, id string) (string, error) {
	p, err := NeedCallsign(ctx)
	if err != nil || id == "" {
		return "", err
	}
	var kind string
	err = s.DB().QueryRow("SELECT kind FROM session WHERE project_id=? AND id=?", p.ProjectID, id).Scan(&kind)
	if errors.Is(err, sql.ErrNoRows) {
		return "", nil
	}
	return kind, err
}
