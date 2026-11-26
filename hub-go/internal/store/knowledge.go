package store

import (
	"crypto/sha256"
	"database/sql"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"regexp"
	"sort"
	"strings"
	"time"
)

var knowledgePath = regexp.MustCompile(`^(?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+\.md$`)
var knowledgeID = regexp.MustCompile(`^[a-zA-Z0-9][a-zA-Z0-9._-]{0,79}$`)
var adrSlugInvalid = regexp.MustCompile(`[^a-z0-9]+`)
var adrNumberPattern = regexp.MustCompile(`(?im)(?:adr_id:\s*ADR-|id:\s*ADR-|(?:^|/)adr-)(\d{3,})`)
var knowledgeADRPath = regexp.MustCompile(`(?i)(?:^|/)adr-\d{3,}-.+\.md$`)
var knowledgeADRStatus = regexp.MustCompile(`(?mi)^status:\s*([a-z_-]+)\s*$`)

func containsPathTraversal(path string) bool {
	for _, part := range strings.Split(path, "/") {
		if part == ".." {
			return true
		}
	}
	return false
}

func knowledgeActor(ctx Ctx, owner bool) (*Principal, string, error) {
	p, err := NeedCallsign(ctx)
	if err != nil {
		return nil, "", err
	}
	if owner && (p.CallsignKind != "human" || !p.HumanApproved || p.Role != "owner") {
		return nil, "", Forbidden("DCR 결정에는 승인된 human project owner가 필요하다")
	}
	return p, p.ProjectID, nil
}

func knowledgeReader(ctx Ctx) (*Principal, string, error) {
	if ctx.Principal != nil && ctx.Principal.Kind == "viewer" && ctx.Principal.ProjectID != "" {
		return ctx.Principal, ctx.Principal.ProjectID, nil
	}
	return knowledgeActor(ctx, false)
}

// checkKnowledgeSource validates a source registration — the tool and the approval request use the same check.
// Paths keep their first-seen order without repeats (Python knowledge.check_source).
func checkKnowledgeSource(q queryExec, pid string, rawID, rawRepo, raw any) (string, string, []string, error) {
	id, _ := rawID.(string)
	if !knowledgeID.MatchString(id) {
		return "", "", nil, InvalidField("source_id", "영문·숫자·._- 1~80자")
	}
	items, ok := raw.([]any)
	if !ok || len(items) == 0 || len(items) > 500 {
		return "", "", nil, InvalidField("allowlist", "허용할 markdown 경로가 하나 이상 필요하다")
	}
	paths := []string{}
	seen := map[string]bool{}
	for _, v := range items {
		path, ok := v.(string)
		if !ok || !knowledgePath.MatchString(path) || containsPathTraversal(path) {
			return "", "", nil, InvalidField("allowlist", "안전한 상대 .md 경로가 필요하다")
		}
		if !seen[path] {
			seen[path] = true
			paths = append(paths, path)
		}
	}
	repo, _ := rawRepo.(string)
	var exists int
	if err := q.QueryRow("SELECT COUNT(*) FROM project_alias WHERE project_id=? AND key=?", pid, repo).Scan(&exists); err != nil {
		return "", "", nil, err
	}
	if exists == 0 {
		return "", "", nil, InvalidField("repo_key", "프로젝트에 등록된 저장소 키가 아니다")
	}
	var version int
	err := q.QueryRow("SELECT version FROM knowledge_source WHERE project_id=? AND id=?", pid, id).Scan(&version)
	if err == nil {
		return "", "", nil, VersionConflict(version, map[string]any{"source_id": id})
	}
	if !errors.Is(err, sql.ErrNoRows) {
		return "", "", nil, err
	}
	// 저장소 하나에 원본은 하나 (DB 유일 제약) — 부딪치기 전에 이유를 말한다
	var taken string
	err = q.QueryRow("SELECT id FROM knowledge_source WHERE project_id=? AND repo_key=?", pid, repo).Scan(&taken)
	if err == nil {
		return "", "", nil, &HubError{Status: 409, Code: "source_exists_for_repo", Message: "이 저장소에는 이미 지식 원본이 있다: " + taken, Detail: map[string]any{"source_id": taken}}
	}
	if !errors.Is(err, sql.ErrNoRows) {
		return "", "", nil, err
	}
	return id, repo, paths, nil
}

