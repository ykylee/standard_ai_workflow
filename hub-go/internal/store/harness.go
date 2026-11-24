package store

import (
	"crypto/rand"
	"database/sql"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"net/url"
	"path"
	"regexp"
	"strings"

	"github.com/ykylee/standard_ai_workflow/hub-go/internal/db"
)

var harnessIDPattern = regexp.MustCompile(`^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$`)
var harnessFilePattern = regexp.MustCompile(`^[A-Za-z0-9._/-]{1,160}$`)

var harnessReportFields = map[string]bool{
	"harness_id": true, "display_name": true, "version": true, "platforms": true,
	"mcp_transports": true, "config_formats": true, "entry_file_candidates": true,
	"documentation_url": true, "notes": true,
}

func harnessText(raw any, field string, max int, required bool) (string, error) {
	if raw == nil && !required {
		return "", nil
	}
	v, ok := raw.(string)
	if !ok || len(v) > max || (required && strings.TrimSpace(v) == "") {
		return "", InvalidField("report."+field, fmt.Sprintf("%d자 이하 문자열", max))
	}
	return strings.TrimSpace(v), nil
}

func harnessStringList(raw any, field string) ([]string, error) {
	items, ok := raw.([]any)
	if raw == nil {
		return []string{}, nil
	}
	if !ok || len(items) > 8 {
		return nil, InvalidField("report."+field, "문자열 목록 0~8개")
	}
	out := []string{}
	seen := map[string]bool{}
	for _, item := range items {
		v, ok := item.(string)
		if !ok || v == "" || len(v) > 160 {
			return nil, InvalidField("report."+field, "각 항목은 1~160자 문자열")
		}
		if !seen[v] {
			seen[v] = true
			out = append(out, v)
		}
	}
	return out, nil
}

