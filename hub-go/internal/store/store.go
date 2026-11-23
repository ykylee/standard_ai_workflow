package store

import (
	"bytes"
	"context"
	"crypto/rand"
	"crypto/sha256"
	"database/sql"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"regexp"
	"sort"
	"strings"
	"time"
	"unicode/utf8"

	"github.com/ykylee/standard_ai_workflow/hub-go/internal/db"
)

const (
	HubKitVersion = "2.1.0"
	TokenPrefix   = "wfh_"
	TitleMax      = 200
)

var (
	CallsignPattern   = regexp.MustCompile(`^[a-z][a-z0-9-]{1,30}[a-z0-9]$`)
	ReservedCallsigns = map[string]bool{"hub": true}
	TokenShape        = regexp.MustCompile(`wfh_[A-Za-z0-9_-]{20,}`)
	ShaPattern        = regexp.MustCompile(`^[0-9a-f]{7,40}$`)
	ValidStatuses     = map[string]bool{"planned": true, "in_progress": true, "blocked": true, "done": true}
	ValidPriorities   = map[string]bool{"high": true, "medium": true, "low": true}
	TaskFieldKeys     = map[string]bool{
		"affected_documents": true,
		"done_criteria":      true,
		"result":             true,
		"risks":              true,
		"follow_up":          true,
		"validation_result":  true,
		"next_step":          true,
	}
)

type Principal struct {
	Kind          string
	ProjectID     string
	Callsign      string
	CallsignKind  string
	HumanApproved bool
	Role          string
	Name          string
}

type Ctx struct {
	Now           time.Time
	Via           string
	Principal     *Principal
	ClientVersion string
	PublicURL     string
}

func HashToken(token string) string {
	sum := sha256.Sum256([]byte(token))
	return hex.EncodeToString(sum[:])
}

func NewToken() (string, error) {
	var buf [32]byte
	if _, err := rand.Read(buf[:]); err != nil {
		return "", err
	}
	return TokenPrefix + base64.RawURLEncoding.EncodeToString(buf[:]), nil
}

func EncodeJSON(v any) (string, error) {
	var buf bytes.Buffer
	enc := json.NewEncoder(&buf)
	enc.SetEscapeHTML(false)
	if err := enc.Encode(v); err != nil {
		return "", err
	}
	return strings.TrimRight(buf.String(), "\n"), nil
}

func MustJSON(v any) string {
	s, err := EncodeJSON(v)
	if err != nil {
		return "{}"
	}
	return s
}

func ScanSecrets(value any, p string) error {
	switch val := value.(type) {
	case string:
		if TokenShape.MatchString(val) {
			where := p
			if where == "" {
				where = "값"
			}
			return &HubError{
				Status:  400,
				Code:    "secret_in_payload",
				Message: "토큰으로 보이는 문자열이 있다: " + where,
				Detail:  map[string]any{"field": p},
			}
		}
	case map[string]any:
		keys := make([]string, 0, len(val))
		for k := range val {
			keys = append(keys, k)
		}
		sort.Strings(keys)
		for _, k := range keys {
			next := k
			if p != "" {
				next = p + "." + k
			}
			if err := ScanSecrets(val[k], next); err != nil {
				return err
			}
		}
	case map[string]string:
		keys := make([]string, 0, len(val))
		for k := range val {
			keys = append(keys, k)
		}
		sort.Strings(keys)
		for _, k := range keys {
			next := k
			if p != "" {
				next = p + "." + k
			}
			if err := ScanSecrets(val[k], next); err != nil {
				return err
			}
		}
	case []any:
		for i, item := range val {
			if err := ScanSecrets(item, fmt.Sprintf("%s[%d]", p, i)); err != nil {
				return err
			}
		}
	case []string:
		for i, item := range val {
			if err := ScanSecrets(item, fmt.Sprintf("%s[%d]", p, i)); err != nil {
				return err
			}
		}
	}
	return nil
}

func AsHubError(err error) (*HubError, bool) {
	if err == nil {
		return nil, false
	}
	var he *HubError
	if errors.As(err, &he) {
		return he, true
	}
	var de *db.Error
	if errors.As(err, &de) {
		return &HubError{Status: de.Status, Code: de.Code, Message: de.Message, Detail: de.Detail}, true
	}
	return nil, false
}

type Store struct {
	Path string
	pool *sql.DB
}

func New(dbPath string) (*Store, error) {
	conn, err := db.Connect(dbPath)
	if err != nil {
		return nil, err
	}
	return &Store{Path: dbPath, pool: conn}, nil
}

func (s *Store) Close() error {
	if s.pool != nil {
		return s.pool.Close()
	}
	return nil
}

func (s *Store) DBVersion() (int, error) {
	return db.SchemaVersion(s.pool)
}

// DB returns the underlying database handle for sibling packages (e.g. tools judge queries).
func (s *Store) DB() *sql.DB {
	return s.pool
}

// WriteTx runs fn inside a database write transaction with rollback on error.
func (s *Store) WriteTx(fn func(tx *sql.Tx) (map[string]any, error)) (map[string]any, error) {
	return s.withWriteTx(fn)
}

type queryExec interface {
	Exec(query string, args ...any) (sql.Result, error)
	Query(query string, args ...any) (*sql.Rows, error)
	QueryRow(query string, args ...any) *sql.Row
}

func (s *Store) withWriteTx(fn func(tx *sql.Tx) (map[string]any, error)) (map[string]any, error) {
	tx, err := s.pool.BeginTx(context.Background(), nil)
	if err != nil {
		return nil, err
	}
	out, err := fn(tx)
	if err != nil {
		_ = tx.Rollback()
		return nil, err
	}
	if err := tx.Commit(); err != nil {
		return nil, err
	}
	return out, nil
}