// KnowledgeSourceRegister registers a project's Git document source — by an approved human owner, or by a callsign
// whose request for the same target an owner approved on the screen (approvalID).
func (s *Store) KnowledgeSourceRegister(ctx Ctx, rawID, rawRepo string, raw any, approvalID string) (map[string]any, error) {
	p, err := NeedCallsign(ctx)
	if err != nil {
		return nil, err
	}
	pid := p.ProjectID
	if approvalID != "" {
		id, repo, paths, cerr := checkKnowledgeSource(s.DB(), pid, rawID, rawRepo, raw)
		if cerr != nil {
			return nil, cerr
		}
		if _, err := s.ApprovalAuthorize(ctx, approvalID, "knowledge_source_register", map[string]any{"source_id": id, "repo_key": repo, "allowlist": paths}); err != nil {
			return nil, err
		}
	} else if p.Kind != "callsign" || p.CallsignKind != "human" || !p.HumanApproved || p.Role != "owner" {
		return nil, Forbidden("지식 원본 등록은 승인된 human 소유자가 하거나, hub_approval_request(action={type: knowledge_source_register, source_id, repo_key, allowlist}) 로 화면 승인을 받은 approval_id 가 필요하다")
	}
	return s.withWriteTx(func(tx *sql.Tx) (map[string]any, error) {
		id, repo, paths, cerr := checkKnowledgeSource(tx, pid, rawID, rawRepo, raw)
		if cerr != nil {
			return nil, cerr
		}
		if approvalID != "" {
			if e := ApprovalConsume(tx, ctx, pid, approvalID); e != nil {
				return nil, e
			}
		}
		blob, _ := json.Marshal(paths)
		if _, e := tx.Exec("INSERT INTO knowledge_source(project_id,id,kind,authority,repo_key,allowlist_json,created_by,created_at) VALUES(?,?,'git','git',?,?,?,?)", pid, id, repo, string(blob), p.Callsign, ctx.Now.Format(time.RFC3339Nano)); e != nil {
			return nil, &HubError{Status: 409, Code: "version_conflict", Message: "knowledge source already exists"}
		}
		projectID := pid
		if e := s.RecordEvent(tx, ctx, &projectID, "knowledge_source", id, "register", nil, map[string]any{"repo_key": repo, "allowlist": paths}, nil); e != nil {
			return nil, e
		}
		return map[string]any{"source_id": id, "repo_key": repo, "allowlist": paths, "authority": "git", "version": 1}, nil
	})
}

