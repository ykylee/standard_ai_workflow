package tools

import (
	"database/sql"
	"encoding/json"
	"fmt"

	"github.com/ykylee/standard_ai_workflow/hub-go/internal/db"
	"github.com/ykylee/standard_ai_workflow/hub-go/internal/store"
)

type setupCheck struct {
	rc     int
	output string
}

type setupStepRow struct{ id, kind, path, sha256, guideVersion, status string }

func confirmItems(raw any, field, shape string, allowed ...string) ([]map[string]any, error) {
	if raw == nil {
		return nil, nil
	}
	items, ok := raw.([]any)
	if !ok {
		return nil, store.InvalidField(field, shape)
	}
	out := make([]map[string]any, 0, len(items))
	for _, item := range items {
		m, ok := item.(map[string]any)
		if !ok {
			return nil, store.InvalidField(field, shape)
		}
		for key := range m {
			known := false
			for _, name := range allowed {
				known = known || key == name
			}
			if !known {
				return nil, store.InvalidField(field, shape)
			}
		}
		if _, ok := m[allowed[0]].(string); !ok {
			return nil, store.InvalidField(field, shape)
		}
		out = append(out, m)
	}
	return out, nil
}

func confirmRC(raw any, exists bool) (int, error) {
	if !exists {
		return 1, nil
	}
	switch n := raw.(type) {
	case int:
		return n, nil
	case int64:
		return int(n), nil
	case float64:
		if n == float64(int(n)) {
			return int(n), nil
		}
	case json.Number:
		if v, err := n.Int64(); err == nil {
			return int(v), nil
		}
	}
	return 0, store.InvalidField("checks.rc", "정수")
}

func setupStepRows(tx *sql.Tx, pid, callsign string) ([]setupStepRow, error) {
	rows, err := tx.Query("SELECT step_id,kind,path,sha256,guide_version,status FROM setup_step WHERE project_id=? AND callsign=? ORDER BY step_id", pid, callsign)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	out := []setupStepRow{}
	for rows.Next() {
		var r setupStepRow
		if err := rows.Scan(&r.id, &r.kind, &r.path, &r.sha256, &r.guideVersion, &r.status); err != nil {
			return nil, err
		}
		out = append(out, r)
	}
	return out, rows.Err()
}

func short12(v string) string {
	if len(v) > 12 {
		return v[:12]
	}
	return v
}

// setupConfirm compares reported file hashes and command results with the issued steps.
// Only issued steps can be confirmed; a step without a report stays as it was.
func setupConfirm(s *store.Store, ctx store.Ctx, args map[string]any) (map[string]any, error) {
	p, err := s.Authenticate(strArg(args, "token", ""), &ctx.Now, "")
	if err != nil {
		return nil, err
	}
	if p == nil || p.Kind != "callsign" {
		return nil, store.Unauthorized("토큰이 없거나 틀렸거나 거둔 토큰이다")
	}
	if p.ProjectID != strArg(args, "project_id", "") {
		return nil, store.Forbidden("이 토큰은 다른 프로젝트의 것이다")
	}
	fileItems, err := confirmItems(args["files"], "files", "[{path, sha256}] 형태", "path", "sha256")
	if err != nil {
		return nil, err
	}
	checkItems, err := confirmItems(args["checks"], "checks", "[{name, rc, output}] 형태", "name", "rc", "output")
	if err != nil {
		return nil, err
	}
	byPath := map[string]string{}
	for _, f := range fileItems {
		sha, _ := f["sha256"].(string)
		byPath[f["path"].(string)] = sha
	}
	byCheck := map[string]setupCheck{}
	for _, c := range checkItems {
		raw, exists := c["rc"]
		rc, err := confirmRC(raw, exists)
		if err != nil {
			return nil, err
		}
		output, _ := c["output"].(string)
		byCheck[c["name"].(string)] = setupCheck{rc, output}
	}
	ignoreCheck, hasIgnore := byCheck["check_ignore"]

	return s.WriteTx(func(tx *sql.Tx) (map[string]any, error) {
		steps, err := setupStepRows(tx, p.ProjectID, p.Callsign)
		if err != nil {
			return nil, err
		}
		confirmed, unconfirmedIDs := []string{}, []string{}
		unconfirmed := []map[string]any{}
		gitignoreFailed := false
		complete, hasEnv := len(steps) > 0, false
		for _, row := range steps {
			hasEnv = hasEnv || row.id == "env"
			if row.status == "confirmed" {
				continue
			}
			ok, why := false, "보고가 없다"
			_, fileReported := byPath[row.path]
			check, checkReported := byCheck[row.id]
			switch {
			case row.id == "gitignore":
				if hasIgnore {
					ok, why = checkIgnoreOK(ignoreCheck.rc, ignoreCheck.output)
				}
			case row.kind == "env" || row.kind == "entry" || (row.kind == "harness" && row.path != ""):
				if fileReported {
					got := byPath[row.path]
					ok, why = got == row.sha256, ""
					if !ok {
						why = fmt.Sprintf("sha256 이 지시와 다르다 (지시 %s…, 받음 %s…)", short12(row.sha256), short12(got))
					}
				}
			case row.kind == "harness":
				if checkReported {
					ok, why = check.rc == 0, ""
					if !ok {
						why = fmt.Sprintf("명령 실패 rc=%d", check.rc)
					}
				}
			}
			if ok {
				if _, err := tx.Exec("UPDATE setup_step SET status='confirmed',detail='',confirmed_at=? WHERE project_id=? AND callsign=? AND step_id=?", db.FormatISO(ctx.Now), p.ProjectID, p.Callsign, row.id); err != nil {
					return nil, err
				}
				confirmed = append(confirmed, row.id)
				if row.kind == "entry" && row.guideVersion != "" {
					if _, err := tx.Exec("UPDATE callsign SET guide_version_seen=? WHERE project_id=? AND id=?", row.guideVersion, p.ProjectID, p.Callsign); err != nil {
						return nil, err
					}
				}
				continue
			}
			complete = false
			if checkReported || fileReported || (row.id == "gitignore" && hasIgnore) {
				if _, err := tx.Exec("UPDATE setup_step SET status='unconfirmed',detail=? WHERE project_id=? AND callsign=? AND step_id=?", why, p.ProjectID, p.Callsign, row.id); err != nil {
					return nil, err
				}
			}
			gitignoreFailed = gitignoreFailed || (row.id == "gitignore" && hasIgnore)
			unconfirmed = append(unconfirmed, map[string]any{"id": row.id, "reason": why})
			unconfirmedIDs = append(unconfirmedIDs, row.id)
		}
		complete = complete && hasEnv
		flag := 0
		if complete {
			flag = 1
		}
		if _, err := tx.Exec("UPDATE callsign SET setup_complete=? WHERE project_id=? AND id=?", flag, p.ProjectID, p.Callsign); err != nil {
			return nil, err
		}
		if err := s.RecordEvent(tx, ctx, &p.ProjectID, "callsign", p.Callsign, "setup_confirm", nil,
			map[string]any{"confirmed": confirmed, "unconfirmed": unconfirmedIDs, "complete": complete}, &p.Callsign); err != nil {
			return nil, err
		}
		var code any
		if gitignoreFailed {
			code = "ignore_not_effective"
		}
		next := "hub_setup_plan 을 다시 부른다 (확인된 단계는 건너뛴다)"
		if complete {
			next = "하네스를 다시 연결한다 — 토큰 환경 변수를 올린 뒤 hub_session_start"
		}
		return map[string]any{"confirmed": confirmed, "unconfirmed": unconfirmed, "setup_complete": complete, "error_code": code, "next": next}, nil
	})
}