func (s *Store) RecordEvent(qe queryExec, ctx Ctx, projectID *string, targetKind, targetID, op string, before, after any, callsignOverride *string) error {
	var who any
	if callsignOverride != nil {
		who = *callsignOverride
	} else if ctx.Principal != nil && ctx.Principal.Callsign != "" {
		who = ctx.Principal.Callsign
	}
	var pidArg any
	if projectID != nil && *projectID != "" {
		pidArg = *projectID
	}
	var beforeArg, afterArg any
	if before != nil {
		beforeArg = MustJSON(before)
	}
	if after != nil {
		afterArg = MustJSON(after)
	}
	var cvArg any
	if ctx.ClientVersion != "" {
		cvArg = ctx.ClientVersion
	}
	_, err := qe.Exec(
		`INSERT INTO event (project_id, at, callsign, target_kind, target_id, op, before_json, after_json, via, client_version) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
		pidArg, db.FormatISO(ctx.Now), who, targetKind, targetID, op, beforeArg, afterArg, ctx.Via, cvArg,
	)
	return err
}

func (s *Store) Idempotent(ctx Ctx, requestID string, fn func(tx *sql.Tx) (map[string]any, error)) (map[string]any, error) {
	return s.withWriteTx(func(tx *sql.Tx) (map[string]any, error) {
		p := ctx.Principal
		if requestID != "" && p != nil && p.ProjectID != "" && p.Callsign != "" {
			var resJSON string
			err := tx.QueryRow(
				"SELECT result_json FROM applied_request WHERE project_id = ? AND callsign = ? AND request_id = ?",
				p.ProjectID, p.Callsign, requestID,
			).Scan(&resJSON)
			if err == nil {
				var replayed map[string]any
				if jErr := json.Unmarshal([]byte(resJSON), &replayed); jErr != nil {
					return nil, jErr
				}
				replayed["replayed"] = true
				return replayed, nil
			}
			if !errors.Is(err, sql.ErrNoRows) {
				return nil, err
			}
		}

		res, err := fn(tx)
		if err != nil {
			return nil, err
		}

		if requestID != "" && p != nil && p.ProjectID != "" && p.Callsign != "" {
			if _, err := tx.Exec(
				"INSERT INTO applied_request (project_id, callsign, request_id, result_json, at) VALUES (?, ?, ?, ?, ?)",
				p.ProjectID, p.Callsign, requestID, MustJSON(res), db.FormatISO(ctx.Now),
			); err != nil {
				return nil, err
			}
		}
		return res, nil
	})
}

func (s *Store) Authenticate(token string, now *time.Time, clientVersion string) (*Principal, error) {
	if token == "" {
		return nil, nil
	}
	h := HashToken(token)
	var pid, id, kind, role string
	var approved int
	err := s.pool.QueryRow(
		"SELECT project_id, id, kind, human_approved, role FROM callsign WHERE token_hash = ? AND revoked_at IS NULL",
		h,
	).Scan(&pid, &id, &kind, &approved, &role)
	if err == nil {
		if now != nil {
			if _, err := s.pool.Exec("UPDATE callsign SET last_seen_at = ? WHERE project_id = ? AND id = ?", db.FormatISO(*now), pid, id); err != nil {
				return nil, err
			}
		}
		if clientVersion != "" {
			cv := clientVersion
			if len([]rune(cv)) > 80 {
				cv = string([]rune(cv)[:80])
			}
			if _, err := s.pool.Exec("UPDATE callsign SET client_version_seen = ? WHERE project_id = ? AND id = ?", cv, pid, id); err != nil {
				return nil, err
			}
		}
		return &Principal{
			Kind:          "callsign",
			ProjectID:     pid,
			Callsign:      id,
			CallsignKind:  kind,
			HumanApproved: approved != 0,
			Role:          role,
		}, nil
	}
	if !errors.Is(err, sql.ErrNoRows) {
		return nil, err
	}

	var hubRole, hubName string
	err = s.pool.QueryRow(
		"SELECT role, name FROM hub_token WHERE token_hash = ? AND revoked_at IS NULL",
		h,
	).Scan(&hubRole, &hubName)
	if err == nil {
		return &Principal{Kind: hubRole, Name: hubName}, nil
	}
	if errors.Is(err, sql.ErrNoRows) {
		return nil, nil
	}
	return nil, err
}

func (s *Store) WebPrincipal(name string) (*Principal, error) {
	var found string
	err := s.pool.QueryRow("SELECT name FROM hub_token WHERE name = ? AND role = 'web' AND revoked_at IS NULL", name).Scan(&found)
	if errors.Is(err, sql.ErrNoRows) {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	return &Principal{Kind: "web", Name: found}, nil
}

func (s *Store) IssueHubToken(role, name string, now time.Time) (string, error) {
	if role != "web" && role != "admin" {
		return "", InvalidField("role", "web · admin 가운데 하나")
	}
	token, err := NewToken()
	if err != nil {
		return "", err
	}
	_, err = s.withWriteTx(func(tx *sql.Tx) (map[string]any, error) {
		var dummy int
		err := tx.QueryRow("SELECT 1 FROM hub_token WHERE name = ?", name).Scan(&dummy)
		if err == nil {
			return nil, &HubError{Status: 409, Code: "token_name_taken", Message: "이미 쓰는 토큰 이름이다: " + name}
		}
		if !errors.Is(err, sql.ErrNoRows) {
			return nil, err
		}
		if _, err := tx.Exec(
			"INSERT INTO hub_token (token_hash, role, name, created_at) VALUES (?, ?, ?, ?)",
			HashToken(token), role, name, db.FormatISO(now),
		); err != nil {
			return nil, err
		}
		hubCS := "hub"
		if err := s.RecordEvent(tx, Ctx{Now: now, Via: "admin"}, nil, "hub_token", name, "issue", nil, map[string]any{"role": role}, &hubCS); err != nil {
			return nil, err
		}
		return nil, nil
	})
	if err != nil {
		return "", err
	}
	return token, nil
}

func (s *Store) RevokeHubToken(name string, now time.Time) error {
	_, err := s.withWriteTx(func(tx *sql.Tx) (map[string]any, error) {
		res, err := tx.Exec("UPDATE hub_token SET revoked_at = ? WHERE name = ? AND revoked_at IS NULL", db.FormatISO(now), name)
		if err != nil {
			return nil, err
		}
		n, _ := res.RowsAffected()
		if n == 0 {
			return nil, NotFound("거둘 토큰이 없다: " + name)
		}
		hubCS := "hub"
		if err := s.RecordEvent(tx, Ctx{Now: now, Via: "admin"}, nil, "hub_token", name, "revoke", nil, nil, &hubCS); err != nil {
			return nil, err
		}
		return nil, nil
	})
	return err
}

func (s *Store) ProjectMoved(projectID string) (string, error) {
	if projectID == "" {
		return "", nil
	}
	var raw string
	err := s.pool.QueryRow("SELECT settings_json FROM project WHERE id = ?", projectID).Scan(&raw)
	if errors.Is(err, sql.ErrNoRows) {
		return "", nil
	}
	if err != nil {
		return "", err
	}
	var settings map[string]any
	if err := json.Unmarshal([]byte(raw), &settings); err != nil {
		return "", nil
	}
	if moved, ok := settings["moved"].(map[string]any); ok {
		if to, ok := moved["to"].(string); ok && to != "" {
			return to, nil
		}
	}
	return "", nil
}

func (s *Store) LookupProject(remoteURL string) (map[string]any, error) {
	key, err := NormalizeGitRemote(remoteURL)
	if err != nil {
		return nil, err
	}
	var pid, dname string
	err = s.pool.QueryRow(
		"SELECT p.id, p.display_name FROM project_alias a JOIN project p ON p.id = a.project_id WHERE a.key = ?",
		key,
	).Scan(&pid, &dname)
	if errors.Is(err, sql.ErrNoRows) {
		return map[string]any{"key": key, "project_id": nil, "display_name": nil}, nil
	}
	if err != nil {
		return nil, err
	}
	out := map[string]any{"key": key, "project_id": pid, "display_name": dname}
	to, err := s.ProjectMoved(pid)
	if err != nil {
		return nil, err
	}
	if to != "" {
		out["moved_to"] = to
	}
	return out, nil
}

func CheckCallsign(callsign, kind string) error {
	if ReservedCallsigns[callsign] {
		return InvalidField("callsign", fmt.Sprintf("예약한 이름이다: '%s'", callsign))
	}
	if !CallsignPattern.MatchString(callsign) {
		return InvalidField("callsign", "소문자 · 숫자 · '-' 3~32 자, 글자로 시작하고 '-' 로 끝나지 않는다 (예: claude-macmini)")
	}
	if kind != "human" && kind != "agent" {
		return InvalidField("kind", "human · agent 가운데 하나")
	}
	return nil
}

func (s *Store) RegisterProject(ctx Ctx, remoteURL, displayName, callsign, kind, label, host string) (map[string]any, error) {
	local := strings.TrimSpace(remoteURL) == ""
	var key string
	var err error
	if local {
		key, err = LocalKey()
	} else {
		key, err = NormalizeGitRemote(remoteURL)
	}
	if err != nil {
		return nil, err
	}
	if err := CheckCallsign(callsign, kind); err != nil {
		return nil, err
	}
	if strings.TrimSpace(displayName) == "" {
		return nil, InvalidField("display_name", "비었다")
	}
	token, err := NewToken()
	if err != nil {
		return nil, err
	}
	var rnd [4]byte
	if _, err := rand.Read(rnd[:]); err != nil {
		return nil, err
	}
	projectID := fmt.Sprintf("P-%s-%s", ctx.Now.Format("20060102"), hex.EncodeToString(rnd[:]))

	return s.withWriteTx(func(tx *sql.Tx) (map[string]any, error) {
		var existingPID string
		err := tx.QueryRow("SELECT project_id FROM project_alias WHERE key = ?", key).Scan(&existingPID)
		if err == nil {
			return nil, &HubError{
				Status:  409,
				Code:    "project_exists",
				Message: "이미 등록된 프로젝트다 — hub_callsign_register 로 합류한다",
				Detail:  map[string]any{"project_id": existingPID, "key": key},
			}
		}
		if !errors.Is(err, sql.ErrNoRows) {
			return nil, err
		}
		nowISO := db.FormatISO(ctx.Now)
		dn := strings.TrimSpace(displayName)
		if _, err := tx.Exec("INSERT INTO project (id, display_name, owner_callsign, created_at) VALUES (?, ?, ?, ?)", projectID, dn, callsign, nowISO); err != nil {
			return nil, err
		}
		if _, err := tx.Exec("INSERT INTO project_alias (key, project_id, kind, added_by, added_at) VALUES (?, ?, 'primary', ?, ?)", key, projectID, callsign, nowISO); err != nil {
			return nil, err
		}
		approved := 0
		if kind == "human" {
			approved = 1
		}
		if _, err := tx.Exec(
			"INSERT INTO callsign (project_id, id, kind, human_approved, role, label, host, token_hash, created_at) VALUES (?, ?, ?, ?, 'owner', ?, ?, ?, ?)",
			projectID, callsign, kind, approved, label, host, HashToken(token), nowISO,
		); err != nil {
			return nil, err
		}
		if err := s.RecordEvent(tx, ctx, &projectID, "project", projectID, "register", nil,
			map[string]any{"key": key, "display_name": dn, "owner": callsign}, &callsign); err != nil {
			return nil, err
		}
		if err := s.RecordEvent(tx, ctx, &projectID, "callsign", callsign, "register", nil,
			map[string]any{"kind": kind, "role": "owner"}, &callsign); err != nil {
			return nil, err
		}
		out := map[string]any{
			"project_id": projectID,
			"key":        key,
			"callsign":   callsign,
			"role":       "owner",
			"token":      token,
		}
		if local {
			out["local_key"] = true
			out["next"] = "원격이 없어 로컬 키로 등록했다 — 주소 조회로는 찾을 수 없다. git 원격을 만든 뒤 hub_project_bind_remote(remote_url) 로 묶어야 다른 환경이 합류한다"
		}
		return out, nil
	})
}

func (s *Store) BindRemote(ctx Ctx, remoteURL string) (map[string]any, error) {
	p, err := NeedCallsign(ctx)
	if err != nil {
		return nil, err
	}
	if p.Role != "owner" || p.CallsignKind != "human" || !p.HumanApproved {
		return nil, Forbidden("원격 묶기는 승인된 human 소유자만 한다")
	}
	key, err := NormalizeGitRemote(remoteURL)
	if err != nil {
		return nil, err
	}
	return s.withWriteTx(func(tx *sql.Tx) (map[string]any, error) {
		var existingPID string
		err := tx.QueryRow("SELECT project_id FROM project_alias WHERE key = ?", key).Scan(&existingPID)
		if err == nil {
			if existingPID == p.ProjectID {
				return map[string]any{"project_id": p.ProjectID, "key": key, "already": true}, nil
			}
			return nil, &HubError{
				Status:  409,
				Code:    "alias_taken",
				Message: "다른 프로젝트가 이 저장소 주소로 등록돼 있다 — 묶지 않는다. 두 프로젝트를 합치는 길은 없다: 사람이 어느 쪽을 쓸지 정한다",
				Detail:  map[string]any{"key": key},
			}
		}
		if !errors.Is(err, sql.ErrNoRows) {
			return nil, err
		}
		if _, err := tx.Exec(
			"INSERT INTO project_alias (key, project_id, kind, added_by, added_at) VALUES (?, ?, 'alias', ?, ?)",
			key, p.ProjectID, p.Callsign, db.FormatISO(ctx.Now),
		); err != nil {
			return nil, err
		}
		if err := s.RecordEvent(tx, ctx, &p.ProjectID, "project", p.ProjectID, "bind_remote", nil, map[string]any{"key": key}, &p.Callsign); err != nil {
			return nil, err
		}
		return map[string]any{"project_id": p.ProjectID, "key": key, "already": false}, nil
	})
}

func (s *Store) RegisterCallsign(ctx Ctx, projectID, callsign, kind, label, host string) (map[string]any, error) {
	if err := CheckCallsign(callsign, kind); err != nil {
		return nil, err
	}
	token, err := NewToken()
	if err != nil {
		return nil, err
	}
	return s.withWriteTx(func(tx *sql.Tx) (map[string]any, error) {
		var dummy int
		err := tx.QueryRow("SELECT 1 FROM project WHERE id = ?", projectID).Scan(&dummy)
		if errors.Is(err, sql.ErrNoRows) {
			return nil, NotFound("프로젝트가 없다: " + projectID)
		}
		if err != nil {
			return nil, err
		}
		var revoked sql.NullString
		err = tx.QueryRow("SELECT revoked_at FROM callsign WHERE project_id = ? AND id = ?", projectID, callsign).Scan(&revoked)
		if err == nil {
			if !revoked.Valid {
				return nil, &HubError{
					Status:  409,
					Code:    "callsign_taken",
					Message: fmt.Sprintf("이미 쓰는 콜사인이다: %s — 그 환경의 .workflow-hub/env 를 찾거나 다른 이름을 쓴다", callsign),
					Detail:  map[string]any{"callsign": callsign},
				}
			}
			if _, err := tx.Exec("DELETE FROM callsign WHERE project_id = ? AND id = ?", projectID, callsign); err != nil {
				return nil, err
			}
		} else if !errors.Is(err, sql.ErrNoRows) {
			return nil, err
		}

		if _, err := tx.Exec(
			"INSERT INTO callsign (project_id, id, kind, human_approved, role, label, host, token_hash, created_at) VALUES (?, ?, ?, 0, 'editor', ?, ?, ?, ?)",
			projectID, callsign, kind, label, host, HashToken(token), db.FormatISO(ctx.Now),
		); err != nil {
			return nil, err
		}
		if err := s.RecordEvent(tx, ctx, &projectID, "callsign", callsign, "register", nil,
			map[string]any{"kind": kind, "role": "editor"}, &callsign); err != nil {
			return nil, err
		}
		return map[string]any{
			"project_id":    projectID,
			"callsign":      callsign,
			"role":          "editor",
			"token":         token,
			"human_pending": kind == "human",
		}, nil
	})
}

func (s *Store) ApproveCallsign(ctx Ctx, callsign string) (map[string]any, error) {
	p, err := NeedCallsign(ctx)
	if err != nil {
		return nil, err
	}
	if p.Role != "owner" || p.CallsignKind != "human" || !p.HumanApproved {
		return nil, Forbidden("콜사인 승인은 승인된 human 소유자만 한다")
	}
	return s.withWriteTx(func(tx *sql.Tx) (map[string]any, error) {
		var kind string
		var approved int
		err := tx.QueryRow("SELECT kind, human_approved FROM callsign WHERE project_id = ? AND id = ? AND revoked_at IS NULL",
			p.ProjectID, callsign).Scan(&kind, &approved)
		if errors.Is(err, sql.ErrNoRows) {
			return nil, NotFound("콜사인이 없다: " + callsign)
		}
		if err != nil {
			return nil, err
		}
		if kind != "human" {
			return nil, InvalidField("callsign", "agent 콜사인은 승인 대상이 아니다")
		}
		if approved != 0 {
			return map[string]any{"callsign": callsign, "human_approved": true, "changed": false}, nil
		}
		if _, err := tx.Exec("UPDATE callsign SET human_approved = 1, version = version + 1 WHERE project_id = ? AND id = ?",
			p.ProjectID, callsign); err != nil {
			return nil, err
		}
		if err := s.RecordEvent(tx, ctx, &p.ProjectID, "callsign", callsign, "approve",
			map[string]any{"human_approved": false}, map[string]any{"human_approved": true}, nil); err != nil {
			return nil, err
		}
		return map[string]any{"callsign": callsign, "human_approved": true, "changed": true}, nil
	})
}

func (s *Store) RevokeCallsign(ctx Ctx, projectID, callsign string) (map[string]any, error) {
	return s.withWriteTx(func(tx *sql.Tx) (map[string]any, error) {
		nowISO := db.FormatISO(ctx.Now)
		res, err := tx.Exec(
			"UPDATE callsign SET revoked_at = ?, version = version + 1 WHERE project_id = ? AND id = ? AND revoked_at IS NULL",
			nowISO, projectID, callsign,
		)
		if err != nil {
			return nil, err
		}
		n, _ := res.RowsAffected()
		if n == 0 {
			return nil, NotFound(fmt.Sprintf("거둘 콜사인이 없다: %s/%s", projectID, callsign))
		}
		rows, err := tx.Query("SELECT id FROM task WHERE project_id = ? AND assignee = ? AND status != 'done'", projectID, callsign)
		if err != nil {
			return nil, err
		}
		released := make([]string, 0)
		for rows.Next() {
			var tid string
			if err := rows.Scan(&tid); err != nil {
				rows.Close()
				return nil, err
			}
			released = append(released, tid)
		}
		rows.Close()
		hubCS := "hub"
		for _, tid := range released {
			if _, err := tx.Exec(
				"UPDATE task SET assignee = NULL, version = version + 1, updated_at = ? WHERE project_id = ? AND id = ?",
				nowISO, projectID, tid,
			); err != nil {
				return nil, err
			}
			if err := s.RecordEvent(tx, ctx, &projectID, "task", tid, "release",
				map[string]any{"assignee": callsign}, map[string]any{"assignee": nil}, &hubCS); err != nil {
				return nil, err
			}
		}
		if err := s.RecordEvent(tx, ctx, &projectID, "callsign", callsign, "revoke", nil,
			map[string]any{"released_tasks": released}, &hubCS); err != nil {
			return nil, err
		}
		return map[string]any{"callsign": callsign, "released_tasks": released}, nil
	})
}

func NeedCallsign(ctx Ctx) (*Principal, error) {
	p := ctx.Principal
	if p == nil || p.Kind != "callsign" || p.ProjectID == "" || p.Callsign == "" {
		return nil, Forbidden("콜사인 토큰이 필요하다")
	}
	return p, nil
}

func NeedReader(ctx Ctx) (*Principal, error) {
	p := ctx.Principal
	if p == nil || (p.Kind != "callsign" && p.Kind != "viewer") || p.ProjectID == "" {
		return nil, Forbidden("콜사인 토큰이 필요하다")
	}
	return p, nil
}

type taskScanner interface {
	Scan(dest ...any) error
}

func scanTaskRow(row taskScanner) (map[string]any, error) {
	var pid, id, title, status, priority, branch, wbs, wbsReason, desc, planMD, fieldsJSON, progNote, createdBy, createdAt, updatedAt string
	var assignee, progAt sql.NullString
	var version int
	err := row.Scan(
		&pid, &id, &title, &status, &priority, &assignee, &branch, &wbs, &wbsReason,
		&desc, &planMD, &fieldsJSON, &progNote, &progAt, &createdBy, &createdAt, &updatedAt, &version,
	)
	if err != nil {
		return nil, err
	}
	var assigneeVal any
	if assignee.Valid {
		assigneeVal = assignee.String
	}
	var progAtVal any
	if progAt.Valid {
		progAtVal = progAt.String
	}
	fields := map[string]any{}
	if fieldsJSON != "" {
		if err := json.Unmarshal([]byte(fieldsJSON), &fields); err != nil {
			return nil, err
		}
	}
	return map[string]any{
		"project_id":        pid,
		"id":                id,
		"title":             title,
		"status":            status,
		"priority":          priority,
		"assignee":          assigneeVal,
		"branch":            branch,
		"wbs":               wbs,
		"wbs_exempt_reason": wbsReason,
		"description":       desc,
		"plan_md":           planMD,
		"fields":            fields,
		"progress_note":     progNote,
		"progress_at":       progAtVal,
		"created_by":        createdBy,
		"created_at":        createdAt,
		"updated_at":        updatedAt,
		"version":           version,
	}, nil
}

const taskSelectCols = "project_id, id, title, status, priority, assignee, branch, wbs, wbs_exempt_reason, description, plan_md, fields_json, progress_note, progress_at, created_by, created_at, updated_at, version"

func (s *Store) GetTask(qe queryExec, projectID, taskID string) (map[string]any, error) {
	row := qe.QueryRow("SELECT "+taskSelectCols+" FROM task WHERE project_id = ? AND id = ?", projectID, taskID)
	t, err := scanTaskRow(row)
	if errors.Is(err, sql.ErrNoRows) {
		return nil, NotFound("task 가 없다: " + taskID)
	}
	if err != nil {
		return nil, err
	}
	return t, nil
}

func ValidateTaskFields(values map[string]any) error {
	if rawTitle, has := values["title"]; has {
		title, ok := rawTitle.(string)
		if !ok || strings.TrimSpace(title) == "" {
			return InvalidField("title", "비었다")
		}
		if rc := utf8.RuneCountInString(title); rc > TitleMax {
			return InvalidField("title", fmt.Sprintf("String should have at most %d characters (지금 %d)", TitleMax, rc))
		}
	}
	if rawStatus, has := values["status"]; has {
		st, ok := rawStatus.(string)
		if !ok || !ValidStatuses[st] {
			return InvalidField("status", "planned · in_progress · blocked · done 가운데 하나")
		}
		if st == "done" {
			return &HubError{
				Status:  422,
				Code:    "gate_denied",
				Message: "done 은 done 게이트를 거치는 hub_task_close 로만 닫는다",
				Detail:  map[string]any{"kit_error_code": "done_requires_gate"},
			}
		}
	}
	if rawPrio, has := values["priority"]; has {
		pr, ok := rawPrio.(string)
		if !ok || !ValidPriorities[pr] {
			return InvalidField("priority", "high · medium · low 가운데 하나")
		}
	}
	if rawFields, has := values["fields"]; has && rawFields != nil {
		fm, ok := rawFields.(map[string]any)
		if !ok {
			return InvalidField("fields", "객체여야 한다")
		}
		var extra []string
		for k := range fm {
			if !TaskFieldKeys[k] {
				extra = append(extra, k)
			}
		}
		if len(extra) > 0 {
			sort.Strings(extra)
			return &HubError{
				Status:  400,
				Code:    "unknown_field",
				Message: "fields 의 모르는 칸: " + strings.Join(extra, ", "),
				Detail:  map[string]any{"fields": extra},
			}
		}
	}
	for _, k := range []string{"branch", "wbs", "wbs_exempt_reason", "description", "plan_md"} {
		if raw, has := values[k]; has {
			if _, ok := raw.(string); !ok {
				return InvalidField(k, "문자열이어야 한다")
			}
		}
	}
	return nil
}

type PrepareCreateFn func(tx *sql.Tx, projectID, taskID string, values map[string]any) (map[string]any, error)
type PrepareUpdateFn func(tx *sql.Tx, before, values map[string]any) (map[string]any, error)

func strVal(m map[string]any, key, def string) string {
	if raw, ok := m[key]; ok && raw != nil {
		if s, ok := raw.(string); ok {
			return s
		}
	}
	return def
}

func (s *Store) TaskCreate(ctx Ctx, values map[string]any, requestID string, prepare PrepareCreateFn) (map[string]any, error) {
	p, err := NeedCallsign(ctx)
	if err != nil {
		return nil, err
	}
	if err := ScanSecrets(values, ""); err != nil {
		return nil, err
	}
	if _, has := values["title"]; !has {
		return nil, InvalidField("title", "필수")
	}
	if err := ValidateTaskFields(values); err != nil {
		return nil, err
	}
	date := ctx.Now.Format("2006-01-02")
	pid, cs := p.ProjectID, p.Callsign

	return s.Idempotent(ctx, requestID, func(tx *sql.Tx) (map[string]any, error) {
		var next int
		err := tx.QueryRow("SELECT next FROM task_seq WHERE project_id = ? AND date = ? AND namespace = ?", pid, date, cs).Scan(&next)
		if errors.Is(err, sql.ErrNoRows) {
			next = 1
		} else if err != nil {
			return nil, err
		}
		if _, err := tx.Exec(
			"INSERT INTO task_seq (project_id, date, namespace, next) VALUES (?, ?, ?, ?) ON CONFLICT(project_id, date, namespace) DO UPDATE SET next = excluded.next",
			pid, date, cs, next+1,
		); err != nil {
			return nil, err
		}
		taskID := fmt.Sprintf("TASK-%s-%s-%03d", date, cs, next)
		vals := values
		if prepare != nil {
			vals, err = prepare(tx, pid, taskID, values)
			if err != nil {
				return nil, err
			}
		}
		fieldsMap := map[string]any{}
		if rawFields, ok := vals["fields"].(map[string]any); ok && rawFields != nil {
			fieldsMap = rawFields
		}
		nowISO := db.FormatISO(ctx.Now)
		if _, err := tx.Exec(
			"INSERT INTO task (project_id, id, title, status, priority, branch, wbs, wbs_exempt_reason, description, plan_md, fields_json, created_by, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
			pid, taskID, strings.TrimSpace(strVal(vals, "title", "")), strVal(vals, "status", "planned"),
			strVal(vals, "priority", "high"), strVal(vals, "branch", ""), strVal(vals, "wbs", ""),
			strVal(vals, "wbs_exempt_reason", ""), strVal(vals, "description", ""), strVal(vals, "plan_md", ""),
			MustJSON(fieldsMap), cs, nowISO, nowISO,
		); err != nil {
			return nil, err
		}
		task, err := s.GetTask(tx, pid, taskID)
		if err != nil {
			return nil, err
		}
		if err := s.RecordEvent(tx, ctx, &pid, "task", taskID, "create", nil, task, nil); err != nil {
			return nil, err
		}
		return map[string]any{"task": task}, nil
	})
}

func (s *Store) TaskGet(ctx Ctx, taskID string) (map[string]any, error) {
	p, err := NeedReader(ctx)
	if err != nil {
		return nil, err
	}
	task, err := s.GetTask(s.pool, p.ProjectID, taskID)
	if err != nil {
		return nil, err
	}
	rows, err := s.pool.Query("SELECT sha, branch, added_by, added_at FROM task_commit WHERE project_id = ? AND task_id = ? ORDER BY added_at",
		p.ProjectID, taskID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	commits := make([]map[string]any, 0)
	for rows.Next() {
		var sha, branch, addedBy, addedAt string
		if err := rows.Scan(&sha, &branch, &addedBy, &addedAt); err != nil {
			return nil, err
		}
		commits = append(commits, map[string]any{
			"sha":      sha,
			"branch":   branch,
			"added_by": addedBy,
			"added_at": addedAt,
		})
	}
	task["commits"] = commits
	return map[string]any{"task": task}, nil
}

func (s *Store) TaskList(ctx Ctx, status *string, assignee *string, limit int, newestFirst bool) (map[string]any, error) {
	p, err := NeedReader(ctx)
	if err != nil {
		return nil, err
	}
	if status != nil && !ValidStatuses[*status] {
		return nil, InvalidField("status", "planned · in_progress · blocked · done 가운데 하나")
	}
	if limit < 1 || limit > 500 {
		return nil, InvalidField("limit", "1~500")
	}
	sqlStr := "SELECT " + taskSelectCols + " FROM task WHERE project_id = ?"
	args := []any{p.ProjectID}
	if status != nil {
		sqlStr += " AND status = ?"
		args = append(args, *status)
	}
	if assignee != nil {
		if *assignee == "" {
			sqlStr += " AND assignee IS NULL"
		} else {
			sqlStr += " AND assignee = ?"
			args = append(args, *assignee)
		}
	}
	if newestFirst {
		sqlStr += " ORDER BY created_at DESC, id DESC LIMIT ?"
	} else {
		sqlStr += " ORDER BY created_at, id LIMIT ?"
	}
	args = append(args, limit)
	rows, err := s.pool.Query(sqlStr, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	tasks := make([]map[string]any, 0)
	for rows.Next() {
		t, err := scanTaskRow(rows)
		if err != nil {
			return nil, err
		}
		tasks = append(tasks, t)
	}
	return map[string]any{"tasks": tasks}, nil
}

type mutateFn func(before map[string]any, p *Principal, tx *sql.Tx) (map[string]any, error)

func (s *Store) versionedUpdateIn(tx *sql.Tx, ctx Ctx, p *Principal, taskID string, expectedVersion *int, op string, mutate mutateFn) (map[string]any, error) {
	pid := p.ProjectID
	before, err := s.GetTask(tx, pid, taskID)
	if err != nil {
		return nil, err
	}
	curVer := before["version"].(int)
	if expectedVersion != nil && curVer != *expectedVersion {
		return nil, VersionConflict(curVer, before)
	}
	changes, err := mutate(before, p, tx)
	if err != nil {
		return nil, err
	}
	if len(changes) == 0 {
		return map[string]any{"task": before, "changed": false}, nil
	}
	keys := make([]string, 0, len(changes))
	for k := range changes {
		keys = append(keys, k)
	}
	sort.Strings(keys)

	sets := make([]string, len(keys))
	vals := make([]any, 0, len(keys)+4)
	for i, k := range keys {
		sets[i] = k + " = ?"
		if k == "fields_json" {
			vals = append(vals, MustJSON(changes[k]))
		} else {
			vals = append(vals, changes[k])
		}
	}
	vals = append(vals, db.FormatISO(ctx.Now), pid, taskID, curVer)
	sqlStr := fmt.Sprintf("UPDATE task SET %s, version = version + 1, updated_at = ? WHERE project_id = ? AND id = ? AND version = ?",
		strings.Join(sets, ", "))
	res, err := tx.Exec(sqlStr, vals...)
	if err != nil {
		return nil, err
	}
	aff, _ := res.RowsAffected()
	if aff != 1 {
		return nil, VersionConflict(curVer, before)
	}
	after, err := s.GetTask(tx, pid, taskID)
	if err != nil {
		return nil, err
	}
	deltaBefore := make(map[string]any, len(keys))
	deltaAfter := make(map[string]any, len(keys))
	for _, k := range keys {
		plain := strings.TrimSuffix(k, "_json")
		deltaBefore[plain] = before[plain]
		deltaAfter[plain] = after[plain]
	}
	if err := s.RecordEvent(tx, ctx, &pid, "task", taskID, op, deltaBefore, deltaAfter, nil); err != nil {
		return nil, err
	}
	return map[string]any{"task": after, "changed": true}, nil
}

func (s *Store) versionedUpdate(ctx Ctx, taskID string, expectedVersion *int, op string, mutate mutateFn, requestID string) (map[string]any, error) {
	p, err := NeedCallsign(ctx)
	if err != nil {
		return nil, err
	}
	return s.Idempotent(ctx, requestID, func(tx *sql.Tx) (map[string]any, error) {
		return s.versionedUpdateIn(tx, ctx, p, taskID, expectedVersion, op, mutate)
	})
}

func (s *Store) TaskUpdate(ctx Ctx, taskID string, expectedVersion int, values map[string]any, requestID string, prepare PrepareUpdateFn) (map[string]any, error) {
	if err := ScanSecrets(values, ""); err != nil {
		return nil, err
	}
	allowed := map[string]bool{
		"title": true, "status": true, "priority": true, "branch": true,
		"wbs": true, "wbs_exempt_reason": true, "description": true, "plan_md": true, "fields": true,
	}
	var extra []string
	for k := range values {
		if !allowed[k] {
			extra = append(extra, k)
		}
	}
	if len(extra) > 0 {
		sort.Strings(extra)
		return nil, &HubError{
			Status:  400,
			Code:    "unknown_field",
			Message: "고칠 수 없는 칸: " + strings.Join(extra, ", "),
			Detail:  map[string]any{"fields": extra},
		}
	}
	if err := ValidateTaskFields(values); err != nil {
		return nil, err
	}

	ev := expectedVersion
	return s.versionedUpdate(ctx, taskID, &ev, "update", func(before map[string]any, _ *Principal, tx *sql.Tx) (map[string]any, error) {
		vals := values
		var err error
		if prepare != nil {
			vals, err = prepare(tx, before, values)
			if err != nil {
				return nil, err
			}
		}
		out := make(map[string]any)
		for k, v := range vals {
			if k == "fields" {
				vm, _ := v.(map[string]any)
				bf, _ := before["fields"].(map[string]any)
				merged := make(map[string]any, len(bf)+len(vm))
				for fk, fv := range bf {
					merged[fk] = fv
				}
				for fk, fv := range vm {
					merged[fk] = fv
				}
				if MustJSON(merged) != MustJSON(bf) {
					out["fields_json"] = merged
				}
			} else {
				target := v
				if k == "title" {
					if ts, ok := v.(string); ok {
						target = strings.TrimSpace(ts)
					}
				}
				if MustJSON(before[k]) != MustJSON(target) {
					out[k] = target
				}
			}
		}
		return out, nil
	}, requestID)
}

func ClaimMutate(before map[string]any, p *Principal) (map[string]any, error) {
	assignee, _ := before["assignee"].(string)
	if assignee == p.Callsign {
		return map[string]any{}, nil
	}
	if assignee != "" {
		return nil, &HubError{
			Status:  409,
			Code:    "already_claimed",
			Message: assignee + " 가 맡고 있다",
			Detail:  map[string]any{"assignee": assignee, "current_version": before["version"]},
		}
	}
	if before["status"] == "done" {
		return nil, &HubError{
			Status:  409,
			Code:    "task_done",
			Message: "닫힌 task 는 맡을 수 없다",
		}
	}
	out := map[string]any{"assignee": p.Callsign}
	if before["status"] == "planned" {
		out["status"] = "in_progress"
	}
	return out, nil
}

func (s *Store) TaskClaim(ctx Ctx, taskID, requestID string) (map[string]any, error) {
	return s.versionedUpdate(ctx, taskID, nil, "claim", func(before map[string]any, p *Principal, _ *sql.Tx) (map[string]any, error) {
		return ClaimMutate(before, p)
	}, requestID)
}

func (s *Store) TaskRelease(ctx Ctx, taskID, requestID string) (map[string]any, error) {
	return s.versionedUpdate(ctx, taskID, nil, "release", func(before map[string]any, p *Principal, _ *sql.Tx) (map[string]any, error) {
		if before["assignee"] == nil {
			return map[string]any{}, nil
		}
		if before["assignee"] != p.Callsign && p.Role != "owner" {
			return nil, Forbidden("맡은 콜사인이나 프로젝트 소유자만 놓을 수 있다")
		}
		return map[string]any{"assignee": nil}, nil
	}, requestID)
}

func (s *Store) TaskProgress(ctx Ctx, taskID, note, requestID string) (map[string]any, error) {
	if err := ScanSecrets(note, "note"); err != nil {
		return nil, err
	}
	if strings.TrimSpace(note) == "" {
		return nil, InvalidField("note", "비었다")
	}
	stamp := ctx.Now.Format("2006-01-02 15:04")
	return s.versionedUpdate(ctx, taskID, nil, "progress", func(_ map[string]any, _ *Principal, _ *sql.Tx) (map[string]any, error) {
		return map[string]any{
			"progress_note": fmt.Sprintf("[%s] %s", stamp, strings.TrimSpace(note)),
			"progress_at":   db.FormatISO(ctx.Now),
		}, nil
	}, requestID)
}

func (s *Store) TaskLinkCommit(ctx Ctx, taskID, sha, branch, requestID string) (map[string]any, error) {
	p, err := NeedCallsign(ctx)
	if err != nil {
		return nil, err
	}
	norm := strings.ToLower(strings.TrimSpace(sha))
	if !ShaPattern.MatchString(norm) {
		return nil, InvalidField("sha", "16진 7~40 자")
	}
	pid := p.ProjectID
	return s.Idempotent(ctx, requestID, func(tx *sql.Tx) (map[string]any, error) {
		if _, err := s.GetTask(tx, pid, taskID); err != nil {
			return nil, err
		}
		res, err := tx.Exec(
			"INSERT OR IGNORE INTO task_commit (project_id, task_id, sha, branch, added_by, added_at) VALUES (?, ?, ?, ?, ?, ?)",
			pid, taskID, norm, branch, p.Callsign, db.FormatISO(ctx.Now),
		)
		if err != nil {
			return nil, err
		}
		aff, _ := res.RowsAffected()
		linked := aff > 0
		if linked {
			if err := s.RecordEvent(tx, ctx, &pid, "task", taskID, "link_commit", nil,
				map[string]any{"sha": norm, "branch": branch}, nil); err != nil {
				return nil, err
			}
		}
		return map[string]any{"task_id": taskID, "sha": norm, "linked": linked}, nil
	})
}

func (s *Store) Events(ctx Ctx, targetKind, targetID string, afterSeq, limit int) (map[string]any, error) {
	p, err := NeedReader(ctx)
	if err != nil {
		return nil, err
	}
	if limit < 1 || limit > 1000 {
		return nil, InvalidField("limit", "1~1000")
	}
	sqlStr := "SELECT seq, project_id, at, callsign, target_kind, target_id, op, before_json, after_json, via, client_version FROM event WHERE project_id = ? AND seq > ?"
	args := []any{p.ProjectID, afterSeq}
	if targetKind != "" {
		sqlStr += " AND target_kind = ?"
		args = append(args, targetKind)
	}
	if targetID != "" {
		sqlStr += " AND target_id = ?"
		args = append(args, targetID)
	}
	sqlStr += " ORDER BY seq LIMIT ?"
	args = append(args, limit)
	rows, err := s.pool.Query(sqlStr, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	events := make([]map[string]any, 0)
	for rows.Next() {
		var seq int
		var pid, callsign, beforeRaw, afterRaw, clientVer sql.NullString
		var at, tk, tid, op, via string
		if err := rows.Scan(&seq, &pid, &at, &callsign, &tk, &tid, &op, &beforeRaw, &afterRaw, &via, &clientVer); err != nil {
			return nil, err
		}
		var beforeVal, afterVal any
		if beforeRaw.Valid {
			_ = json.Unmarshal([]byte(beforeRaw.String), &beforeVal)
		}
		if afterRaw.Valid {
			_ = json.Unmarshal([]byte(afterRaw.String), &afterVal)
		}
		var csVal any
		if callsign.Valid {
			csVal = callsign.String
		}
		var pidVal any
		if pid.Valid {
			pidVal = pid.String
		}
		var cvVal any
		if clientVer.Valid {
			cvVal = clientVer.String
		}
		events = append(events, map[string]any{
			"seq":            seq,
			"project_id":     pidVal,
			"at":             at,
			"callsign":       csVal,
			"target_kind":    tk,
			"target_id":      tid,
			"op":             op,
			"before":         beforeVal,
			"after":          afterVal,
			"via":            via,
			"client_version": cvVal,
		})
	}
	return map[string]any{"events": events}, nil
}
