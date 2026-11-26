package tools

import (
	"strings"
	"testing"

	"github.com/ykylee/standard_ai_workflow/hub-go/internal/store"
)

// TestGuideRegionBudgetEdges — 렌더 영역 예산 12KiB · 120줄: 정확히는 통과, 1B · 1줄 넘으면 422
// (TASK-2026-11-26-claude-plex-027, Python check_hub_bootstrap case 10 와 같은 판정).
func TestGuideRegionBudgetEdges(t *testing.T) {
	render := func(body string) (string, error) {
		return renderGuideAtEntry("claude-code", "CLAUDE.md", "P-x", "Demo", body, 1)
	}
	base, err := render("x")
	if err != nil {
		t.Fatal(err)
	}
	exactBytes := strings.Repeat("x", 1+store.GuideRegionBudgetBytes-len(base))
	if r, err := render(exactBytes); err != nil || len(r) != store.GuideRegionBudgetBytes {
		t.Fatalf("exact bytes: len=%d err=%v", len(r), err)
	}
	if _, err := render(exactBytes + "x"); err == nil || !strings.Contains(err.Error(), "entry_budget_exceeded") {
		t.Fatalf("over bytes: want entry_budget_exceeded, got %v", err)
	}
	two, err := render("a\nb")
	if err != nil {
		t.Fatal(err)
	}
	lines := strings.Count(two, "\n")
	parts := make([]string, 2+store.GuideRegionBudgetLines-lines)
	for i := range parts {
		parts[i] = "a"
	}
	exactLines := strings.Join(parts, "\n")
	if r, err := render(exactLines); err != nil || strings.Count(r, "\n") != store.GuideRegionBudgetLines {
		t.Fatalf("exact lines: lines=%d err=%v", strings.Count(r, "\n"), err)
	}
	if _, err := render(exactLines + "\na"); err == nil || !strings.Contains(err.Error(), "entry_budget_exceeded") {
		t.Fatalf("over lines: want entry_budget_exceeded, got %v", err)
	}
	if err := store.GuideRegionOverBudget("X", strings.Repeat("y\n", store.GuideRegionBudgetLines)); err != nil {
		t.Fatalf("store judge at line budget: %v", err)
	}
}
