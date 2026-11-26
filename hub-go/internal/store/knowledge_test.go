package store

import (
	"path/filepath"
	"testing"
	"time"

	"github.com/ykylee/standard_ai_workflow/hub-go/internal/db"
)

func TestKnowledgeAndDCRLifecycle(t *testing.T) {
	now := time.Date(2026, 11, 24, 0, 0, 0, 0, time.UTC)
	path := filepath.Join(t.TempDir(), "knowledge.db")
	if _, err := db.OpenDB(path, now); err != nil {
		t.Fatal(err)
	}
	st, err := New(path)
	if err != nil {
		t.Fatal(err)
	}
	defer st.Close()
	ctx := Ctx{Now: now, Via: "test"}
	reg, err := st.RegisterProject(ctx, "git@github.com:acme/knowledge.git", "Knowledge", "owner-human", "human", "", "")
	if err != nil {
		t.Fatal(err)
	}
	owner, err := st.Authenticate(reg["token"].(string), &now, "test")
	if err != nil {
		t.Fatal(err)
	}
	ownerCtx := Ctx{Now: now, Via: "test", Principal: owner}
	join, err := st.RegisterCallsign(ownerCtx, reg["project_id"].(string), "agent-writer", "agent", "", "")
	if err != nil {
		t.Fatal(err)
	}
	agent, err := st.Authenticate(join["token"].(string), &now, "test")
	if err != nil {
		t.Fatal(err)
	}
	agentCtx := Ctx{Now: now, Via: "test", Principal: agent}
	oldPath := "ai-workflow/wiki/decisions/adr-036-old-choice.md"
	adrPath := "ai-workflow/wiki/decisions/adr-037-test-choice.md"
	repo := "github.com/acme/knowledge"
	if _, err = st.KnowledgeSourceRegister(ownerCtx, "repo-docs", repo, []any{"docs/design.md", oldPath, adrPath}, ""); err != nil {
		t.Fatal(err)
	}
	sha := "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
	doc := map[string]any{"path": "docs/design.md", "title": "Design", "body": "# Design\nShared project knowledge baseline.\n"}
	oldADR := map[string]any{"path": oldPath, "title": "ADR-036 Old Choice", "body": "---\nadr_id: ADR-036\nstatus: accepted\n---\n\n# Old Choice\n"}
	if _, err = st.KnowledgeSync(agentCtx, "repo-docs", sha, []any{doc, oldADR}); err != nil {
		t.Fatal(err)
	}
	search, err := st.KnowledgeSearch(agentCtx, "shared baseline", 20)
	if err != nil {
		t.Fatal(err)
	}
	if search["total"] != 1 {
		t.Fatalf("search=%#v", search)
	}
	oldRef := "git:" + repo + ":" + oldPath + "@" + sha
	dcr, err := st.DCRCreate(agentCtx, "Test Choice", "Current rule is insufficient.", "Adopt the new rule.", []any{oldRef})
	if err != nil {
		t.Fatal(err)
	}
	id := dcr["id"].(string)
	if _, err = st.DCRDecide(agentCtx, id, 1, "approve", "should fail"); err == nil {
		t.Fatal("unapproved agent decided DCR")
	}
	approved, err := st.DCRDecide(ownerCtx, id, 1, "approve", "Approved by owner.")
	if err != nil {
		t.Fatal(err)
	}
	// 승인 = 확정 (소유자 2026-11-26): 같은 트랜잭션에서 위키 ADR 이 생기고 DCR 은 accepted
	if approved["status"] != "accepted" || approved["adr_path"] != "decisions/adr-037-test-choice.md" || approved["adr_id"] != "ADR-037" {
		t.Fatalf("approval=%#v", approved)
	}
	page, err := st.WikiGet(agentCtx, "decisions/adr-037-test-choice.md")
	if err != nil {
		t.Fatal(err)
	}
	if page["body"] != approved["content"] {
		t.Fatalf("wiki ADR body differs: %#v", page["body"])
	}
	detail, err := st.DCRGet(agentCtx, id)
	if err != nil {
		t.Fatal(err)
	}
	if detail["status"] != "accepted" {
		t.Fatalf("DCR status=%v", detail["status"])
	}
	old, err := st.KnowledgeGet(agentCtx, oldRef)
	if err != nil {
		t.Fatal(err)
	}
	if old["status"] != "superseded" {
		t.Fatalf("old ADR state=%v", old["status"])
	}
}
