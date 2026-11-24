package store

import (
	"crypto/pbkdf2"
	"crypto/rand"
	"crypto/sha256"
	"crypto/subtle"
	"database/sql"
	"encoding/base64"
	"encoding/hex"
	"errors"
	"fmt"
	"regexp"
	"strings"
	"time"

	"github.com/ykylee/standard_ai_workflow/hub-go/internal/db"
)

const accountPasswordRounds = 310000
const accountSessionDays = 30

var accountNamePattern = regexp.MustCompile(`^[a-z0-9][a-z0-9._-]{2,63}$`)

type HubAccount struct {
	ID          string `json:"id"`
	Username    string `json:"username"`
	DisplayName string `json:"display_name"`
}

func accountPasswordHash(password string) (string, error) {
	salt := make([]byte, 16)
	if _, err := rand.Read(salt); err != nil {
		return "", err
	}
	key, err := pbkdf2.Key(sha256.New, password, salt, accountPasswordRounds, 32)
	if err != nil {
		return "", err
	}
	return fmt.Sprintf("pbkdf2_sha256$%d$%s$%s", accountPasswordRounds,
		base64.RawURLEncoding.EncodeToString(salt), base64.RawURLEncoding.EncodeToString(key)), nil
}

func accountPasswordMatches(password, encoded string) bool {
	parts := strings.Split(encoded, "$")
	if len(parts) != 4 || parts[0] != "pbkdf2_sha256" {
		return false
	}
	var rounds int
	if _, err := fmt.Sscanf(parts[1], "%d", &rounds); err != nil || rounds < 100000 || rounds > 1000000 {
		return false
	}
	salt, err := base64.RawURLEncoding.DecodeString(parts[2])
	if err != nil {
		return false
	}
	want, err := base64.RawURLEncoding.DecodeString(parts[3])
	if err != nil || len(want) != 32 {
		return false
	}
	got, err := pbkdf2.Key(sha256.New, password, salt, rounds, 32)
	if err != nil {
		return false
	}
	return subtle.ConstantTimeCompare(got, want) == 1
}

func (s *Store) AccountEnroll(token, username, displayName, password string, now time.Time) (string, HubAccount, map[string]any, error) {
	p, err := s.Authenticate(token, &now, "")
	if err != nil {
		return "", HubAccount{}, nil, err
	}
	if p == nil || p.Kind != "callsign" || p.CallsignKind != "human" || !p.HumanApproved {
		return "", HubAccount{}, nil, Forbidden("승인된 사람 콜사인 토큰으로만 계정을 만들 수 있다")
	}
	username = strings.ToLower(strings.TrimSpace(username))
	displayName = strings.TrimSpace(displayName)
	if !accountNamePattern.MatchString(username) {
		return "", HubAccount{}, nil, InvalidField("username", "영문 소문자·숫자·._- 3~64자")
	}
	if displayName == "" || len([]rune(displayName)) > 100 {
		return "", HubAccount{}, nil, InvalidField("display_name", "1~100자")
	}
	if len([]rune(password)) < 8 || len([]rune(password)) > 256 {
		return "", HubAccount{}, nil, InvalidField("password", "8~256자")
	}
	passwordHash, err := accountPasswordHash(password)
	if err != nil {
		return "", HubAccount{}, nil, err
	}
	var idBytes [16]byte
	if _, err := rand.Read(idBytes[:]); err != nil {
		return "", HubAccount{}, nil, err
	}
	account := HubAccount{ID: "acct_" + hex.EncodeToString(idBytes[:]), Username: username, DisplayName: displayName}
	session, err := NewToken()
	if err != nil {
		return "", HubAccount{}, nil, err
	}
	expires := now.Add(accountSessionDays * 24 * time.Hour)
	_, err = s.withWriteTx(func(tx *sql.Tx) (map[string]any, error) {
		var linked int
		err := tx.QueryRow("SELECT COUNT(*) FROM hub_account_callsign WHERE project_id=? AND callsign=?", p.ProjectID, p.Callsign).Scan(&linked)
		if err != nil {
			return nil, err
		}
		if linked > 0 {
			return nil, &HubError{Status: 409, Code: "callsign_already_linked", Message: "이 사람 콜사인은 이미 계정에 연결됐다"}
		}
		if _, err := tx.Exec("INSERT INTO hub_account(id,username,display_name,password_hash,created_at) VALUES(?,?,?,?,?)", account.ID, username, displayName, passwordHash, db.FormatISO(now)); err != nil {
			if strings.Contains(strings.ToLower(err.Error()), "unique") {
				return nil, &HubError{Status: 409, Code: "username_taken", Message: "이미 사용 중인 계정 이름이다"}
			}
			return nil, err
		}
		if _, err := tx.Exec("INSERT INTO hub_account_callsign(account_id,project_id,callsign,linked_at) VALUES(?,?,?,?)", account.ID, p.ProjectID, p.Callsign, db.FormatISO(now)); err != nil {
			return nil, err
		}
		_, err = tx.Exec("INSERT INTO hub_account_session(token_hash,account_id,created_at,expires_at) VALUES(?,?,?,?)", HashToken(session), account.ID, db.FormatISO(now), db.FormatISO(expires))
		return nil, err
	})
	if err != nil {
		return "", HubAccount{}, nil, err
	}
	return session, account, map[string]any{"project_id": p.ProjectID, "callsign": p.Callsign}, nil
}