func (s *Store) KnowledgeSync(ctx Ctx, sourceID, commit string, raw any) (map[string]any, error) {
	p, pid, err := knowledgeActor(ctx, false)
	if err != nil {
		return nil, err
	}
	if !ShaPattern.MatchString(strings.ToLower(commit)) {
		return nil, InvalidField("commit_sha", "40자리 이하 16진 커밋 SHA가 필요하다")
	}
	items, ok := raw.([]any)
	if !ok || len(items) == 0 || len(items) > 500 {
		return nil, InvalidField("documents", "문서가 1~500개 필요하다")
	}
	var allowedJSON string
	var repo string
	err = s.DB().QueryRow("SELECT allowlist_json,repo_key FROM knowledge_source WHERE project_id=? AND id=? AND enabled=1", pid, sourceID).Scan(&allowedJSON, &repo)
	if err == sql.ErrNoRows {
		return nil, NotFound("knowledge source가 없다: " + sourceID)
	}
	if err != nil {
		return nil, err
	}
	var list []string
	_ = json.Unmarshal([]byte(allowedJSON), &list)
	allowed := map[string]bool{}
	for _, x := range list {
		allowed[x] = true
	}
	type doc struct{ path, title, body string }
	docs := []doc{}
	for i, v := range items {
		m, ok := v.(map[string]any)
		if !ok {
			return nil, InvalidField(fmt.Sprintf("documents[%d]", i), "객체여야 한다")
		}
		path, _ := m["path"].(string)
		title, _ := m["title"].(string)
		body, _ := m["body"].(string)
		if !allowed[path] {
			return nil, Forbidden("source allowlist에 없는 경로: " + path)
		}
		if strings.TrimSpace(title) == "" || strings.TrimSpace(body) == "" || len(body) > 192*1024 {
			return nil, InvalidField("documents", "title/body가 비었거나 본문이 192KB를 넘는다")
		}
		if err = ScanSecrets(body, "body"); err != nil {
			return nil, err
		}
		docs = append(docs, doc{path, strings.TrimSpace(title), body})
	}
	now := ctx.Now.Format(time.RFC3339Nano)
	results := []map[string]any{}
	tx, err := s.DB().Begin()
	if err != nil {
		return nil, err
	}
	defer tx.Rollback()
	for _, d := range docs {
		sum := sha256.Sum256([]byte(d.body))
		digest := hex.EncodeToString(sum[:])
		pending, qerr := tx.Query("SELECT id,target_refs_json FROM decision_change WHERE project_id=? AND status='approved_pending_export' AND adr_path=? AND adr_sha256=?", pid, d.path, digest)
		if qerr != nil {
			return nil, qerr
		}
		for pending.Next() {
			var dcrID, targets string
			if qerr = pending.Scan(&dcrID, &targets); qerr != nil {
				pending.Close()
				return nil, qerr
			}
			_, qerr = tx.Exec("UPDATE decision_change SET status='accepted',version=version+1,updated_at=? WHERE project_id=? AND id=?", now, pid, dcrID)
			if qerr != nil {
				pending.Close()
				return nil, qerr
			}
			var refs []string
			_ = json.Unmarshal([]byte(targets), &refs)
			for _, ref := range refs {
				if strings.HasPrefix(ref, "git:") {
					v := strings.TrimPrefix(ref, "git:")
					if i := strings.Index(v, ":"); i >= 0 {
						oldPath := strings.SplitN(v[i+1:], "@", 2)[0]
						if regexp.MustCompile(`(?:^|/)adr-[^/]+\.md$`).MatchString(oldPath) {
							_, _ = tx.Exec("UPDATE knowledge_revision SET status='superseded' WHERE project_id=? AND path=? AND status='active'", pid, oldPath)
						}
					}
				}
			}
			_, qerr = tx.Exec("INSERT INTO decision_event(project_id,dcr_id,at,actor,op,after_json) VALUES(?,?,?,?,?,?)", pid, dcrID, now, p.Callsign, "publish_confirmed", MustJSON(map[string]any{"path": d.path, "content_sha256": digest, "commit_sha": strings.ToLower(commit)}))
			if qerr != nil {
				pending.Close()
				return nil, qerr
			}
		}
		pending.Close()
		var rev int
		var prior string
		e := tx.QueryRow("SELECT revision,content_sha256 FROM knowledge_revision WHERE project_id=? AND source_id=? AND path=? ORDER BY revision DESC LIMIT 1", pid, sourceID, d.path).Scan(&rev, &prior)
		if e != nil && e != sql.ErrNoRows {
			return nil, e
		}
		if e == nil && prior == digest && func() bool {
			var priorSHA string
			_ = tx.QueryRow("SELECT commit_sha FROM knowledge_revision WHERE project_id=? AND source_id=? AND path=? AND revision=?", pid, sourceID, d.path, rev).Scan(&priorSHA)
			return priorSHA == strings.ToLower(commit)
		}() {
			results = append(results, map[string]any{"path": d.path, "revision": rev, "unchanged": true})
			continue
		}
		if e == nil && strings.Contains("/"+d.path, "/decisions/adr-") {
			var approved int
			_ = tx.QueryRow("SELECT COUNT(*) FROM decision_change WHERE project_id=? AND status='approved_pending_export' AND adr_path=? AND adr_sha256=?", pid, d.path, digest).Scan(&approved)
			if approved == 0 {
				return nil, &HubError{Status: 409, Code: "adr_requires_dcr", Message: "기존 ADR은 DCR 승인으로만 새 판을 만든다: " + d.path}
			}
		}
		if e == nil {
			_, err = tx.Exec("UPDATE knowledge_revision SET status='superseded' WHERE project_id=? AND source_id=? AND path=? AND status='active'", pid, sourceID, d.path)
			if err != nil {
				return nil, err
			}
		}
		rev++
		_, err = tx.Exec("INSERT INTO knowledge_revision(project_id,source_id,path,revision,commit_sha,content_sha256,title,body_md,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)", pid, sourceID, d.path, rev, strings.ToLower(commit), digest, d.title, d.body, p.Callsign, now)
		if err != nil {
			return nil, err
		}
		results = append(results, map[string]any{"path": d.path, "revision": rev, "content_sha256": digest})
	}
	projectID := pid
	if err = s.RecordEvent(tx, ctx, &projectID, "knowledge_source", sourceID, "sync", nil, map[string]any{"commit_sha": strings.ToLower(commit), "documents": results}, nil); err != nil {
		return nil, err
	}
	if err = tx.Commit(); err != nil {
		return nil, err
	}
	return map[string]any{"source_id": sourceID, "repo_key": repo, "commit_sha": strings.ToLower(commit), "documents": results}, nil
}

