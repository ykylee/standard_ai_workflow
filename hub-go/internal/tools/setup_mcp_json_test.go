package tools

import (
	"encoding/json"
	"strings"
	"testing"
)

// Claude Code 의 .mcp.json 은 headersHelper 로 .workflow-hub/env 의 콜사인 토큰을 읽는다 — 셸 환경 변수 없이 붙는 길.
// 승인된 일반 프로필 경로에는 하네스가 모를 수 있는 칸을 넣지 않는다. 어느 쪽이든 토큰 값은 설정에 없다.
func TestSetupMCPJSONHeadersHelper(t *testing.T) {
	read := func(content string) map[string]any {
		var data map[string]any
		if err := json.Unmarshal([]byte(content), &data); err != nil {
			t.Fatalf("not JSON: %v", err)
		}
		return data["mcpServers"].(map[string]any)["workflow-hub"].(map[string]any)
	}
	claude, err := setupMCPJSON(`{"mcpServers":{"other":{"type":"stdio"}}}`, "https://hub.example/mcp")
	if err != nil {
		t.Fatal(err)
	}
	server := read(claude)
	if server["headersHelper"] != "python3 .workflow-hub/hub_client.py mcp-headers" {
		t.Fatalf("headersHelper = %v", server["headersHelper"])
	}
	if server["headers"].(map[string]any)["Authorization"] != "Bearer ${WORKFLOW_HUB_TOKEN}" {
		t.Fatalf("static header fallback lost: %v", server["headers"])
	}
	if !strings.Contains(claude, `"other"`) {
		t.Fatal("existing servers were dropped")
	}
	profile, err := setupMCPJSONAtPath("", "https://hub.example/mcp", "harness-mcp.json")
	if err != nil {
		t.Fatal(err)
	}
	if _, ok := read(profile)["headersHelper"]; ok {
		t.Fatal("generic profile config must not carry headersHelper")
	}
}
