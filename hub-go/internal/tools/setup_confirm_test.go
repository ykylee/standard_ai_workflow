package tools

import (
	"errors"
	"testing"
	"time"

	"github.com/ykylee/standard_ai_workflow/hub-go/internal/store"
)

func TestSetupConfirmBootstrapToComplete(t *testing.T) {
	st := openTestStore(t)
	now := time.Date(2026, 11, 24, 12, 0, 0, 0, time.UTC)
	ctx := store.Ctx{Now: now, Via: "http", PublicURL: "https://hub.example/workflow"}
	reg, err := st.RegisterProject(ctx, "https://github.com/acme/confirm", "Confirm", "owner-a", "human", "", "")
	if err != nil {
		t.Fatal(err)
	}
	pid, token := reg["project_id"].(string), reg["token"].(string)
	call := func(name string, extra map[string]any) map[string]any {
		t.Helper()
		args := map[string]any{"project_id": pid, "token": token}
		for k, v := range extra {
			args[k] = v
		}
		out, err := Call(st, name, args, ctx)
		if err != nil {
			t.Fatalf("%s: %v", name, err)
		}
		return out
	}
	planArgs := map[string]any{"harnesses": []any{"codex"}, "scan": map[string]any{"files": map[string]any{}}}
	ignore := func(output string) map[string]any {
		return map[string]any{"checks": []any{map[string]any{"name": "check_ignore", "rc": 0, "output": output}}}
	}
	call("hub_setup_plan", planArgs)
	bad := call("hub_setup_confirm", ignore(".gitignore:1:!/.workflow-hub/\t.workflow-hub/env\n"))
	if bad["error_code"] != "ignore_not_effective" || bad["setup_complete"] != false {
		t.Fatalf("negated rule must not confirm: %#v", bad)
	}
	if plan := call("hub_setup_plan", planArgs); plan["stage"] != "gitignore" {
		t.Fatalf("token instruction leaked before gitignore confirmation: %#v", plan["stage"])
	}
	if got := call("hub_setup_confirm", ignore(".gitignore:1:/.workflow-hub/\t.workflow-hub/env\n")); len(got["confirmed"].([]string)) != 1 {
		t.Fatalf("gitignore not confirmed: %#v", got)
	}
	plan := call("hub_setup_plan", planArgs)
	files, checks := []any{}, []any{}
	for _, raw := range plan["steps"].([]any) {
		step := raw.(map[string]any)
		if step["op"] == "write" {
			files = append(files, map[string]any{"path": step["path"], "sha256": step["sha256_after"]})
		}
	}
	wrong := append([]any{map[string]any{"path": ".workflow-hub/env", "sha256": "bad"}}, files[1:]...)
	if got := call("hub_setup_confirm", map[string]any{"files": wrong, "checks": checks}); got["setup_complete"] != false {
		t.Fatalf("hash mismatch must not complete: %#v", got)
	}
	failed := []any{map[string]any{"name": "harness:codex", "rc": 1, "output": ""}}
	if got := call("hub_setup_confirm", map[string]any{"files": files, "checks": failed}); got["setup_complete"] != false {
		t.Fatalf("failed command must not complete: %#v", got)
	}
	passed := []any{map[string]any{"name": "harness:codex", "rc": 0, "output": ""}}
	if got := call("hub_setup_confirm", map[string]any{"checks": passed}); got["setup_complete"] != true {
		t.Fatalf("setup should complete: %#v", got)
	}
	var seen string
	if err := st.DB().QueryRow("SELECT COALESCE(guide_version_seen,'') FROM callsign WHERE project_id=? AND id='owner-a' AND setup_complete=1", pid).Scan(&seen); err != nil || seen == "" {
		t.Fatalf("callsign completion not recorded: %q %v", seen, err)
	}
	for _, c := range []struct {
		args map[string]any
		code string
	}{
		{map[string]any{"project_id": pid, "token": "nope"}, "unauthorized"},
		{map[string]any{"project_id": "P-other", "token": token}, "forbidden"},
		{map[string]any{"project_id": pid, "token": token, "files": []any{map[string]any{"path": "a", "x": 1}}}, "invalid_field"},
		{map[string]any{"project_id": pid, "token": token, "checks": []any{map[string]any{"name": "a", "rc": "x"}}}, "invalid_field"},
	} {
		_, err := Call(st, "hub_setup_confirm", c.args, ctx)
		var he *store.HubError
		if !errors.As(err, &he) || he.Code != c.code {
			t.Fatalf("want %s got %v", c.code, err)
		}
	}
}