func (s *Store) KnowledgeSearch(ctx Ctx, query string, limit int) (map[string]any, error) {
	_, pid, err := knowledgeReader(ctx)
	if err != nil {
		return nil, err
	}
	if strings.TrimSpace(query) == "" {
		return nil, InvalidField("query", "검색어가 비었다")
	}
	if limit < 1 {
		limit = 20
	}
	if limit > 100 {
		limit = 100
	}
	words := strings.Fields(strings.ToLower(query))
	hits := []map[string]any{}
	rows, err := s.DB().Query("SELECT r.source_id,r.path,r.revision,r.commit_sha,r.content_sha256,r.title,r.body_md,r.created_at,s.repo_key,r.status FROM knowledge_revision r JOIN knowledge_source s ON s.project_id=r.project_id AND s.id=r.source_id WHERE r.project_id=? AND r.revision=(SELECT MAX(r2.revision) FROM knowledge_revision r2 WHERE r2.project_id=r.project_id AND r2.source_id=r.source_id AND r2.path=r.path) ORDER BY r.path", pid)
	if err != nil {
		return nil, err
	}
	for rows.Next() {
		var source, path, sha, digest, title, body, at, repo, revisionStatus string
		var rev int
		if err = rows.Scan(&source, &path, &rev, &sha, &digest, &title, &body, &at, &repo, &revisionStatus); err != nil {
			rows.Close()
			return nil, err
		}
		hay := strings.ToLower(path + "\n" + title + "\n" + body)
		found := true
		for _, w := range words {
			if !strings.Contains(hay, w) {
				found = false
				break
			}
		}
		if found {
			runes := []rune(body)
			isADR := knowledgeADRPath.MatchString(path) || strings.Contains(body, "adr_id:")
			kind := "design_doc"
			status := revisionStatus
			if isADR {
				kind = "adr"
				if revisionStatus != "superseded" {
					if m := knowledgeADRStatus.FindStringSubmatch(body); len(m) > 1 {
						status = strings.ToLower(m[1])
					}
				}
			}
			hits = append(hits, map[string]any{"ref": "git:" + repo + ":" + path + "@" + sha, "canonical_ref": repo + ":" + path, "kind": kind, "title": title, "path": path, "status": status, "authority": "git", "revision": rev, "source_sha": sha, "content_sha256": digest, "updated_at": at, "relations": []any{}, "excerpt": string(runes[:min(len(runes), 240)])})
		}
	}
	rows.Close()
	wiki, err := s.DB().Query("SELECT path,body_md,version,updated_at FROM wiki_page WHERE project_id=?", pid)
	if err != nil {
		return nil, err
	}
	for wiki.Next() {
		var path, body, at string
		var ver int
		if err = wiki.Scan(&path, &body, &ver, &at); err != nil {
			wiki.Close()
			return nil, err
		}
		hay := strings.ToLower(path + "\n" + body)
		found := true
		for _, w := range words {
			if !strings.Contains(hay, w) {
				found = false
				break
			}
		}
		if found {
			runes := []rune(body)
			sum := sha256.Sum256([]byte(body))
			hits = append(hits, map[string]any{"ref": fmt.Sprintf("hub-wiki:%s@%d", path, ver), "canonical_ref": "hub-wiki:" + path, "kind": "wiki", "title": path, "path": path, "status": "active", "authority": "hub", "revision": ver, "source_sha": nil, "content_sha256": hex.EncodeToString(sum[:]), "updated_at": at, "relations": []any{}, "excerpt": string(runes[:min(len(runes), 240)])})
		}
	}
	wiki.Close()
	dcrRows, err := s.DB().Query("SELECT id,title,rationale,proposal_md,status,version,updated_at FROM decision_change WHERE project_id=? ORDER BY created_at", pid)
	if err != nil {
		return nil, err
	}
	for dcrRows.Next() {
		var id, title, rationale, proposal, status, updated string
		var version int
		if err = dcrRows.Scan(&id, &title, &rationale, &proposal, &status, &version, &updated); err != nil {
			dcrRows.Close()
			return nil, err
		}
		content := rationale + "\n" + proposal
		hay := strings.ToLower(id + "\n" + title + "\n" + content)
		found := true
		for _, w := range words {
			if !strings.Contains(hay, w) {
				found = false
				break
			}
		}
		if found {
			sum := sha256.Sum256([]byte(content))
			hits = append(hits, map[string]any{"ref": fmt.Sprintf("hub-dcr:%s@%d", id, version), "canonical_ref": "hub-dcr:" + id, "kind": "dcr", "title": title, "path": nil, "status": status, "authority": "hub", "revision": version, "source_sha": nil, "content_sha256": hex.EncodeToString(sum[:]), "updated_at": updated, "relations": []any{}, "excerpt": string([]rune(content)[:min(len([]rune(content)), 240)])})
		}
	}
	if err = dcrRows.Err(); err != nil {
		dcrRows.Close()
		return nil, err
	}
	dcrRows.Close()
	memRows, err := s.DB().Query("SELECT id,body_json,version,updated_at FROM memory_entry WHERE project_id=? ORDER BY id", pid)
	if err != nil {
		return nil, err
	}
	for memRows.Next() {
		var id, body, updated string
		var version int
		if err = memRows.Scan(&id, &body, &version, &updated); err != nil {
			memRows.Close()
			return nil, err
		}
		hay := strings.ToLower(id + "\n" + body)
		found := true
		for _, w := range words {
			if !strings.Contains(hay, w) {
				found = false
				break
			}
		}
		if found {
			sum := sha256.Sum256([]byte(body))
			runes := []rune(body)
			hits = append(hits, map[string]any{"ref": fmt.Sprintf("hub-memory:%s@%d", id, version), "canonical_ref": "hub-memory:" + id, "kind": "memory", "title": id, "path": nil, "status": "active", "authority": "hub", "revision": version, "source_sha": nil, "content_sha256": hex.EncodeToString(sum[:]), "updated_at": updated, "relations": []any{}, "excerpt": string(runes[:min(len(runes), 240)])})
		}
	}
	if err = memRows.Err(); err != nil {
		memRows.Close()
		return nil, err
	}
	memRows.Close()
	total := len(hits)
	if len(hits) > limit {
		hits = hits[:limit]
	}
	return map[string]any{"query": query, "hits": hits, "total": total}, nil
}

