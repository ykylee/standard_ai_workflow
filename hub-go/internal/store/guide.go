package store

import (
	"database/sql"
	"fmt"
	"strings"
	"unicode/utf8"

	"github.com/ykylee/standard_ai_workflow/hub-go/internal/assets"
	"github.com/ykylee/standard_ai_workflow/hub-go/internal/db"
	"github.com/ykylee/standard_ai_workflow/hub-go/internal/pytext"
)

const (
	guideBodyMax = 64 * 1024
	guideNoteMax = 500
)

// GuideRegionBudgetBytes · GuideRegionBudgetLines — 허브 렌더 영역 한 개의 상한, Python render.HUB_REGION_BUDGET_* 와 같다
// (TASK-2026-11-26-claude-plex-027). 근거: Claude Code 진입 파일 200줄 권고 · Codex AGENTS.md 합계 32KiB 잘림.
const (
	GuideRegionBudgetBytes = 12 * 1024
	GuideRegionBudgetLines = 120
)

// GuideRegionOverBudget — 영역이 예산을 넘으면 entry_budget_exceeded 422 (바이트 · 줄 수 둘 다 본다).
func GuideRegionOverBudget(entry, region string) error {
	size, lines := len([]byte(region)), strings.Count(region, "\n")
	if size > GuideRegionBudgetBytes || lines > GuideRegionBudgetLines {
		return &HubError{Status: 422, Code: "entry_budget_exceeded",
			Message: fmt.Sprintf("%s 렌더 영역 %dB · %d줄 > 예산 %dB · %d줄 — 프로젝트 지침을 줄여요", entry, size, lines, GuideRegionBudgetBytes, GuideRegionBudgetLines),
			Detail:  map[string]any{"size": size, "budget": GuideRegionBudgetBytes, "lines": lines, "line_budget": GuideRegionBudgetLines}}
	}
	return nil
}

// GuidePropose applies a guide immediately for an approved human, otherwise
// records an open proposal for an approved human to decide.
func (s *Store) GuidePropose(ctx Ctx, baseVersion int, body, note string) (map[string]any, error) {
	p, err := NeedCallsign(ctx)
	if err != nil {
		return nil, err
	}
	if len([]byte(body)) > guideBodyMax {
		return nil, InvalidField("body", fmt.Sprintf("문자열 · %d 바이트 이하", guideBodyMax))
	}
	if utf8.RuneCountInString(note) > guideNoteMax || strings.ContainsAny(note, "\r\n") {
		return nil, InvalidField("note", fmt.Sprintf("한 줄 · %d자 이하", guideNoteMax))
	}
	if err := ScanSecrets(map[string]any{"body": body, "note": note}, ""); err != nil {
		return nil, err
	}
	pid := p.ProjectID
	var result map[string]any
	_, err = s.withWriteTx(func(tx *sql.Tx) (map[string]any, error) {
		version, current, err := currentGuide(tx, pid)
		if err != nil {
			return nil, err
		}
		if version != baseVersion {
			return nil, &HubError{Status: 409, Code: "version_conflict", Message: fmt.Sprintf("지침 판이 그 사이 올랐어요 — 지금 %d", version), Detail: map[string]any{"current_version": version, "current": current}}
		}
		if body == current {
			return nil, InvalidField("body", "지금 판과 같아요")
		}
		var display string
		if err := tx.QueryRow("SELECT display_name FROM project WHERE id=?", pid).Scan(&display); err != nil {
			return nil, err
		}
		if err := checkGuideRenderable(pid, display, body); err != nil {
			return nil, err
		}
		var n int
		if err := tx.QueryRow("SELECT COUNT(*) FROM guide_proposal WHERE project_id=?", pid).Scan(&n); err != nil {
			return nil, err
		}
		id := fmt.Sprintf("GP-%04d", n+1)
		editor := p.Kind == "callsign" && p.CallsignKind == "human" && p.HumanApproved
		status := "open"
		var decidedBy, decidedAt any
		if editor {
			status, decidedBy, decidedAt = "approved", p.Callsign, db.FormatISO(ctx.Now)
		}
		if _, err := tx.Exec("INSERT INTO guide_proposal(project_id,id,base_version,body_md,note,proposed_by,proposed_at,status,decided_by,decided_at) VALUES(?,?,?,?,?,?,?,?,?,?)", pid, id, baseVersion, body, note, p.Callsign, db.FormatISO(ctx.Now), status, decidedBy, decidedAt); err != nil {
			return nil, err
		}
		if err := s.RecordEvent(tx, ctx, &pid, "guide_proposal", id, "propose", nil, map[string]any{"base_version": baseVersion, "note": note, "direct": editor}, nil); err != nil {
			return nil, err
		}
		var applied any
		if editor {
			next := version + 1
			if err := applyGuide(s, tx, ctx, pid, body, p.Callsign, next); err != nil {
				return nil, err
			}
			if _, err := tx.Exec("UPDATE guide_proposal SET applied_version=? WHERE project_id=? AND id=?", next, pid, id); err != nil {
				return nil, err
			}
			applied = next
		}
		guideVersion := any(nil)
		if editor {
			guideVersion = fmt.Sprintf("%s+p%d", HubKitVersion, version+1)
		}
		nextStep := any("승인된 human 콜사인이 hub_guide_decide 로 승인해야 판이 오른다")
		if editor {
			nextStep = nil
		}
		result = map[string]any{"proposal_id": id, "status": status, "applied_version": applied, "guide_version": guideVersion, "next": nextStep}
		return result, nil
	})
	return result, err
}

