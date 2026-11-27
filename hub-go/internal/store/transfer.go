package store

import (
	"crypto/rand"
	"crypto/sha256"
	"database/sql"
	"encoding/base64"
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

// 허브 간 프로젝트 이전 — Python hub/transfer.py 와 같은 묶음 형식 · digest · 거절.

const bundleFormat = "workflow-hub-project-bundle/1"

// hubScopedTables never travel: account links and execution approvals belong to the hub that issued them.
var hubScopedTables = map[string]bool{
	"meta": true, "hub_token": true, "sqlite_sequence": true, "project": true, "hub_invite": true, "relay_host": true, "relay_invite": true,
	"harness_registry": true, "harness_person": true, "harness_registry_person": true,
	"hub_account": true, "hub_account_callsign": true, "hub_account_session": true, "hub_account_login_attempt": true,
	"approval_grant": true, "a2a_task": true, "a2a_peer": true,
}

func (s *Store) postgres() bool {
	return strings.HasPrefix(s.Path, "postgres://") || strings.HasPrefix(s.Path, "postgresql://")
}

func stringRows(tx *sql.Tx, query string, args ...any) ([]string, error) {
	rows, err := tx.Query(query, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	out := []string{}
	for rows.Next() {
		var v string
		if err := rows.Scan(&v); err != nil {
			return nil, err
		}
		out = append(out, v)
	}
	return out, rows.Err()
}

func (s *Store) tableColumns(tx *sql.Tx, table string) ([]string, error) {
	if s.postgres() {
		return stringRows(tx, "SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name=? ORDER BY ordinal_position", table)
	}
	return stringRows(tx, "SELECT name FROM pragma_table_info(?) ORDER BY cid", table)
}

func (s *Store) projectTables(tx *sql.Tx) ([]string, error) {
	query := "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
	if s.postgres() {
		query = "SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE' ORDER BY table_name"
	}
	names, err := stringRows(tx, query)
	if err != nil {
		return nil, err
	}
	out := []string{}
	for _, name := range names {
		if hubScopedTables[name] {
			continue
		}
		cols, err := s.tableColumns(tx, name)
		if err != nil {
			return nil, err
		}
		for _, c := range cols {
			if c == "project_id" {
				out = append(out, name)
				break
			}
		}
	}
	return out, nil
}

// foreignKeyOrder returns parents before children.
func (s *Store) foreignKeyOrder(tx *sql.Tx, tables []string) ([]string, error) {
	in := map[string]bool{}
	for _, t := range tables {
		in[t] = true
	}
	parents := map[string]map[string]bool{}
	for _, child := range tables {
		query := `SELECT "table" FROM pragma_foreign_key_list(?)`
		if s.postgres() {
			query = "SELECT parent.relname FROM pg_constraint fk JOIN pg_class child ON child.oid=fk.conrelid JOIN pg_class parent ON parent.oid=fk.confrelid " +
				"JOIN pg_namespace ns ON ns.oid=child.relnamespace WHERE fk.contype='f' AND ns.nspname='public' AND child.relname=?"
		}
		list, err := stringRows(tx, query, child)
		if err != nil {
			return nil, err
		}
		parents[child] = map[string]bool{}
		for _, p := range list {
			if in[p] {
				parents[child][p] = true
			}
		}
	}
	ordered := []string{}
	for len(in) > 0 {
		ready := []string{}
		for t := range in {
			free := true
			for p := range parents[t] {
				free = free && !in[p]
			}
			if free {
				ready = append(ready, t)
			}
		}
		if len(ready) == 0 {
			return nil, &HubError{Status: 409, Code: "bundle_schema_cycle", Message: "표 사이 외래 키 순환이 있어 이전할 수 없어요"}
		}
		sort.Strings(ready)
		for _, t := range ready {
			delete(in, t)
		}
		ordered = append(ordered, ready...)
	}
	return ordered, nil
}

// canonicalJSON writes the bytes Python json.dumps(sort_keys, ensure_ascii=False, separators=(",", ":")) writes.
func canonicalJSON(b *strings.Builder, v any) {
	switch x := v.(type) {
	case nil:
		b.WriteString("null")
	case bool:
		b.WriteString(strconv.FormatBool(x))
	case string:
		b.WriteByte('"')
		for _, r := range x {
			switch r {
			case '"', '\\':
				b.WriteByte('\\')
				b.WriteRune(r)
			case '\n':
				b.WriteString(`\n`)
			case '\r':
				b.WriteString(`\r`)
			case '\t':
				b.WriteString(`\t`)
			case '\b':
				b.WriteString(`\b`)
			case '\f':
				b.WriteString(`\f`)
			default:
				if r < 0x20 {
					fmt.Fprintf(b, `\u%04x`, r)
				} else {
					b.WriteRune(r)
				}
			}
		}
		b.WriteByte('"')
	case int:
		b.WriteString(strconv.Itoa(x))
	case int64:
		b.WriteString(strconv.FormatInt(x, 10))
	case float64:
		text := strconv.FormatFloat(x, 'f', -1, 64)
		if !strings.Contains(text, ".") {
			text += ".0"
		}
		b.WriteString(text)
	case []string:
		list := make([]any, len(x))
		for i := range x {
			list[i] = x[i]
		}
		canonicalJSON(b, list)
	case [][]any:
		list := make([]any, len(x))
		for i := range x {
			list[i] = x[i]
		}
		canonicalJSON(b, list)
	case []any:
		b.WriteByte('[')
		for i, item := range x {
			if i > 0 {
				b.WriteByte(',')
			}
			canonicalJSON(b, item)
		}
		b.WriteByte(']')
	case map[string]any:
		keys := make([]string, 0, len(x))
		for k := range x {
			keys = append(keys, k)
		}
		sort.Strings(keys)
		b.WriteByte('{')
		for i, k := range keys {
			if i > 0 {
				b.WriteByte(',')
			}
			canonicalJSON(b, k)
			b.WriteByte(':')
			canonicalJSON(b, x[k])
		}
		b.WriteByte('}')
	}
}

func bundleDigest(project, tables any) string {
	var b strings.Builder
	canonicalJSON(&b, map[string]any{"project": project, "tables": tables})
	sum := sha256.Sum256([]byte(b.String()))
	return "sha256:" + hex.EncodeToString(sum[:])
}

func rawRows(tx *sql.Tx, query string, args ...any) ([]string, [][]any, error) {
	rows, err := tx.Query(query, args...)
	if err != nil {
		return nil, nil, err
	}
	defer rows.Close()
	cols, err := rows.Columns()
	if err != nil {
		return nil, nil, err
	}
	out := [][]any{}
	for rows.Next() {
		vals, ptrs := make([]any, len(cols)), make([]any, len(cols))
		for i := range vals {
			ptrs[i] = &vals[i]
		}
		if err := rows.Scan(ptrs...); err != nil {
			return nil, nil, err
		}
		for i, v := range vals {
			if raw, ok := v.([]byte); ok {
				vals[i] = string(raw)
			}
		}
		out = append(out, vals)
	}
	return cols, out, rows.Err()
}

// ExportBundle reads a whole project; it does not seal it.
func (s *Store) ExportBundle(projectID string, now time.Time, publicURL string) (map[string]any, error) {
	version, err := s.DBVersion()
	if err != nil {
		return nil, err
	}
	return s.withWriteTx(func(tx *sql.Tx) (map[string]any, error) {
		cols, rows, err := rawRows(tx, "SELECT * FROM project WHERE id=?", projectID)
		if err != nil {
			return nil, err
		}
		if len(rows) == 0 {
			return nil, NotFound("프로젝트가 없어요: " + projectID)
		}
		project := map[string]any{}
		for i, c := range cols {
			project[c] = rows[0][i]
		}
		names, err := s.projectTables(tx)
		if err != nil {
			return nil, err
		}
		tables, counts := map[string]any{}, map[string]any{}
		for _, name := range names {
			order := "rowid"
			if name == "event" {
				order = "seq"
			} else if s.postgres() {
				order = "ctid"
			}
			cols, rows, err := rawRows(tx, fmt.Sprintf(`SELECT * FROM "%s" WHERE project_id=? ORDER BY %s`, name, order), projectID)
			if err != nil {
				return nil, err
			}
			tables[name] = map[string]any{"columns": cols, "rows": rows}
			counts[name] = len(rows)
		}
		return map[string]any{"format": bundleFormat,
			"source":  map[string]any{"public_url": publicURL, "kit_version": HubKitVersion, "db_version": version, "exported_at": db.FormatISO(now)},
			"project": project, "tables": tables, "counts": counts, "digest": bundleDigest(project, tables)}, nil
	})
}

func projectSettings(tx *sql.Tx, projectID string) (map[string]any, error) {
	var raw sql.NullString
	err := tx.QueryRow("SELECT settings_json FROM project WHERE id=?", projectID).Scan(&raw)
	if errors.Is(err, sql.ErrNoRows) {
		return nil, NotFound("프로젝트가 없어요: " + projectID)
	}
	if err != nil {
		return nil, err
	}
	settings := map[string]any{}
	if raw.String != "" {
		if err := json.Unmarshal([]byte(raw.String), &settings); err != nil {
			return nil, err
		}
	}
	return settings, nil
}

func (s *Store) setMoved(projectID, to string, now time.Time) (map[string]any, error) {
	return s.withWriteTx(func(tx *sql.Tx) (map[string]any, error) {
		settings, err := projectSettings(tx, projectID)
		if err != nil {
			return nil, err
		}
		was := settings["moved"]
		op, after := "unsealed", any(nil)
		if to == "" {
			delete(settings, "moved")
		} else {
			settings["moved"] = map[string]any{"to": to, "at": db.FormatISO(now)}
			op, was, after = "sealed", nil, map[string]any{"moved_to": to}
		}
		if _, err := tx.Exec("UPDATE project SET settings_json=?,version=version+1 WHERE id=?", MustJSON(settings), projectID); err != nil {
			return nil, err
		}
		who := "hub"
		if err := s.RecordEvent(tx, Ctx{Now: now, Via: "admin"}, &projectID, "project", projectID, op, was, after, &who); err != nil {
			return nil, err
		}
		if to == "" {
			return map[string]any{"project_id": projectID, "sealed": false}, nil
		}
		return map[string]any{"project_id": projectID, "sealed": true, "moved_to": to}, nil
	})
}

// Seal marks a project as moved; every call on it then answers 410.
func (s *Store) Seal(projectID, to string, now time.Time) (map[string]any, error) {
	if to = strings.TrimSpace(to); to == "" {
		return nil, &HubError{Status: 400, Code: "invalid_field", Message: "moved_to: 새 허브 주소가 필요해요"}
	}
	return s.setMoved(projectID, to, now)
}

// Unseal reverses Seal.
func (s *Store) Unseal(projectID string, now time.Time) (map[string]any, error) {
	return s.setMoved(projectID, "", now)
}

func bundleError(status int, code, message string, detail map[string]any) error {
	return &HubError{Status: status, Code: code, Message: message, Detail: detail}
}

// ImportBundle writes a bundle; guard runs in the same transaction so an invite cannot be used twice.
func (s *Store) ImportBundle(raw any, now time.Time, guard func(tx *sql.Tx, projectID string) error) (map[string]any, error) {
	bundle, ok := raw.(map[string]any)
	if !ok || bundle["format"] != bundleFormat {
		return nil, bundleError(400, "invalid_bundle", "묶음 형식이 "+bundleFormat+" 이 아니다", nil)
	}
	project, ok1 := bundle["project"].(map[string]any)
	all, ok2 := bundle["tables"].(map[string]any)
	if !ok1 || !ok2 {
		return nil, bundleError(400, "invalid_bundle", "project · tables 가 없다", nil)
	}
	if bundleDigest(project, all) != bundle["digest"] {
		return nil, bundleError(400, "bundle_digest_mismatch", "묶음 내용이 digest 와 다르다 — 바뀌었거나 잘렸다", nil)
	}
	source, _ := bundle["source"].(map[string]any)
	srcDB, _ := source["db_version"].(int)
	if latest := db.LatestVersion(); srcDB > latest {
		return nil, bundleError(409, "bundle_newer_than_hub", fmt.Sprintf("묶음의 DB 판 %d 이 이 허브가 아는 %d 보다 새롭다 — 허브를 올린다", srcDB, latest),
			map[string]any{"bundle_db_version": srcDB, "hub_db_version": latest})
	}
	type table struct {
		columns []string
		rows    []any
	}
	// 예전 묶음에 실린 허브 전역 표(계정 연결 · 승인 기록)는 들이지 않는다.
	tables, skipped := map[string]table{}, []string{}
	for name, v := range all {
		if hubScopedTables[name] {
			skipped = append(skipped, name)
			continue
		}
		spec, _ := v.(map[string]any)
		rawCols, okC := spec["columns"].([]any)
		rows, okR := spec["rows"].([]any)
		if !okC || !okR {
			return nil, bundleError(400, "invalid_bundle", "표 형식이 아니다: "+name, nil)
		}
		t := table{rows: rows}
		for _, c := range rawCols {
			text, _ := c.(string)
			t.columns = append(t.columns, text)
		}
		tables[name] = t
	}
	sort.Strings(skipped)
	pid, _ := project["id"].(string)
	return s.withWriteTx(func(tx *sql.Tx) (map[string]any, error) {
		if guard != nil {
			if err := guard(tx, pid); err != nil {
				return nil, err
			}
		}
		if !s.postgres() {
			if _, err := tx.Exec("PRAGMA defer_foreign_keys = ON"); err != nil {
				return nil, err
			}
		}
		known, err := s.projectTables(tx)
		if err != nil {
			return nil, err
		}
		knownSet := map[string]bool{}
		for _, t := range known {
			knownSet[t] = true
		}
		unknown, names := []string{}, []string{}
		for name := range tables {
			names = append(names, name)
			if !knownSet[name] {
				unknown = append(unknown, name)
			}
		}
		if len(unknown) > 0 {
			sort.Strings(unknown)
			return nil, bundleError(409, "bundle_unknown_table", "이 허브에 없는 표: "+strings.Join(unknown, ", "), map[string]any{"tables": unknown})
		}
		replaced := false
		settings, err := projectSettings(tx, pid)
		if err == nil {
			if moved, _ := settings["moved"].(map[string]any); moved == nil || moved["to"] == nil || moved["to"] == "" {
				return nil, bundleError(409, "project_exists", "이 허브에 같은 프로젝트가 이미 있다: "+pid+" (봉인되지 않음)", map[string]any{"project_id": pid})
			}
			// 되옮기기 — 봉인된 사본을 새 묶음으로 바꾼다. 사본에 매인 로그인 연결 · 승인은 함께 거둔다.
			order, err := s.foreignKeyOrder(tx, known)
			if err != nil {
				return nil, err
			}
			drop := []string{"hub_account_callsign", "a2a_task", "a2a_peer", "approval_grant"}
			for i := len(order) - 1; i >= 0; i-- {
				drop = append(drop, order[i])
			}
			for _, name := range drop {
				if _, err := tx.Exec(fmt.Sprintf(`DELETE FROM "%s" WHERE project_id=?`, name), pid); err != nil {
					return nil, err
				}
			}
			if _, err := tx.Exec("DELETE FROM project WHERE id=?", pid); err != nil {
				return nil, err
			}
			replaced = true
		} else if he, ok := AsHubError(err); !ok || he.Status != 404 {
			return nil, err
		}
		clash := []string{}
		for _, row := range tables["project_alias"].rows {
			cells, _ := row.([]any)
			if len(cells) == 0 {
				continue
			}
			var n int
			if err := tx.QueryRow("SELECT COUNT(*) FROM project_alias WHERE key=?", cells[0]).Scan(&n); err != nil {
				return nil, err
			}
			if n > 0 {
				clash = append(clash, fmt.Sprint(cells[0]))
			}
		}
		if len(clash) > 0 {
			return nil, bundleError(409, "alias_taken", "이 허브에서 다른 프로젝트가 쓰는 저장소 주소: "+strings.Join(clash, ", "), map[string]any{"keys": clash})
		}
		insert := func(name string, columns []string, values []any) error {
			quoted, marks := make([]string, len(columns)), make([]string, len(columns))
			for i, c := range columns {
				quoted[i], marks[i] = `"`+c+`"`, "?"
			}
			_, err := tx.Exec(fmt.Sprintf(`INSERT INTO "%s" (%s) VALUES (%s)`, name, strings.Join(quoted, ", "), strings.Join(marks, ", ")), values...)
			return err
		}
		pcols, err := s.tableColumns(tx, "project")
		if err != nil {
			return nil, err
		}
		moved := map[string]any{}
		if text, _ := project["settings_json"].(string); text != "" {
			if err := json.Unmarshal([]byte(text), &moved); err != nil {
				return nil, bundleError(400, "invalid_bundle", "project.settings_json 이 JSON 이 아니다", nil)
			}
		}
		delete(moved, "moved") // 옮겨 온 정본은 봉인 상태가 아니다
		columns, values := []string{}, []any{}
		for _, c := range pcols {
			v, has := project[c]
			if c == "settings_json" {
				v, has = MustJSON(moved), true
			}
			if has {
				columns, values = append(columns, c), append(values, v)
			}
		}
		if err := insert("project", columns, values); err != nil {
			return nil, err
		}
		order, err := s.foreignKeyOrder(tx, names)
		if err != nil {
			return nil, err
		}
		counts := map[string]any{}
		for _, name := range order {
			t := tables[name]
			have, err := s.tableColumns(tx, name)
			if err != nil {
				return nil, err
			}
			haveSet := map[string]bool{}
			for _, c := range have {
				haveSet[c] = true
			}
			missing, index, cols := []string{}, []int{}, []string{}
			pidAt := -1
			for i, c := range t.columns {
				if name == "event" && c == "seq" {
					continue
				}
				if !haveSet[c] {
					missing = append(missing, c)
				}
				if c == "project_id" {
					pidAt = i
				}
				index, cols = append(index, i), append(cols, c)
			}
			if len(missing) > 0 {
				sort.Strings(missing)
				return nil, bundleError(409, "bundle_unknown_column", name+" 에 없는 열: "+strings.Join(missing, ", "), map[string]any{"table": name, "columns": missing})
			}
			for _, row := range t.rows {
				cells, ok := row.([]any)
				// 묶음의 줄은 그 프로젝트 것이어야 한다 — 다른 프로젝트에 줄을 심지 못하게.
				if !ok || len(cells) != len(t.columns) || pidAt < 0 || cells[pidAt] != pid {
					return nil, bundleError(400, "invalid_bundle", name+" 의 줄이 이 프로젝트의 것이 아니다", nil)
				}
				values := make([]any, len(index))
				for i, at := range index {
					values[i] = cells[at]
				}
				if err := insert(name, cols, values); err != nil {
					return nil, err
				}
			}
			counts[name] = len(t.rows)
		}
		who := "hub"
		if err := s.RecordEvent(tx, Ctx{Now: now, Via: "admin"}, &pid, "project", pid, "project_imported", nil,
			map[string]any{"source": bundle["source"], "digest": bundle["digest"], "replaced": replaced}, &who); err != nil {
			return nil, err
		}
		return map[string]any{"project_id": pid, "counts": counts, "replaced_sealed_copy": replaced, "skipped_hub_tables": skipped, "digest": bundle["digest"]}, nil
	})
}

func transferOwner(ctx Ctx) (string, error) {
	p := ctx.Principal
	if p == nil || p.Kind != "callsign" || p.Role != "owner" || p.CallsignKind != "human" || !p.HumanApproved {
		return "", Forbidden("프로젝트 이전은 그 프로젝트의 소유자(승인된 human)가 해요")
	}
	return p.ProjectID, nil
}

// ProjectExport lets an owner take a bundle, sealing first when sealTo is given.
func (s *Store) ProjectExport(ctx Ctx, sealTo string) (map[string]any, error) {
	pid, err := transferOwner(ctx)
	if err != nil {
		return nil, err
	}
	if sealTo != "" && ctx.PublicURL != "" && strings.TrimRight(sealTo, "/") == strings.TrimRight(ctx.PublicURL, "/") {
		return nil, &HubError{Status: 400, Code: "invalid_field", Message: "seal_to: 지금 허브와 같은 주소예요"}
	}
	was, err := s.ProjectMoved(pid)
	if err != nil {
		return nil, err
	}
	var sealed any
	if sealTo != "" {
		if sealed, err = s.Seal(pid, sealTo, ctx.Now); err != nil {
			return nil, err
		}
	}
	bundle, err := s.ExportBundle(pid, ctx.Now, ctx.PublicURL)
	if err != nil {
		return nil, err
	}
	return map[string]any{"sealed": sealed, "was_sealed": was != "", "bundle": bundle}, nil
}

// ProjectUnseal lets an owner undo a failed move.
func (s *Store) ProjectUnseal(ctx Ctx) (map[string]any, error) {
	pid, err := transferOwner(ctx)
	if err != nil {
		return nil, err
	}
	return s.Unseal(pid, ctx.Now)
}

// IssueProjectInvite makes a single-use code for bringing one project into this hub.
func (s *Store) IssueProjectInvite(projectID string, now time.Time, hours int, note string) (map[string]any, error) {
	if strings.TrimSpace(projectID) == "" {
		return nil, &HubError{Status: 400, Code: "invalid_field", Message: "project: 들일 프로젝트 ID"}
	}
	var raw [24]byte
	if _, err := rand.Read(raw[:]); err != nil {
		return nil, err
	}
	code := "wfi_" + base64.RawURLEncoding.EncodeToString(raw[:])
	expires := db.FormatISO(now.Add(time.Duration(hours) * time.Hour))
	return s.withWriteTx(func(tx *sql.Tx) (map[string]any, error) {
		if _, err := tx.Exec("INSERT INTO hub_invite (code_hash,for_project,created_at,expires_at,note) VALUES (?,?,?,?,?)", HashToken(code), projectID, db.FormatISO(now), expires, note); err != nil {
			return nil, err
		}
		who := "hub"
		if err := s.RecordEvent(tx, Ctx{Now: now, Via: "admin"}, nil, "hub_invite", projectID, "issue", nil, map[string]any{"expires_at": expires}, &who); err != nil {
			return nil, err
		}
		return map[string]any{"code": code, "project_id": projectID, "expires_at": expires}, nil
	})
}

// ProjectImport accepts a bundle with a single-use invite code; the code is the authority.
func (s *Store) ProjectImport(ctx Ctx, invite string, bundle any) (map[string]any, error) {
	object, ok := bundle.(map[string]any)
	if !ok {
		return nil, bundleError(400, "invalid_bundle", "bundle 이 객체가 아니다", nil)
	}
	hash := HashToken(invite)
	project, _ := object["project"].(map[string]any)
	bundlePID, _ := project["id"].(string)
	check := func(q interface {
		QueryRow(string, ...any) *sql.Row
	}) error {
		var target, expires string
		var used sql.NullString
		err := q.QueryRow("SELECT for_project,expires_at,used_at FROM hub_invite WHERE code_hash=?", hash).Scan(&target, &expires, &used)
		if errors.Is(err, sql.ErrNoRows) {
			return bundleError(403, "invalid_invite", "초대 코드가 없다", nil)
		}
		if err != nil {
			return err
		}
		if used.String != "" {
			return bundleError(403, "invite_used", "이미 쓴 초대 코드다", nil)
		}
		if expires <= db.FormatISO(ctx.Now) {
			return bundleError(403, "invite_expired", "초대 코드가 만료됐다", nil)
		}
		if bundlePID != target {
			return bundleError(403, "invite_wrong_project", "이 초대 코드는 "+target+" 용이다 (묶음: "+bundlePID+")", map[string]any{"invite_project": target, "bundle_project": bundlePID})
		}
		return nil
	}
	if err := check(s.pool); err != nil {
		return nil, err
	}
	return s.ImportBundle(object, ctx.Now, func(tx *sql.Tx, pid string) error {
		if err := check(tx); err != nil {
			return err
		}
		_, err := tx.Exec("UPDATE hub_invite SET used_at=? WHERE code_hash=?", db.FormatISO(ctx.Now), hash)
		return err
	})
}

// RelayList lists the relays serving the caller's project.
func (s *Store) RelayList(ctx Ctx) (map[string]any, error) {
	p, err := NeedReader(ctx)
	if err != nil {
		return nil, err
	}
	rows, err := s.pool.Query("SELECT host_id,name,harnesses_json,allow_digest,last_seen_at,projects_json FROM relay_host WHERE revoked_at IS NULL ORDER BY host_id")
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	hosts := []map[string]any{}
	for rows.Next() {
		var id, name, harnesses, projects string
		var digest, seen sql.NullString
		if err := rows.Scan(&id, &name, &harnesses, &digest, &seen, &projects); err != nil {
			return nil, err
		}
		var list []string
		if err := json.Unmarshal([]byte(projects), &list); err != nil {
			return nil, err
		}
		for _, pid := range list {
			if pid == p.ProjectID {
				host := map[string]any{"host_id": id, "name": name, "harnesses": json.RawMessage(harnesses), "allow_digest": nil, "last_seen_at": nil}
				if digest.String != "" {
					host["allow_digest"] = digest.String
				}
				if seen.Valid {
					host["last_seen_at"] = seen.String
				}
				hosts = append(hosts, host)
				break
			}
		}
	}
	return map[string]any{"hosts": hosts}, rows.Err()
}