func normalizeHarnessReport(raw any) (map[string]any, error) {
	input, ok := raw.(map[string]any)
	if !ok {
		return nil, InvalidField("report", "하네스 프로필 객체")
	}
	unknown := []string{}
	for key := range input {
		if !harnessReportFields[key] {
			unknown = append(unknown, key)
		}
	}
	if len(unknown) > 0 {
		return nil, UnknownField(unknown)
	}
	if err := ScanSecrets(input, "report"); err != nil {
		return nil, err
	}
	id, err := harnessText(input["harness_id"], "harness_id", 64, true)
	if err != nil {
		return nil, err
	}
	id = strings.ToLower(id)
	if !harnessIDPattern.MatchString(id) {
		return nil, InvalidField("report.harness_id", "소문자 영문·숫자와 내부 하이픈만 허용")
	}
	display, err := harnessText(input["display_name"], "display_name", 100, true)
	if err != nil {
		return nil, err
	}
	version, err := harnessText(input["version"], "version", 80, false)
	if err != nil {
		return nil, err
	}
	notes, err := harnessText(input["notes"], "notes", 1000, false)
	if err != nil {
		return nil, err
	}
	docURL, err := harnessText(input["documentation_url"], "documentation_url", 500, false)
	if err != nil {
		return nil, err
	}
	if docURL != "" {
		u, parseErr := url.Parse(docURL)
		if parseErr != nil || u.Scheme != "https" || u.Host == "" || u.User != nil {
			return nil, InvalidField("report.documentation_url", "인증 정보 없는 HTTPS URL")
		}
	}
	platforms, err := harnessStringList(input["platforms"], "platforms")
	if err != nil {
		return nil, err
	}
	transports, err := harnessStringList(input["mcp_transports"], "mcp_transports")
	if err != nil {
		return nil, err
	}
	formats, err := harnessStringList(input["config_formats"], "config_formats")
	if err != nil {
		return nil, err
	}
	files, err := harnessStringList(input["entry_file_candidates"], "entry_file_candidates")
	if err != nil {
		return nil, err
	}
	for _, file := range files {
		if !harnessFilePattern.MatchString(file) || strings.Contains(file, `\`) || strings.HasPrefix(file, "/") || strings.HasPrefix(file, "~") || strings.Contains(file, ":") || path.IsAbs(file) {
			return nil, InvalidField("report.entry_file_candidates", "안전한 상대 경로만 허용")
		}
		for _, part := range strings.Split(file, "/") {
			if part == ".." {
				return nil, InvalidField("report.entry_file_candidates", "경로 역행은 허용하지 않는다")
			}
		}
	}
	return map[string]any{"harness_id": id, "display_name": display, "version": version,
		"platforms": platforms, "mcp_transports": transports, "config_formats": formats,
		"entry_file_candidates": files, "documentation_url": docURL, "notes": notes}, nil
}

func needHarnessCallsign(ctx Ctx) (*Principal, error) {
	p := ctx.Principal
	if p == nil || p.Kind != "callsign" || p.ProjectID == "" || p.Callsign == "" {
		return nil, Unauthorized("프로젝트 콜사인 토큰이 필요하다")
	}
	return p, nil
}

func needHarnessAdmin(ctx Ctx) (*Principal, error) {
	p := ctx.Principal
	if p == nil || p.Kind != "admin" {
		return nil, Forbidden("hub admin 토큰만 전역 하네스 제보를 검토할 수 있다")
	}
	return p, nil
}

func (s *Store) HarnessReportSubmit(ctx Ctx, raw any) (map[string]any, error) {
	p, err := needHarnessCallsign(ctx)
	if err != nil {
		return nil, err
	}
	report, err := normalizeHarnessReport(raw)
	if err != nil {
		return nil, err
	}
	id := report["harness_id"].(string)
	result, err := s.withWriteTx(func(tx *sql.Tx) (map[string]any, error) {
		var reportID, status string
		err := tx.QueryRow("SELECT id,status FROM harness_report WHERE project_id=? AND harness_id=? AND status='pending' ORDER BY submitted_at DESC LIMIT 1", p.ProjectID, id).Scan(&reportID, &status)
		if err == nil {
			return map[string]any{"report_id": reportID, "status": status, "replayed": true}, nil
		}
		if err != sql.ErrNoRows {
			return nil, err
		}
		var suffix [6]byte
		if _, err := rand.Read(suffix[:]); err != nil {
			return nil, err
		}
		reportID = "HR-" + hex.EncodeToString(suffix[:])
		blob, _ := EncodeJSON(report)
		if _, err := tx.Exec("INSERT INTO harness_report(id,project_id,harness_id,report_json,submitted_by,client_version,submitted_at,status) VALUES(?,?,?,?,?,?,?,'pending')", reportID, p.ProjectID, id, blob, p.Callsign, ctx.ClientVersion, db.FormatISO(ctx.Now)); err != nil {
			return nil, err
		}
		pid := p.ProjectID
		if err := s.RecordEvent(tx, ctx, &pid, "harness_report", reportID, "submit", nil, map[string]any{"harness_id": id, "status": "pending"}, nil); err != nil {
			return nil, err
		}
		return map[string]any{"report_id": reportID, "harness_id": id, "status": "pending", "registered": false, "next": "hub admin 검토 후 등록 여부가 결정된다"}, nil
	})
	return result, err
}

func (s *Store) HarnessReportList(ctx Ctx, status string, global bool) (map[string]any, error) {
	p := ctx.Principal
	if p == nil || (p.Kind != "callsign" && p.Kind != "admin") {
		return nil, Unauthorized("")
	}
	if global && p.Kind != "admin" {
		return nil, Forbidden("hub admin 토큰만 전역 검토 대기열을 볼 수 있다")
	}
	if status != "" && status != "pending" && status != "approved" && status != "rejected" {
		return nil, InvalidField("status", "pending · approved · rejected")
	}
	query := "SELECT id,project_id,harness_id,report_json,submitted_by,client_version,submitted_at,status,reviewed_by,reviewed_at,decision_note FROM harness_report"
	args := []any{}
	if !global {
		if _, err := needHarnessCallsign(ctx); err != nil {
			return nil, err
		}
		query += " WHERE project_id=?"
		args = append(args, p.ProjectID)
	}
	if status != "" {
		if strings.Contains(query, " WHERE ") {
			query += " AND status=?"
		} else {
			query += " WHERE status=?"
		}
		args = append(args, status)
	}
	query += " ORDER BY submitted_at DESC LIMIT 200"
	rows, err := s.DB().Query(query, args...)
	if err != nil {
		return nil, err
	}
	items := []map[string]any{}
	for rows.Next() {
		var id, projectID, harnessID, reportJSON, submittedBy, clientVersion, submittedAt, reportStatus, reviewedBy, decisionNote string
		var reviewedAt sql.NullString
		if err := rows.Scan(&id, &projectID, &harnessID, &reportJSON, &submittedBy, &clientVersion, &submittedAt, &reportStatus, &reviewedBy, &reviewedAt, &decisionNote); err != nil {
			return nil, err
		}
		var report map[string]any
		if err := json.Unmarshal([]byte(reportJSON), &report); err != nil {
			return nil, err
		}
		var reviewed any
		if reviewedAt.Valid {
			reviewed = reviewedAt.String
		}
		items = append(items, map[string]any{"id": id, "project_id": projectID, "harness_id": harnessID, "report": report,
			"submitted_by": submittedBy, "client_version": clientVersion, "submitted_at": submittedAt, "status": reportStatus,
			"reviewed_by": reviewedBy, "reviewed_at": reviewed, "decision_note": decisionNote})
	}
	return map[string]any{"reports": items}, rows.Err()
}

func (s *Store) HarnessRegistryList(ctx Ctx, includeInactive bool) (map[string]any, error) {
	p := ctx.Principal
	if p == nil || (p.Kind != "callsign" && p.Kind != "admin") {
		return nil, Unauthorized("")
	}
	if includeInactive && p.Kind != "admin" {
		return nil, Forbidden("비활성 등록부 조회는 hub admin만 가능하다")
	}
	query := "SELECT harness_id,display_name,profile_json,source_report_id,version,active,registered_by,registered_at FROM harness_registry"
	if !includeInactive {
		query += " WHERE active=1"
	}
	query += " ORDER BY harness_id"
	rows, err := s.DB().Query(query)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	items := []map[string]any{}
	for rows.Next() {
		var id, display, profileJSON, sourceID, actor, registered string
		var version, active int
		if err := rows.Scan(&id, &display, &profileJSON, &sourceID, &version, &active, &actor, &registered); err != nil {
			return nil, err
		}
		var profile map[string]any
		if err := json.Unmarshal([]byte(profileJSON), &profile); err != nil {
			return nil, err
		}
		items = append(items, map[string]any{"harness_id": id, "display_name": display, "profile": profile, "source_report_id": sourceID,
			"version": version, "active": active != 0, "registered_by": actor, "registered_at": registered, "setup_ready": false})
	}
	if err := rows.Err(); err != nil {
		rows.Close()
		return nil, err
	}
	if err := rows.Close(); err != nil {
		return nil, err
	}
	for _, item := range items {
		owners, err := s.HarnessPeopleFor(item["harness_id"].(string))
		if err != nil {
			return nil, err
		}
		item["owners"] = owners
	}
	return map[string]any{"harnesses": items}, nil
}

func (s *Store) HarnessPeopleFor(harnessID string) ([]map[string]any, error) {
	rows, err := s.DB().Query("SELECT p.id,p.display_name FROM harness_registry_person rp JOIN harness_person p ON p.id=rp.person_id WHERE rp.harness_id=? AND p.active=1 ORDER BY p.display_name,p.id", harnessID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	out := []map[string]any{}
	for rows.Next() {
		var id, name string
		if err := rows.Scan(&id, &name); err != nil {
			return nil, err
		}
		out = append(out, map[string]any{"id": id, "display_name": name})
	}
	return out, rows.Err()
}

func (s *Store) HarnessPeopleList(ctx Ctx) (map[string]any, error) {
	if _, err := needHarnessAdmin(ctx); err != nil {
		return nil, err
	}
	rows, err := s.DB().Query("SELECT id,display_name,created_by,created_at FROM harness_person WHERE active=1 ORDER BY display_name,id")
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	items := []map[string]any{}
	for rows.Next() {
		var id, name, actor, created string
		if err := rows.Scan(&id, &name, &actor, &created); err != nil {
			return nil, err
		}
		items = append(items, map[string]any{"id": id, "display_name": name, "created_by": actor, "created_at": created})
	}
	return map[string]any{"people": items}, rows.Err()
}

func (s *Store) HarnessPersonCreate(ctx Ctx, displayName string) (map[string]any, error) {
	p, err := needHarnessAdmin(ctx)
	if err != nil {
		return nil, err
	}
	displayName = strings.TrimSpace(displayName)
	if displayName == "" || len(displayName) > 100 {
		return nil, InvalidField("display_name", "필수 100자 이하 문자열")
	}
	if err := ScanSecrets(map[string]any{"display_name": displayName}, "person"); err != nil {
		return nil, err
	}
	var suffix [6]byte
	if _, err := rand.Read(suffix[:]); err != nil {
		return nil, err
	}
	id := "HP-" + hex.EncodeToString(suffix[:])
	if _, err := s.DB().Exec("INSERT INTO harness_person(id,display_name,created_by,created_at) VALUES(?,?,?,?)", id, displayName, p.Name, db.FormatISO(ctx.Now)); err != nil {
		return nil, err
	}
	return map[string]any{"person": map[string]any{"id": id, "display_name": displayName}}, nil
}

func (s *Store) HarnessReportDecide(ctx Ctx, reportID, decision, note string, ownerIDs []string) (map[string]any, error) {
	p, err := needHarnessAdmin(ctx)
	if err != nil {
		return nil, err
	}
	if decision != "approve" && decision != "reject" {
		return nil, InvalidField("decision", "approve · reject")
	}
	if len(note) > 1000 {
		return nil, InvalidField("note", "1000자 이하")
	}
	if decision == "approve" {
		if len(ownerIDs) == 0 || len(ownerIDs) > 20 {
			return nil, InvalidField("owner_ids", "승인 등록에 사람 담당자 1~20명을 지정해야 한다")
		}
		seen := map[string]bool{}
		for _, id := range ownerIDs {
			if id == "" || seen[id] {
				return nil, InvalidField("owner_ids", "등록된 사람 ID의 중복 없는 목록이어야 한다")
			}
			seen[id] = true
		}
	}
	var harnessID string
	result, err := s.withWriteTx(func(tx *sql.Tx) (map[string]any, error) {
		var projectID, reportJSON, status string
		if err := tx.QueryRow("SELECT project_id,harness_id,report_json,status FROM harness_report WHERE id=?", reportID).Scan(&projectID, &harnessID, &reportJSON, &status); err != nil {
			if err == sql.ErrNoRows {
				return nil, NotFound("하네스 제보가 없다: " + reportID)
			}
			return nil, err
		}
		if status != "pending" {
			return nil, &HubError{Status: 409, Code: "version_conflict", Message: "이미 검토가 끝난 제보다", Detail: map[string]any{"status": status}}
		}
		approvedStatus := "rejected"
		if decision == "approve" {
			for _, personID := range ownerIDs {
				var active int
				if err := tx.QueryRow("SELECT active FROM harness_person WHERE id=?", personID).Scan(&active); err != nil || active != 1 {
					return nil, InvalidField("owner_ids", "활성 사람 명부에서 담당자를 선택해야 한다")
				}
			}
			var profile map[string]any
			if err := json.Unmarshal([]byte(reportJSON), &profile); err != nil {
				return nil, err
			}
			if _, err := tx.Exec("INSERT INTO harness_registry(harness_id,display_name,profile_json,source_report_id,version,active,registered_by,registered_at) VALUES(?,?,?,?,1,1,?,?) ON CONFLICT(harness_id) DO UPDATE SET display_name=excluded.display_name,profile_json=excluded.profile_json,source_report_id=excluded.source_report_id,version=harness_registry.version+1,active=1,registered_by=excluded.registered_by,registered_at=excluded.registered_at", harnessID, profile["display_name"], reportJSON, reportID, p.Name, db.FormatISO(ctx.Now)); err != nil {
				return nil, err
			}
			if _, err := tx.Exec("DELETE FROM harness_registry_person WHERE harness_id=?", harnessID); err != nil {
				return nil, err
			}
			for _, personID := range ownerIDs {
				if _, err := tx.Exec("INSERT INTO harness_registry_person(harness_id,person_id,assigned_by,assigned_at) VALUES(?,?,?,?)", harnessID, personID, p.Name, db.FormatISO(ctx.Now)); err != nil {
					return nil, err
				}
			}
			approvedStatus = "approved"
		}
		if _, err := tx.Exec("UPDATE harness_report SET status=?,reviewed_by=?,reviewed_at=?,decision_note=? WHERE id=? AND status='pending'", approvedStatus, p.Name, db.FormatISO(ctx.Now), note, reportID); err != nil {
			return nil, err
		}
		pid := projectID
		if err := s.RecordEvent(tx, ctx, &pid, "harness_report", reportID, decision, map[string]any{"status": "pending"}, map[string]any{"status": approvedStatus, "harness_id": harnessID, "note": note}, &p.Name); err != nil {
			return nil, err
		}
		return map[string]any{"report_id": reportID, "harness_id": harnessID, "status": approvedStatus, "registered": decision == "approve", "setup_ready": false}, nil
	})
	return result, err
}