func TestWikiReadTools(t *testing.T) {
	st := openTestStore(t)
	now := time.Date(2026, 11, 24, 12, 0, 0, 0, time.UTC)
	project := func(name string) store.Ctx {
		reg, err := st.RegisterProject(store.Ctx{Now: now, Via: "test"}, "https://github.com/acme/"+name, name, "owner-"+name, "human", "", "")
		if err != nil {
			t.Fatal(err)
		}
		p, err := st.Authenticate(reg["token"].(string), &now, "test")
		if err != nil {
			t.Fatal(err)
		}
		return store.Ctx{Now: now, Via: "http", Principal: p}
	}
	a, b := project("wa"), project("wb")
	if _, err := Call(st, "hub_wiki_ingest", map[string]any{"summary": "첫 수집", "pages": []any{
		map[string]any{"path": "concepts/foo.md", "body": "# 푸 개념\n\n허브 중계 설명이 여기에 있다."},
		map[string]any{"path": "top.md", "body": "허브 첫 장"},
		map[string]any{"path": "zeta/x.md", "body": "---\ntitle: \"제트\"\n---\n본문"},
	}}, a); err != nil {
		t.Fatal(err)
	}
	get, err := Call(st, "hub_wiki_get", map[string]any{"path": "concepts/foo.md"}, a)
	if err != nil || get["version"] != 1 {
		t.Fatalf("get: %#v %v", get, err)
	}
	list, err := Call(st, "hub_wiki_list", map[string]any{"prefix": "zeta/"}, a)
	if err != nil || len(list["pages"].([]map[string]any)) != 1 || list["pages"].([]map[string]any)[0]["title"] != "제트" {
		t.Fatalf("list: %#v %v", list, err)
	}
	hit, err := Call(st, "hub_wiki_search", map[string]any{"query": "중계 허브"}, a)
	if err != nil || hit["total"] != 1 || hit["hits"].([]map[string]any)[0]["snippet"] != "# 푸 개념  허브 중계 설명이 여기에 있다." {
		t.Fatalf("search: %#v %v", hit, err)
	}
	index, err := Call(st, "hub_wiki_get", map[string]any{"path": "index.md"}, a)
	want := "# Master Knowledge Index\n\n## Concepts\n\n### [[concepts/foo]] {#foo}\n\n## zeta\n\n### [[zeta/x]] {#x}\n\n## Meta\n\n### [[top]] {#top}\n"
	if err != nil || index["body"] != want {
		t.Fatalf("index: %q %v", index["body"], err)
	}
	for _, c := range []struct {
		ctx  store.Ctx
		path string
		code string
	}{{b, "concepts/foo.md", "not_found"}, {a, "../x.md", "invalid_field"}, {store.Ctx{Now: now, Via: "http"}, "concepts/foo.md", ""}} {
		_, err := Call(st, "hub_wiki_get", map[string]any{"path": c.path}, c.ctx)
		var he *store.HubError
		if !errors.As(err, &he) || (c.code != "" && he.Code != c.code) {
			t.Fatalf("%s: want %s got %v", c.path, c.code, err)
		}
	}
	if other, err := Call(st, "hub_wiki_search", map[string]any{"query": "허브"}, b); err != nil || other["total"] != 0 {
		t.Fatalf("cross-project leak: %#v %v", other, err)
	}
}