func (s *Store) DCRCreate(ctx Ctx, title, rationale, proposal string, rawRefs any) (map[string]any, error) {
	p, pid, err := knowledgeActor(ctx, false)
	if err != nil {
		return nil, err
	}
	if strings.TrimSpace(title) == "" || strings.TrimSpace(rationale) == "" || strings.TrimSpace(proposal) == "" {
		return nil, InvalidField("DCR", "title, rationale, proposal이 필요하다")
	}
	if len(title)+len(rationale)+len(proposal) > 150*1024 {
		return nil, InvalidField("DCR", "DCR 본문 합계는 150KB까지")
	}
	for _, v := range []string{title, rationale, proposal} {
		if err = ScanSecrets(v, "DCR"); err != nil {
			return nil, err
		}
	}
	refs := []any{}
	if rawRefs != nil {
		var ok bool
		refs, ok = rawRefs.([]any)
		if !ok {
			return nil, InvalidField("target_refs", "문자열 배열이어야 한다")
		}
	}
	bases := map[string]any{}
	for _, raw := range refs {
		ref, ok := raw.(string)
		if !ok {
			return nil, InvalidField("target_refs", "문자열 배열이어야 한다")
		}
		current, getErr := s.KnowledgeGet(ctx, ref)
		if getErr != nil {
			return nil, getErr
		}
		bases[ref] = map[string]any{"revision": current["revision"], "source_sha": current["source_sha"], "content_sha256": current["content_sha256"]}
	}
	blob, _ := json.Marshal(refs)
	baseBlob, _ := json.Marshal(bases)
	now := ctx.Now.Format(time.RFC3339Nano)
	return s.withWriteTx(func(tx *sql.Tx) (map[string]any, error) {
		var n int
		if e := tx.QueryRow("SELECT COALESCE(MAX(CAST(SUBSTR(id,5) AS INTEGER)),0) FROM decision_change WHERE project_id=?", pid).Scan(&n); e != nil {
			return nil, e
		}
		id := fmt.Sprintf("DCR-%04d", n+1)
		if _, e := tx.Exec("INSERT INTO decision_change(project_id,id,title,rationale,proposal_md,target_refs_json,base_revisions_json,status,author,created_at,updated_at) VALUES(?,?,?,?,?,?,?,'open',?,?,?)", pid, id, strings.TrimSpace(title), strings.TrimSpace(rationale), proposal, string(blob), string(baseBlob), p.Callsign, now, now); e != nil {
			return nil, e
		}
		if _, e := tx.Exec("INSERT INTO decision_event(project_id,dcr_id,at,actor,op,after_json) VALUES(?,?,?,?,?,?)", pid, id, now, p.Callsign, "create", MustJSON(map[string]any{"status": "open", "title": title})); e != nil {
			return nil, e
		}
		return map[string]any{"id": id, "status": "open", "version": 1, "title": strings.TrimSpace(title)}, nil
	})
}