func (s *Store) AccountLogin(username, password string, now time.Time) (string, HubAccount, error) {
	username = strings.ToLower(strings.TrimSpace(username))
	usernameHash := HashToken(username)
	var account HubAccount
	var encoded string
	denied, limited := false, false
	_, err := s.withWriteTx(func(tx *sql.Tx) (map[string]any, error) {
		var attempts int
		var started string
		var locked sql.NullString
		e := tx.QueryRow("SELECT attempts,window_started_at,locked_until FROM hub_account_login_attempt WHERE username_hash=?", usernameHash).Scan(&attempts, &started, &locked)
		if e != nil && !errors.Is(e, sql.ErrNoRows) {
			return nil, e
		}
		if e == nil && locked.Valid && locked.String > db.FormatISO(now) {
			limited = true
			return nil, nil
		}
		e = tx.QueryRow("SELECT id,username,display_name,password_hash FROM hub_account WHERE username=? AND active=1", username).Scan(&account.ID, &account.Username, &account.DisplayName, &encoded)
		if errors.Is(e, sql.ErrNoRows) {
			encoded = "pbkdf2_sha256$310000$AAAAAAAAAAAAAAAAAAAAAA$AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
		}
		valid := accountPasswordMatches(password, encoded) && e == nil
		if e != nil && !errors.Is(e, sql.ErrNoRows) {
			return nil, e
		}
		if !valid {
			denied = true
			window := now
			count := 1
			if e == nil || attempts > 0 {
				if parsed, parseErr := time.Parse(time.RFC3339, started); parseErr == nil && now.Sub(parsed) < 15*time.Minute {
					window = parsed
					count = attempts + 1
				}
			}
			var until any
			if count >= 8 {
				until = db.FormatISO(now.Add(15 * time.Minute))
			}
			_, writeErr := tx.Exec("INSERT INTO hub_account_login_attempt(username_hash,attempts,window_started_at,locked_until) VALUES(?,?,?,?) ON CONFLICT(username_hash) DO UPDATE SET attempts=excluded.attempts,window_started_at=excluded.window_started_at,locked_until=excluded.locked_until", usernameHash, count, db.FormatISO(window), until)
			return nil, writeErr
		}
		_, e = tx.Exec("DELETE FROM hub_account_login_attempt WHERE username_hash=?", usernameHash)
		return nil, e
	})
	if err != nil {
		return "", HubAccount{}, err
	}
	if limited {
		return "", HubAccount{}, &HubError{Status: 429, Code: "login_rate_limited", Message: "로그인 시도가 많다 — 잠시 뒤 다시 시도한다"}
	}
	if denied {
		return "", HubAccount{}, Unauthorized("계정 이름 또는 비밀번호가 맞지 않는다")
	}
	session, err := NewToken()
	if err != nil {
		return "", HubAccount{}, err
	}
	_, err = s.pool.Exec("INSERT INTO hub_account_session(token_hash,account_id,created_at,expires_at) VALUES(?,?,?,?)", HashToken(session), account.ID, db.FormatISO(now), db.FormatISO(now.Add(accountSessionDays*24*time.Hour)))
	return session, account, err
}

