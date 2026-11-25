package store

import (
	"database/sql"
	"errors"
)

// callsignUse counts what makes a callsign undeletable; registration and setup events do not.
var callsignUse = [][2]string{
	{"events", "SELECT COUNT(*) FROM event WHERE project_id=? AND callsign=? AND NOT (target_kind='callsign' AND target_id=callsign)"},
	{"tasks", "SELECT COUNT(*) FROM task WHERE project_id=? AND assignee=?"},
	{"handoffs", "SELECT COUNT(*) FROM handoff WHERE project_id=? AND callsign=?"},
	{"sessions", "SELECT COUNT(*) FROM session WHERE project_id=? AND callsign=?"},
	{"accounts", "SELECT COUNT(*) FROM hub_account_callsign WHERE project_id=? AND callsign=?"},
	{"messages", "SELECT COUNT(*) FROM inbox_message WHERE project_id=? AND to_kind='callsign' AND to_id=?"},
	{"a2a_messages", "SELECT COUNT(*) FROM a2a_peer WHERE project_id=? AND to_callsign=?"},
}

func removeCallsignRows(tx *sql.Tx, projectID, callsign string) error {
	if _, err := tx.Exec("DELETE FROM setup_step WHERE project_id=? AND callsign=?", projectID, callsign); err != nil {
		return err
	}
	_, err := tx.Exec("DELETE FROM callsign WHERE project_id=? AND id=?", projectID, callsign)
	return err
}

// DeleteCallsign removes a callsign that never did anything beyond registration and setup.
// Only a hub admin may; anything with history must be revoked instead.
func (s *Store) DeleteCallsign(ctx Ctx, projectID, callsign, confirm string) (map[string]any, error) {
	if ctx.Via != "admin" && (ctx.Principal == nil || ctx.Principal.Kind != "admin") {
		return nil, Forbidden("콜사인 삭제는 허브 관리자만 한다")
	}
	if confirm != callsign {
		return nil, InvalidField("confirm", "지울 콜사인 이름을 그대로 적는다")
	}
	return s.withWriteTx(func(tx *sql.Tx) (map[string]any, error) {
		var role, kind string
		err := tx.QueryRow("SELECT role,kind FROM callsign WHERE project_id=? AND id=?", projectID, callsign).Scan(&role, &kind)
		if errors.Is(err, sql.ErrNoRows) {
			return nil, NotFound("콜사인이 없다: " + projectID + "/" + callsign)
		}
		if err != nil {
			return nil, err
		}
		var owned int
		if err := tx.QueryRow("SELECT COUNT(*) FROM project WHERE id=? AND owner_callsign=?", projectID, callsign).Scan(&owned); err != nil {
			return nil, err
		}
		if owned > 0 || role == "owner" {
			return nil, &HubError{Status: 409, Code: "callsign_is_owner", Message: "프로젝트 소유자 콜사인은 지울 수 없다: " + callsign, Detail: map[string]any{"callsign": callsign}}
		}
		used := map[string]any{}
		for _, q := range callsignUse {
			var n int
			if err := tx.QueryRow(q[1], projectID, callsign).Scan(&n); err != nil {
				return nil, err
			}
			if n > 0 {
				used[q[0]] = n
			}
		}
		if len(used) > 0 {
			return nil, &HubError{Status: 409, Code: "callsign_in_use", Message: "활동 기록이 있어 지우지 않는다: " + callsign + " — 거두기(callsign revoke)를 쓴다", Detail: map[string]any{"callsign": callsign, "used": used}}
		}
		if err := removeCallsignRows(tx, projectID, callsign); err != nil {
			return nil, err
		}
		actor := "admin:hub"
		if ctx.Principal != nil && ctx.Principal.Name != "" {
			actor = "admin:" + ctx.Principal.Name
		}
		if err := s.RecordEvent(tx, ctx, &projectID, "callsign", callsign, "delete", map[string]any{"kind": kind, "role": role}, nil, &actor); err != nil {
			return nil, err
		}
		return map[string]any{"callsign": callsign, "deleted": true}, nil
	})
}
