package tools

import (
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"strings"

	"github.com/ykylee/standard_ai_workflow/hub-go/internal/judge"
	"github.com/ykylee/standard_ai_workflow/hub-go/internal/pytext"
	"github.com/ykylee/standard_ai_workflow/hub-go/internal/store"
)

// hub_state — 허브 데이터를 1.x 배치로 펼쳐 같은 생성기(judge)로 상태 요약을 만든다 (Python Memory.state).

func stateHandoff(sections map[string]any, titles map[string]string) string {
	str := func(key string) string {
		if v, _ := sections[key].(string); v != "" {
			return v
		}
		return "-"
	}
	list := func(key string, withTitle bool) string {
		out := ""
		raw, _ := sections[key].([]any)
		for _, item := range raw {
			text := fmt.Sprint(item)
			if t, ok := titles[text]; withTitle && ok {
				text += " — " + t
			}
			out += "- " + text + "\n"
		}
		return out
	}
	items := func(key string) string {
		if v := list(key, true); v != "" {
			return v
		}
		return "-\n"
	}
	plain := func(key string) string {
		if v := list(key, false); v != "" {
			return v
		}
		return "- -\n"
	}
	return "# Session Handoff\n\n" +
		"## 1. 현재 작업 요약\n\n- 현재 기준선: " + str("baseline") + "\n- 현재 주 작업 축: " + str("focus") + "\n\n" +
		"## 2. 진행 중 작업\n\n- 현재 `in_progress` 작업:\n" + items("in_progress") + "\n" +
		"## 3. 차단 작업\n\n- 현재 `blocked` 작업:\n" + items("blocked") + "\n" +
		"## 4. 최근 완료 작업\n\n- 최근 완료 작업 목록:\n" + items("recent_done") + "\n" +
		"## 5. 다음 세션 시작 포인트\n\n" + plain("next") + "\n## 6. 남은 리스크\n\n" + plain("risks")
}

func taskDate(id string) string {
	parts := strings.Split(id, "-")
	if len(parts) < 2 {
		return ""
	}
	return strings.Join(parts[1:min(4, len(parts))], "-")
}

func hubState(s *store.Store, ctx store.Ctx, callsign string) (map[string]any, error) {
	p, err := store.NeedCallsign(ctx)
	if err != nil {
		return nil, err
	}
	who := callsign
	if who == "" {
		who = p.Callsign
	}
	files, titles := map[string]string{}, map[string]string{}
	branch := "ai-workflow/memory/active/" + who
	backlogs := map[string]string{}
	rows, err := s.DB().Query("SELECT id,title,status,wbs,plan_md,progress_note FROM task WHERE project_id=? ORDER BY created_at,id", p.ProjectID)
	if err != nil {
		return nil, err
	}
	for rows.Next() {
		var id, title, status string
		var wbs, plan, progress sql.NullString
		if err := rows.Scan(&id, &title, &status, &wbs, &plan, &progress); err != nil {
			rows.Close()
			return nil, err
		}
		titles[id] = title
		date := taskDate(id)
		text := fmt.Sprintf("---\nid: %s\nstatus: %s\ncreated_at: %s\nsource_anchor: generic-%s\nsource_path: backlog/%s.md\nkind: generic", id, status, date, strings.ToLower(id), date)
		if wbs.String != "" {
			text += "\nwbs: " + wbs.String
		}
		text += fmt.Sprintf("\n---\n\n# %s — %s\n\n## 📝 Description\n\n- Status: %s\n", id, title, status)
		if judge.Strip(plan.String) != "" {
			text += "\n## 🧭 Plan\n\n" + pytext.RStrip(plan.String) + "\n"
		}
		if progress.String != "" {
			text += "\n## 🛠️ Implementation / Content\n\n- Progress: " + progress.String + "\n"
		}
		files[branch+"/backlog/tasks/"+id+".md"] = text
		if backlogs[date] == "" {
			backlogs[date] = "# Daily Backlog — " + date + "\n\n"
		}
		backlogs[date] += fmt.Sprintf("- **%s** [generic] %s\n  - path: [`./tasks/%s.md`](./tasks/%s.md)\n  - status: %s\n", id, title, id, id, status)
	}
	if err := rows.Err(); err != nil {
		rows.Close()
		return nil, err
	}
	rows.Close()
	for date, text := range backlogs {
		files[branch+"/backlog/"+date+".md"] = text
	}
	var raw string
	sections := map[string]any{}
	err = s.DB().QueryRow("SELECT sections_json FROM handoff WHERE project_id=? AND callsign=?", p.ProjectID, who).Scan(&raw)
	if err != nil && !errors.Is(err, sql.ErrNoRows) {
		return nil, err
	}
	if err == nil {
		if err := json.Unmarshal([]byte(raw), &sections); err != nil {
			return nil, err
		}
	}
	files[branch+"/"+migHandoff] = stateHandoff(sections, titles)
	var display string
	if err := s.DB().QueryRow("SELECT display_name FROM project WHERE id=?", p.ProjectID).Scan(&display); err != nil {
		return nil, err
	}
	files["docs/PROJECT_PROFILE.md"] = "# " + display + "\n"
	docs, err := s.DB().Query("SELECT name,body_md FROM project_doc WHERE project_id=?", p.ProjectID)
	if err != nil {
		return nil, err
	}
	defer docs.Close()
	for docs.Next() {
		var name, body string
		if err := docs.Scan(&name, &body); err != nil {
			return nil, err
		}
		if name == "profile" && body != "" {
			files["docs/PROJECT_PROFILE.md"] = body
		} else if name == "purpose" && body != "" {
			files[migPurpose] = body
		}
	}
	if err := docs.Err(); err != nil {
		return nil, err
	}
	payload, err := judge.BuildWorkflowStatePayload(files, ctx.Now.Format("2006-01-02"))
	if err != nil {
		return nil, err
	}
	return map[string]any{"callsign": who, "state": payload}, nil
}
