package httpapi

import (
	"fmt"
	"html"
	"io/fs"
	"net/http"
	"path"
	"strings"

	"github.com/ykylee/standard_ai_workflow/hub-go/internal/assets"
	"github.com/ykylee/standard_ai_workflow/hub-go/internal/tools"
)

type harnessGuide struct {
	name      string
	entryFile string
	before    string
	after     string
}

func guides(publicURL string) []harnessGuide {
	mcp := strings.TrimRight(publicURL, "/") + "/mcp"
	return []harnessGuide{
		{name: "claude-code", entryFile: "CLAUDE.md", before: "claude mcp add --transport http workflow-hub " + mcp,
			after: "부트스트랩이 .mcp.json 에 headersHelper 'python3 .workflow-hub/hub_client.py mcp-headers' 를 쓴다 (Claude Code 는 이 파일 쓰기에 사람 승인을 요구한다) — 콜사인 토큰을 .workflow-hub/env 에서 읽으므로 환경 변수 없이 다시 시작"},
		{name: "codex", entryFile: "AGENTS.md", before: "codex mcp add workflow-hub --url " + mcp,
			after: "부트스트랩이 --bearer-token-env-var WORKFLOW_HUB_TOKEN 로 다시 등록한다. 대화형은 허브 도구마다 승인을 묻고, 비대화(codex exec)는 실행마다 -c 'mcp_servers.workflow-hub.default_tools_approval_mode=\"approve\"' 를 줘야 허브 도구를 부른다 (부트스트랩 때도 같다 — 자동 승인은 사람의 선택이라 설정에 쓰지 않는다)"},
		{name: "minimax-code", entryFile: "MiniMax.md", before: "저장소 뿌리의 .mcp.json 에 {\"mcpServers\": {\"workflow-hub\": {\"type\": \"http\", \"url\": \"" + mcp + "\"}}}",
			after: "부트스트랩이 같은 .mcp.json 에 환경 변수 참조 헤더를 더한다 (Claude Code 와 같은 파일)"},
		{name: "antigravity", entryFile: "ANTIGRAVITY.md", before: "agy mcp add workflow-hub " + mcp,
			after: "주의: Antigravity 는 헤더의 환경 변수 참조를 확장하지 않는다. 부트스트랩이 토큰을 사용자 범위 ~/.gemini/config/mcp_config.json 에 평문으로 넣는 명령을 경고와 함께 낸다 — 그 파일을 공유하지 않는다"},
	}
}

func (s *Server) handleGuidePage(w http.ResponseWriter, r *http.Request) {
	if r.URL.Path != "/" {
		http.NotFound(w, r)
		return
	}
	s.writeHubHeaders(w)
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	w.Header().Set("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; frame-ancestors 'none'")
	w.Header().Set("Referrer-Policy", "same-origin")
	base := html.EscapeString(s.cfg.PublicURL)
	var rows strings.Builder
	for _, h := range guides(s.cfg.PublicURL) {
		fmt.Fprintf(&rows, "<section><h2>%s <small>(%s)</small></h2><p>① 등록 전</p><pre>%s</pre><p>② 셋업 뒤</p><p>%s</p></section>",
			html.EscapeString(h.name), html.EscapeString(h.entryFile), html.EscapeString(h.before), html.EscapeString(h.after))
	}
	fmt.Fprintf(w, "<!doctype html><html lang=\"ko\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"><title>워크플로우 허브</title><style>body{font-family:system-ui,sans-serif;max-width:860px;margin:2rem auto;padding:0 16px;line-height:1.55}pre{background:#f4f4f5;padding:.6rem .8rem;overflow-x:auto;white-space:pre-wrap;word-break:break-all}@media (prefers-color-scheme:dark){body{background:#111;color:#eee}pre{background:#222}}</style></head><body>")
	fmt.Fprintf(w, "<h1>워크플로우 허브</h1><p>Hub %s · kit 호환 %s · 계약 %s · 주소 <code>%s</code> · <a href=\"ui/\">화면</a></p>", html.EscapeString(s.cfg.HubVersion), html.EscapeString(tools.KitVersion), html.EscapeString(tools.Contract), base)
	fmt.Fprintf(w, "<p><b>가장 쉬운 길</b>: 에이전트에게 \"<code>%s/setup.md</code> 를 읽고 이 저장소를 셋업해\" 라고 한다 (<a href=\"setup.md\">에이전트용 절차</a>).</p>", html.EscapeString(strings.TrimRight(s.cfg.PublicURL, "/")))
	fmt.Fprint(w, "<p>저장소 뿌리에서 하네스에 허브 MCP 를 등록한 뒤, 에이전트에게 \"워크플로우 허브에 이 저장소를 등록하고 셋업해\" 라고 한다. 부트스트랩 도구가 프로젝트 등록(또는 합류) · <code>.gitignore</code> 확인 · 토큰 저장 · 진입 파일 · 하네스 설정을 차례로 지시한다. PC에서 원격으로 하네스를 실행할 때만 선택형 로컬 중계를 설정한다.</p>")
	w.Write([]byte(rows.String()))
	fmt.Fprint(w, "</body></html>")
}

func (s *Server) handleSetupMarkdown(w http.ResponseWriter, _ *http.Request) {
	s.writeHubHeaders(w)
	w.Header().Set("Content-Type", "text/markdown; charset=utf-8")
	base := strings.TrimRight(s.cfg.PublicURL, "/")
	var harnessLines strings.Builder
	for _, h := range guides(s.cfg.PublicURL) {
		fmt.Fprintf(&harnessLines, "- `%s` (진입 파일 `%s`) — 허브 MCP 등록: `%s`\n", h.name, h.entryFile, h.before)
	}
	body := strings.NewReplacer("{{BASE}}", base, "{{HUB_VERSION}}", s.cfg.HubVersion, "{{KIT_VERSION}}", tools.KitVersion, "{{HARNESS_LINES}}", harnessLines.String()).Replace(assets.SetupMarkdown)
	_, _ = w.Write([]byte(body))
}

var screenHeaders = map[string]string{
	"Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'",
	"Referrer-Policy":         "same-origin",
	"X-Content-Type-Options":  "nosniff",
}

func (s *Server) handleUIRedirect(w http.ResponseWriter, _ *http.Request) {
	w.Header().Set("Location", "ui/")
	w.WriteHeader(http.StatusTemporaryRedirect)
}

func (s *Server) handleUIStatic(w http.ResponseWriter, r *http.Request) {
	name := r.PathValue("name")
	files := map[string]string{
		"":            "text/html; charset=utf-8",
		"hub.js":      "text/javascript; charset=utf-8",
		"hub.css":     "text/css; charset=utf-8",
		"favicon.svg": "image/svg+xml",
	}
	mediaType, ok := files[name]
	if !ok || (name != "" && path.Base(name) != name) {
		writeJSONResponse(w, http.StatusNotFound, map[string]any{"error_code": "not_found", "message": "없는 자산", "detail": map[string]any{}})
		return
	}
	fileName := name
	if fileName == "" {
		fileName = "index.html"
	}
	for k, v := range screenHeaders {
		w.Header().Set(k, v)
	}
	w.Header().Set("Cache-Control", "no-cache")
	w.Header().Set("Content-Type", mediaType)
	data, err := fs.ReadFile(assets.StaticFS, "static/"+fileName)
	if err != nil {
		writeJSONResponse(w, http.StatusNotFound, map[string]any{"error_code": "not_found", "message": "없는 자산", "detail": map[string]any{}})
		return
	}
	w.WriteHeader(http.StatusOK)
	_, _ = w.Write(data)
}
