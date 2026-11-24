package tools

import (
	"errors"
	"testing"
	"time"

	"github.com/ykylee/standard_ai_workflow/hub-go/internal/store"
)

// 광고한 도구는 모두 구현돼 있어야 한다 — 3.2.1 은 셋업 도구가 501 이라 새 환경이 붙지 못했다.
func TestEveryAdvertisedToolIsImplemented(t *testing.T) {
	st := openTestStore(t)
	now := time.Date(2026, 11, 24, 12, 0, 0, 0, time.UTC)
	reg, err := st.RegisterProject(store.Ctx{Now: now, Via: "test"}, "https://github.com/acme/parity", "Parity", "owner-a", "human", "", "")
	if err != nil {
		t.Fatal(err)
	}
	token := reg["token"].(string)
	p, err := st.Authenticate(token, &now, "test")
	if err != nil {
		t.Fatal(err)
	}
	ctx := store.Ctx{Now: now, Via: "http", Principal: p, PublicURL: "https://hub.example"}
	fill := map[string]any{"string": "x", "integer": 1, "boolean": false, "array": []any{"x"}, "object": map[string]any{}}
	for _, spec := range ToolOrder {
		name := spec.Name
		args := map[string]any{}
		for _, key := range spec.Required {
			kind, _ := spec.Properties[key]["type"].(string)
			args[key] = fill[kind]
		}
		_, err := Call(st, name, args, ctx)
		var he *store.HubError
		if errors.As(err, &he) && he.Code == "not_implemented_in_go" {
			t.Errorf("%s is advertised but not implemented", name)
		}
	}
}
