package store

import (
	"crypto/rand"
	"database/sql"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"time"

	"github.com/ykylee/standard_ai_workflow/hub-go/internal/db"
)

// RelayInvite creates a single-use, 24-hour invite for a relay host.
func (s *Store) RelayInvite(ctx Ctx) (map[string]any, error) {
	p, err := needOwner(ctx)
	if err != nil {
		return nil, err
	}
	var raw [18]byte
	if _, err := rand.Read(raw[:]); err != nil {
		return nil, err
	}
	code := "wri_" + base64.RawURLEncoding.EncodeToString(raw[:])
	expires := ctx.Now.UTC().Add(24 * time.Hour)
	_, err = s.withWriteTx(func(tx *sql.Tx) (map[string]any, error) {
		if _, err := tx.Exec("INSERT INTO relay_invite(code_hash,for_project,owner_callsign,created_at,expires_at) VALUES(?,?,?,?,?)", HashToken(code), p.ProjectID, p.Callsign, db.FormatISO(ctx.Now), db.FormatISO(expires)); err != nil {
			return nil, err
		}
		if err := s.RecordEvent(tx, ctx, &p.ProjectID, "relay_invite", "-", "issue", nil, map[string]any{"expires_at": db.FormatISO(expires)}, nil); err != nil {
			return nil, err
		}
		return map[string]any{}, nil
	})
	if err != nil {
		return nil, err
	}
	base := ctx.PublicURL
	if base == "" {
		base = "<허브 주소>"
	}
	return map[string]any{"invite": code, "expires_at": db.FormatISO(expires), "command": fmt.Sprintf("python -m workflow_kit relay init --hub %s --invite <위 코드> --name <이 PC 이름>", base), "note": "코드는 이 응답에만 있다 — 그 PC 의 사람에게 직접 건넨다. 한 번 쓰면 끝이다."}, nil
}

// RelayRevoke revokes a relay host, and only the owner who invited it may do so.
func (s *Store) RelayRevoke(ctx Ctx, hostID string) (map[string]any, error) {
	p, err := needOwner(ctx)
	if err != nil {
		return nil, err
	}
	return s.withWriteTx(func(tx *sql.Tx) (map[string]any, error) {
		var inviter, projectsJSON string
		err := tx.QueryRow("SELECT owner_callsign,projects_json FROM relay_host WHERE host_id=? AND revoked_at IS NULL", hostID).Scan(&inviter, &projectsJSON)
		if err == sql.ErrNoRows {
			return nil, NotFound("이 프로젝트의 중계가 아니다: " + hostID)
		}
		if err != nil {
			return nil, err
		}
		var projects []string
		if err := json.Unmarshal([]byte(projectsJSON), &projects); err != nil {
			return nil, err
		}
		found := false
		for _, pid := range projects {
			if pid == p.ProjectID {
				found = true
				break
			}
		}
		if !found {
			return nil, NotFound("이 프로젝트의 중계가 아니다: " + hostID)
		}
		if inviter != p.Callsign {
			return nil, Forbidden("그 중계를 초대한 owner 만")
		}
		if _, err := tx.Exec("UPDATE relay_host SET revoked_at=? WHERE host_id=?", db.FormatISO(ctx.Now), hostID); err != nil {
			return nil, err
		}
		if err := s.RecordEvent(tx, ctx, &p.ProjectID, "relay_host", hostID, "revoke", nil, nil, nil); err != nil {
			return nil, err
		}
		return map[string]any{"host_id": hostID, "revoked": true}, nil
	})
}