func (s *Store) DCRDecide(ctx Ctx, id string, expected int, outcome, rationale string) (map[string]any, error) {
	p, pid, err := knowledgeActor(ctx, true)
	if err != nil {
		return nil, err
	}
	if outcome != "approve" && outcome != "reject" || strings.TrimSpace(rationale) == "" {
		return nil, InvalidField("decision", "approve/reject와 판단 근거가 필요하다")
	}
	var status, title, context, proposal, targetRefs, baseRefs string
	var version int
	err = s.DB().QueryRow("SELECT status,version,title,rationale,proposal_md,target_refs_json,base_revisions_json FROM decision_change WHERE project_id=? AND id=?", pid, id).Scan(&status, &version, &title, &context, &proposal, &targetRefs, &baseRefs)
	if err == sql.ErrNoRows {
		return nil, NotFound("DCR이 없다: " + id)
	}
	if err != nil {
		return nil, err
	}
	if version != expected {
		return nil, VersionConflict(version, map[string]any{"status": status})
	}
	if status != "open" {
		return nil, &HubError{Status: 409, Code: "invalid_dcr_transition", Message: "open 상태만 결정할 수 있다"}
	}
	if outcome == "approve" {
		var bases map[string]map[string]any
		if err = json.Unmarshal([]byte(baseRefs), &bases); err != nil {
			return nil, err
		}
		for ref, base := range bases {
			if strings.HasPrefix(ref, "hub-wiki:") {
				v := strings.TrimPrefix(ref, "hub-wiki:")
				i := strings.LastIndex(v, "@")
				if i < 0 {
					return nil, InvalidField("target_refs", "invalid wiki revision")
				}
				var revision int
				e := s.DB().QueryRow("SELECT version FROM wiki_page WHERE project_id=? AND path=?", pid, v[:i]).Scan(&revision)
				if e != nil || base["revision"] != float64(revision) && base["revision"] != revision {
					return nil, &HubError{Status: 409, Code: "stale_decision_base", Message: "DCR target가 바뀌었다: " + ref}
				}
			} else {
				v := strings.TrimPrefix(ref, "git:")
				i := strings.Index(v, ":")
				j := strings.LastIndex(v, "@")
				if i < 1 || j <= i {
					return nil, InvalidField("target_refs", "invalid Git revision")
				}
				var sha, digest string
				e := s.DB().QueryRow("SELECT r.commit_sha,r.content_sha256 FROM knowledge_revision r JOIN knowledge_source s ON s.project_id=r.project_id AND s.id=r.source_id WHERE r.project_id=? AND s.repo_key=? AND r.path=? AND r.status='active' ORDER BY r.revision DESC LIMIT 1", pid, v[:i], v[i+1:j]).Scan(&sha, &digest)
				if e != nil || base["source_sha"] != sha || base["content_sha256"] != digest {
					return nil, &HubError{Status: 409, Code: "stale_decision_base", Message: "DCR target가 바뀌었다: " + ref}
				}
			}
		}
	}
	// 승인 = 확정 (소유자 2026-11-26): ADR 은 이 트랜잭션에서 허브 위키 decisions/ 에 쓰이고 DCR 은 곧바로 accepted.
	// Git 저장소에 두는 것은 위키 내보내기의 일이다 — 승인을 Git 커밋에 묶지 않는다 (Python knowledge.dcr_decide 와 같다).
	next := "rejected"
	if outcome == "approve" {
		next = "accepted"
	}
	now := ctx.Now.Format(time.RFC3339Nano)
	adrPath, adrBody, digest, adrIDOut := "", "", "", ""
	var supersededPaths []string
	var wikiWritten map[string]any
	if outcome == "approve" {
		// 번호는 Git 지식 원본과 허브 위키의 ADR 을 모두 본다 — 한쪽만 보면 번호가 겹친다
		rows, queryErr := s.DB().Query("SELECT path,body_md FROM knowledge_revision WHERE project_id=? UNION ALL SELECT path,body_md FROM wiki_page WHERE project_id=?", pid, pid)
		if queryErr != nil {
			return nil, queryErr
		}
		maxADR := 0
		for rows.Next() {
			var path, body string
			if queryErr = rows.Scan(&path, &body); queryErr != nil {
				rows.Close()
				return nil, queryErr
			}
			for _, m := range adrNumberPattern.FindAllStringSubmatch(path+"\n"+body, -1) {
				var n int
				if _, scanErr := fmt.Sscanf(m[1], "%d", &n); scanErr == nil && n > maxADR {
					maxADR = n
				}
			}
		}
		if queryErr = rows.Err(); queryErr != nil {
			rows.Close()
			return nil, queryErr
		}
		rows.Close()
		adrNum := maxADR + 1
		adrSuffix := fmt.Sprintf("%03d", adrNum)
		adrID := fmt.Sprintf("ADR-%03d", adrNum)
		slug := strings.Trim(adrSlugInvalid.ReplaceAllString(strings.ToLower(title), "-"), "-")
		if len(slug) > 48 {
			slug = slug[:48]
		}
		if slug == "" {
			slug = "decision"
		}
		var refs []string
		_ = json.Unmarshal([]byte(targetRefs), &refs)
		supersedes := []string{}
		for _, ref := range refs {
			v := strings.TrimPrefix(ref, "git:")
			i := strings.Index(v, ":")
			j := strings.LastIndex(v, "@")
			if i >= 0 && j > i && regexp.MustCompile(`(?:^|/)adr-[^/]+\.md$`).MatchString(v[i+1:j]) {
				supersedes = append(supersedes, ref)
			}
		}
		supersedesJSON, _ := json.Marshal(supersedes)
		relatedSet := map[string]bool{}
		for _, ref := range refs {
			if v, ok := strings.CutPrefix(ref, "hub-wiki:"); ok {
				if at := strings.LastIndex(v, "@"); at >= 0 {
					v = v[:at]
				}
				relatedSet[strings.TrimSuffix(v, ".md")] = true
			}
		}
		related := []string{}
		for r := range relatedSet {
			related = append(related, r)
		}
		sort.Strings(related)
		relatedJSON, _ := json.Marshal(related)
		day := ctx.Now.Format("2006-01-02")
		adrIDOut = adrID
		adrPath = "decisions/adr-" + adrSuffix + "-" + slug + ".md"
		adrBody = fmt.Sprintf("---\ntype: decision\nstatus: accepted\nadr_id: %s\ndecided_at: %s\nalternatives_considered: []\nrelated_pages: %s\nsupersedes: %s\ndcr: %s\ncreated: %s\nupdated: %s\n---\n\n# %s: %s\n\n## Status\n\n**Accepted** (%s %s 승인 · %s)\n\n## Context\n\n%s\n\n## Decision\n\n%s\n\n## Approval\n\n%s\n",
			adrID, day, string(relatedJSON), string(supersedesJSON), id, day, day, adrID, title, day, p.Callsign, id, context, proposal, strings.TrimSpace(rationale))
		supersededPaths = nil
		for _, ref := range supersedes {
			v := strings.TrimPrefix(ref, "git:")
			if i := strings.Index(v, ":"); i >= 0 {
				v = v[i+1:]
				if at := strings.Index(v, "@"); at >= 0 {
					v = v[:at]
				}
				supersededPaths = append(supersededPaths, v)
			}
		}
		sum := sha256.Sum256([]byte(adrBody))
		digest = hex.EncodeToString(sum[:])
		if err = ScanSecrets(adrBody, "adr"); err != nil {
			return nil, err
		}
	}
	_, err = s.withWriteTx(func(tx *sql.Tx) (map[string]any, error) {
		var result sql.Result
		var e error
		if adrBody != "" {
			result, e = tx.Exec("UPDATE decision_change SET status=?,reviewer=?,decision_rationale=?,adr_path=?,adr_sha256=?,version=version+1,updated_at=? WHERE project_id=? AND id=? AND version=? AND status='open'", next, p.Callsign, strings.TrimSpace(rationale), adrPath, digest, now, pid, id, expected)
		} else {
			result, e = tx.Exec("UPDATE decision_change SET status=?,reviewer=?,decision_rationale=?,version=version+1,updated_at=? WHERE project_id=? AND id=? AND version=? AND status='open'", next, p.Callsign, strings.TrimSpace(rationale), now, pid, id, expected)
		}
		if e != nil {
			return nil, e
		}
		n, _ := result.RowsAffected()
		if n != 1 {
			return nil, &HubError{Status: 409, Code: "version_conflict", Message: "DCR이 다른 요청에서 갱신됐다"}
		}
		if adrBody != "" {
			written, we := s.wikiWritePages(tx, ctx, pid, p.Callsign, []wikiWrite{{path: adrPath, body: adrBody}}, adrIDOut+" — "+id+" 승인")
			if we != nil {
				return nil, we
			}
			wikiWritten = written
			// 대체되는 Git ADR 은 지식 원본에서 superseded 로 (그 문서 자체는 고치지 않는다 — D2)
			for _, old := range supersededPaths {
				if _, we = tx.Exec("UPDATE knowledge_revision SET status='superseded' WHERE project_id=? AND path=? AND status='active'", pid, old); we != nil {
					return nil, we
				}
			}
		}
		if _, e = tx.Exec("INSERT INTO decision_event(project_id,dcr_id,at,actor,op,before_json,after_json) VALUES(?,?,?,?,?,?,?)", pid, id, now, p.Callsign, outcome, MustJSON(map[string]any{"status": "open", "version": version}), MustJSON(map[string]any{"status": next, "rationale": rationale})); e != nil {
			return nil, e
		}
		return map[string]any{"ok": true}, nil
	})
	if err != nil {
		return nil, err
	}
	result := map[string]any{"id": id, "status": next, "version": version + 1}
	if adrBody != "" && wikiWritten != nil {
		pages, _ := wikiWritten["pages"].([]map[string]any)
		wikiVersion := 0
		if len(pages) == 1 {
			wikiVersion, _ = pages[0]["version"].(int)
		}
		result["adr_id"] = adrIDOut
		result["adr_path"] = adrPath
		result["content"] = adrBody
		result["content_sha256"] = digest
		result["wiki"] = map[string]any{"path": adrPath, "version": wikiVersion, "ingest_id": wikiWritten["ingest_id"]}
	}
	return result, nil
}
