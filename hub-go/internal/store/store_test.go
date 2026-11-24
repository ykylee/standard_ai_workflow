package store

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/ykylee/standard_ai_workflow/hub-go/internal/db"
)

func testNow() time.Time {
	return time.Date(2026, 11, 22, 12, 0, 0, 0, time.UTC)
}

func TestGitKeyNormalize(t *testing.T) {
	same := []string{
		"git@github.com:Acme/Demo.git",
		"https://github.com/acme/demo",
		"ssh://git@github.com:22/Acme/Demo.git/",
		"https://user@GitHub.com/acme//demo.git",
	}
	for _, u := range same {
		got, err := NormalizeGitRemote(u)
		if err != nil || got != "github.com/acme/demo" {
			t.Fatalf("NormalizeGitRemote(%q) = %q, %v", u, got, err)
		}
	}
	if got, err := NormalizeGitRemote("https://git.example.org/Team/Repo.git"); err != nil || got != "git.example.org/Team/Repo" {
		t.Fatalf("case-sensitive host: got=%q err=%v", got, err)
	}
	if got, err := NormalizeGitRemote("git@gitlab.com:Grp/Sub/Repo.git"); err != nil || got != "gitlab.com/grp/sub/repo" {
		t.Fatalf("nested path: got=%q err=%v", got, err)
	}
	for _, bad := range []string{"", "file:///srv/repo.git", "/srv/repo", "./repo", `C:\work\repo`, "https://github.com/"} {
		_, err := NormalizeGitRemote(bad)
		he, ok := AsHubError(err)
		if !ok || he.Code != "invalid_remote" {
			t.Fatalf("expected invalid_remote for %q, got %v", bad, err)
		}
	}
}

func TestStoreLifecycle(t *testing.T) {
	dir := t.TempDir()
	dbPath := filepath.Join(dir, "hub.db")
	now := testNow()
	if _, err := db.OpenDB(dbPath, now); err != nil {
		t.Fatalf("OpenDB failed: %v", err)
	}
	st, err := New(dbPath)
	if err != nil {
		t.Fatalf("New store failed: %v", err)
	}
	defer st.Close()

	reg, err := st.RegisterProject(Ctx{Now: now, Via: "http"}, "git@github.com:Acme/Demo.git", "Demo", "claude-a", "human", "", "")
	if err != nil {
		t.Fatalf("RegisterProject failed: %v", err)
	}
	tokA := reg["token"].(string)
	pid := reg["project_id"].(string)
	if !strings.HasPrefix(tokA, "wfh_") || reg["role"] != "owner" {
		t.Fatalf("unexpected reg: %+v", reg)
	}

	look, err := st.LookupProject("https://github.com/acme/demo")
	if err != nil || look["project_id"] != pid {
		t.Fatalf("LookupProject=%+v err=%v", look, err)
	}

	// Duplicate alias rejected 409
	_, dupErr := st.RegisterProject(Ctx{Now: now, Via: "http"}, "ssh://git@github.com/acme/demo", "x", "other-a", "agent", "", "")
	if he, _ := AsHubError(dupErr); he == nil || he.Status != 409 || he.Code != "project_exists" {
		t.Fatalf("expected 409 project_exists, got %v", dupErr)
	}

	join, err := st.RegisterCallsign(Ctx{Now: now, Via: "http"}, pid, "codex-b", "human", "", "")
	if err != nil {
		t.Fatalf("RegisterCallsign failed: %v", err)
	}
	tokB := join["token"].(string)

	// Token plaintext must not exist on disk
	raw, _ := os.ReadFile(dbPath)
	if strings.Contains(string(raw), tokA) || strings.Contains(string(raw), tokB) {
		t.Fatalf("token plaintext leaked in DB file")
	}

	pA, err := st.Authenticate(tokA, &now, "test-cli")
	if err != nil || pA == nil || pA.Callsign != "claude-a" {
		t.Fatalf("auth A failed: %+v %v", pA, err)
	}
	pB, err := st.Authenticate(tokB, &now, "")
	if err != nil || pB == nil || pB.Callsign != "codex-b" {
		t.Fatalf("auth B failed: %+v %v", pB, err)
	}

	ctxA := Ctx{Now: now, Via: "http", Principal: pA}
	ctxB := Ctx{Now: now, Via: "http", Principal: pB}

	// Overlong Korean title (>200 runes)
	_, err = st.TaskCreate(ctxA, map[string]any{"title": strings.Repeat("가", 201)}, "", nil)
	if he, _ := AsHubError(err); he == nil || he.Code != "invalid_field" || !strings.Contains(he.Message, "200") {
		t.Fatalf("expected invalid_field 200, got %v", err)
	}

	created, err := st.TaskCreate(ctxA, map[string]any{"title": "첫 task"}, "", nil)
	if err != nil {
		t.Fatalf("TaskCreate failed: %v", err)
	}
	id1 := created["task"].(map[string]any)["id"].(string)

	// Update + 409 conflict
	upd, err := st.TaskUpdate(ctxA, id1, 1, map[string]any{"title": "고친 제목"}, "", nil)
	if err != nil || upd["task"].(map[string]any)["version"] != 2 {
		t.Fatalf("TaskUpdate failed: %+v %v", upd, err)
	}
	_, err = st.TaskUpdate(ctxB, id1, 1, map[string]any{"title": "낡은"}, "", nil)
	if he, _ := AsHubError(err); he == nil || he.Status != 409 || he.Code != "version_conflict" {
		t.Fatalf("expected 409 version_conflict, got %v", err)
	}

	// Claim / clash / release / progress idempotency
	if _, err := st.TaskClaim(ctxA, id1, ""); err != nil {
		t.Fatalf("claim A failed: %v", err)
	}
	if _, err := st.TaskClaim(ctxB, id1, ""); err == nil {
		t.Fatalf("expected already_claimed")
	}
	if _, err := st.TaskRelease(ctxA, id1, ""); err != nil {
		t.Fatalf("release A failed: %v", err)
	}
	if _, err := st.TaskClaim(ctxB, id1, ""); err != nil {
		t.Fatalf("claim B failed: %v", err)
	}
	p1, err := st.TaskProgress(ctxB, id1, "구현 중", "r-1")
	if err != nil || p1["replayed"] != nil {
		t.Fatalf("progress 1 failed: %+v %v", p1, err)
	}
	p2, err := st.TaskProgress(ctxB, id1, "구현 중", "r-1")
	if err != nil || p2["replayed"] != true {
		t.Fatalf("progress 2 expected replay: %+v %v", p2, err)
	}

	// Revoke callsign B -> invalidates token + releases task
	rev, err := st.RevokeCallsign(Ctx{Now: now, Via: "admin"}, pid, "codex-b")
	if err != nil {
		t.Fatalf("RevokeCallsign failed: %v", err)
	}
	if rel := rev["released_tasks"].([]string); len(rel) != 1 || rel[0] != id1 {
		t.Fatalf("unexpected released_tasks: %+v", rev)
	}
	if gone, err := st.Authenticate(tokB, nil, ""); err != nil || gone != nil {
		t.Fatalf("revoked token still accepted: %+v %v", gone, err)
	}
}