// GuideDecide approves or rejects an open guide proposal.
func (s *Store) GuideDecide(ctx Ctx, proposalID string, approve bool) (map[string]any, error) {
	p, err := NeedCallsign(ctx)
	if err != nil {
		return nil, err
	}
	if p.CallsignKind != "human" || !p.HumanApproved {
		return nil, Forbidden("지침 제안의 승인 · 거절은 승인된 human 콜사인만 해요")
	}
	pid := p.ProjectID
	var result map[string]any
	_, err = s.withWriteTx(func(tx *sql.Tx) (map[string]any, error) {
		var base int
		var body, status string
		err := tx.QueryRow("SELECT base_version,body_md,status FROM guide_proposal WHERE project_id=? AND id=?", pid, proposalID).Scan(&base, &body, &status)
		if err == sql.ErrNoRows {
			return nil, NotFound("지침 제안이 없어요: " + proposalID)
		}
		if err != nil {
			return nil, err
		}
		if status != "open" {
			return nil, &HubError{Status: 409, Code: "already_decided", Message: "이미 " + status + " 된 제안이에요", Detail: map[string]any{"status": status}}
		}
		var applied any
		if approve {
			version, current, err := currentGuide(tx, pid)
			if err != nil {
				return nil, err
			}
			if base != version {
				return nil, &HubError{Status: 409, Code: "version_conflict", Message: fmt.Sprintf("제안의 기준 판 %d 이 지금 판 %d 이 아니에요 — 새 판 위에서 다시 제안해요", base, version), Detail: map[string]any{"current_version": version, "current": current}}
			}
			var display string
			if err := tx.QueryRow("SELECT display_name FROM project WHERE id=?", pid).Scan(&display); err != nil {
				return nil, err
			}
			if err := checkGuideRenderable(pid, display, body); err != nil {
				return nil, err
			}
			next := version + 1
			if err := applyGuide(s, tx, ctx, pid, body, p.Callsign, next); err != nil {
				return nil, err
			}
			applied = next
		}
		decided := "rejected"
		if approve {
			decided = "approved"
		}
		if _, err := tx.Exec("UPDATE guide_proposal SET status=?,decided_by=?,decided_at=?,applied_version=? WHERE project_id=? AND id=?", decided, p.Callsign, db.FormatISO(ctx.Now), applied, pid, proposalID); err != nil {
			return nil, err
		}
		if err := s.RecordEvent(tx, ctx, &pid, "guide_proposal", proposalID, "decide", map[string]any{"status": "open"}, map[string]any{"status": decided, "applied_version": applied}, nil); err != nil {
			return nil, err
		}
		guideVersion := any(nil)
		if approve {
			guideVersion = fmt.Sprintf("%s+p%d", HubKitVersion, applied.(int))
		}
		result = map[string]any{"proposal_id": proposalID, "status": decided, "applied_version": applied, "guide_version": guideVersion}
		return result, nil
	})
	return result, err
}

func currentGuide(q interface{ QueryRow(string, ...any) *sql.Row }, projectID string) (int, string, error) {
	var version int
	var body string
	err := q.QueryRow("SELECT version,body_md FROM guide WHERE project_id=? ORDER BY version DESC LIMIT 1", projectID).Scan(&version, &body)
	if err == sql.ErrNoRows {
		return 0, "", nil
	}
	return version, body, err
}

func applyGuide(s *Store, tx *sql.Tx, ctx Ctx, projectID, body, actor string, version int) error {
	if _, err := tx.Exec("INSERT INTO guide(project_id,version,body_md,updated_by,updated_at) VALUES(?,?,?,?,?)", projectID, version, body, actor, db.FormatISO(ctx.Now)); err != nil {
		return err
	}
	return s.RecordEvent(tx, ctx, &projectID, "guide", fmt.Sprint(version), "set", nil, map[string]any{"version": version}, &actor)
}

func checkGuideRenderable(projectID, display, body string) error {
	entries := []struct{ harness, entry string }{{"claude-code", "CLAUDE.md"}, {"codex", "AGENTS.md"}, {"minimax-code", "MiniMax.md"}, {"antigravity", "ANTIGRAVITY.md"}}
	for _, item := range entries {
		harness, entry := item.harness, item.entry
		rendered := fmt.Sprintf("<!-- 이 영역은 워크플로우 허브가 렌더링한다 (%s · %s). 고칠 것은 허브에 지침 제안으로. -->\n%s", entry, harness, assets.StandardBlock)
		if pytext.Strip(body) != "" {
			rendered += fmt.Sprintf("\n## 프로젝트 지침 — %s\n\n%s\n", display, pytext.Strip(body))
		}
		version := HubKitVersion + "+p1"
		region := fmt.Sprintf("<!-- workflow-hub:begin project=%s guide=%s sha256=%064d -->\n%s<!-- workflow-hub:end -->\n", projectID, version, 0, rendered)
		if err := GuideRegionOverBudget(entry, region); err != nil {
			return err
		}
	}
	return nil
}