func (s *Store) AccountLink(accountID, token string, now time.Time) (map[string]any, error) {
	p, err := s.Authenticate(token, &now, "")
	if err != nil {
		return nil, err
	}
	if p == nil || p.Kind != "callsign" || p.CallsignKind != "human" || !p.HumanApproved {
		return nil, Forbidden("승인된 사람 콜사인 토큰만 계정에 연결할 수 있다")
	}
	return s.withWriteTx(func(tx *sql.Tx) (map[string]any, error) {
		var active int
		if err := tx.QueryRow("SELECT COUNT(*) FROM hub_account WHERE id=? AND active=1", accountID).Scan(&active); err != nil {
			return nil, err
		}
		if active == 0 {
			return nil, Unauthorized("허브 계정 세션이 만료됐다")
		}
		var linked string
		err := tx.QueryRow("SELECT account_id FROM hub_account_callsign WHERE project_id=? AND callsign=?", p.ProjectID, p.Callsign).Scan(&linked)
		if err == nil {
			if linked == accountID {
				return map[string]any{"project_id": p.ProjectID, "callsign": p.Callsign, "unchanged": true}, nil
			}
			return nil, &HubError{Status: 409, Code: "callsign_already_linked", Message: "이 사람 콜사인은 다른 허브 계정에 연결됐다"}
		}
		if !errors.Is(err, sql.ErrNoRows) {
			return nil, err
		}
		if _, err := tx.Exec("INSERT INTO hub_account_callsign(account_id,project_id,callsign,linked_at) VALUES(?,?,?,?)", accountID, p.ProjectID, p.Callsign, db.FormatISO(now)); err != nil {
			return nil, err
		}
		return map[string]any{"project_id": p.ProjectID, "callsign": p.Callsign}, nil
	})
}

func (s *Store) AccountBySession(token string, now time.Time) (*HubAccount, error) {
	if token == "" {
		return nil, nil
	}
	var a HubAccount
	err := s.pool.QueryRow("SELECT a.id,a.username,a.display_name FROM hub_account_session s JOIN hub_account a ON a.id=s.account_id WHERE s.token_hash=? AND s.revoked_at IS NULL AND s.expires_at>? AND a.active=1", HashToken(token), db.FormatISO(now)).Scan(&a.ID, &a.Username, &a.DisplayName)
	if errors.Is(err, sql.ErrNoRows) {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	return &a, nil
}

func (s *Store) AccountCallsign(accountID, projectID string) (*Principal, error) {
	var p Principal
	var approved int
	err := s.pool.QueryRow("SELECT c.project_id,c.id,c.kind,c.human_approved,c.role,c.label,a.username,a.display_name FROM hub_account_callsign l JOIN callsign c ON c.project_id=l.project_id AND c.id=l.callsign JOIN hub_account a ON a.id=l.account_id WHERE l.account_id=? AND l.project_id=? AND c.revoked_at IS NULL AND a.active=1", accountID, projectID).Scan(&p.ProjectID, &p.Callsign, &p.CallsignKind, &approved, &p.Role, &p.Name, &p.AccountName, &p.AccountLabel)
	if errors.Is(err, sql.ErrNoRows) {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	p.Kind = "callsign"
	p.HumanApproved = approved != 0
	p.AuthMode = "account"
	return &p, nil
}

func (s *Store) AccountProjects(accountID string) ([]string, error) {
	rows, err := s.pool.Query("SELECT DISTINCT project_id FROM hub_account_callsign WHERE account_id=? ORDER BY project_id", accountID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var out []string
	for rows.Next() {
		var id string
		if err := rows.Scan(&id); err != nil {
			return nil, err
		}
		out = append(out, id)
	}
	return out, rows.Err()
}

func (s *Store) AccountDetails(accountID string) (*HubAccount, error) {
	var a HubAccount
	err := s.pool.QueryRow("SELECT id,username,display_name FROM hub_account WHERE id=? AND active=1", accountID).Scan(&a.ID, &a.Username, &a.DisplayName)
	if errors.Is(err, sql.ErrNoRows) {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	return &a, nil
}

func (s *Store) AccountLogout(token string, now time.Time) error {
	if token == "" {
		return nil
	}
	_, err := s.pool.Exec("UPDATE hub_account_session SET revoked_at=? WHERE token_hash=? AND revoked_at IS NULL", db.FormatISO(now), HashToken(token))
	return err
}