func TestTaskListPageFiltersAndPagination(t *testing.T) {
	dbPath := filepath.Join(t.TempDir(), "hub.db")
	now := time.Date(2026, 11, 24, 12, 0, 0, 0, time.UTC)
	if _, err := db.OpenDB(dbPath, now); err != nil {
		t.Fatal(err)
	}
	st, err := New(dbPath)
	if err != nil {
		t.Fatal(err)
	}
	defer st.Close()
	reg, err := st.RegisterProject(Ctx{Now: now, Via: "test"}, "https://github.com/acme/task-page", "Task page", "owner-human", "human", "", "")
	if err != nil {
		t.Fatal(err)
	}
	p, err := st.Authenticate(reg["token"].(string), &now, "test")
	if err != nil {
		t.Fatal(err)
	}
	ctx := Ctx{Now: now, Via: "test", Principal: p}
	category := map[string]any{"category": map[string]any{"level_1": "Product", "level_2": "Hub", "level_3": "Listing"}}
	for _, item := range []map[string]any{
		{"title": "page one", "wbs": "M-061/WBS-61.1", "fields": category},
		{"title": "page two", "wbs": "M-061/WBS-61.2", "fields": category},
		{"title": "unlinked", "fields": map[string]any{"category": map[string]any{"level_1": "Operations", "level_2": "Support", "level_3": "Triage"}}},
	} {
		if _, err := st.TaskCreate(ctx, item, "", nil); err != nil {
			t.Fatal(err)
		}
	}
	filters := map[string]string{"roadmap": "linked", "milestone": "M-061", "category_level_1": "Product"}
	first, err := st.TaskListPage(ctx, filters, 1, 0)
	if err != nil {
		t.Fatal(err)
	}
	if first["total"] != 2 || len(first["tasks"].([]map[string]any)) != 1 || first["offset"] != 0 {
		t.Fatalf("first page=%#v", first)
	}
	second, err := st.TaskListPage(ctx, filters, 1, 1)
	if err != nil {
		t.Fatal(err)
	}
	if second["total"] != 2 || len(second["tasks"].([]map[string]any)) != 1 || second["offset"] != 1 {
		t.Fatalf("second page=%#v", second)
	}
	if first["tasks"].([]map[string]any)[0]["id"] == second["tasks"].([]map[string]any)[0]["id"] {
		t.Fatal("pagination repeated a task")
	}
	if _, err := st.TaskListPage(ctx, map[string]string{"milestone": "bad"}, 25, 0); err == nil {
		t.Fatal("invalid milestone accepted")
	}
}
