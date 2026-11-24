package httpapi

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"

	"github.com/ykylee/standard_ai_workflow/hub-go/internal/assets"
	"github.com/ykylee/standard_ai_workflow/hub-go/internal/mcpserver"
	"github.com/ykylee/standard_ai_workflow/hub-go/internal/store"
	"github.com/ykylee/standard_ai_workflow/hub-go/internal/tools"
	"github.com/ykylee/standard_ai_workflow/hub-go/internal/waiter"
)

const (
	// MaxBody matches Python hub.app.MAX_BODY (256 KiB).
	MaxBody = 256 * 1024
)

// BigBodyTools matches Python hub.app.BIG_BODY_TOOLS per-tool request caps.
var BigBodyTools = map[string]int{
	"hub_migrate_plan":   8 * 1024 * 1024,
	"hub_migrate_import": 8 * 1024 * 1024,
	"hub_project_import": 64 * 1024 * 1024,
}

// Config configures the HTTP server router.
type Config struct {
	Store        *store.Store
	HubVersion   string
	PublicURL    string
	Exposure     string
	WebTokenName string
	Clock        func() time.Time
}

// Server wraps the public guide, health, bootstrap, tool, and MCP HTTP routes.
type Server struct {
	cfg Config
	mux *http.ServeMux
}

// New constructs a configured HTTP handler for workflow-hub.
func New(cfg Config) *Server {
	if cfg.HubVersion == "" {
		cfg.HubVersion = "dev"
	}
	if cfg.Exposure == "" {
		cfg.Exposure = "loopback"
	}
	if cfg.Clock == nil {
		cfg.Clock = func() time.Time { return time.Now().UTC().Truncate(time.Second) }
	}
	s := &Server{cfg: cfg, mux: http.NewServeMux()}
	mcp := &mcpserver.Server{
		Store:      cfg.Store,
		HubVersion: cfg.HubVersion,
		PublicURL:  cfg.PublicURL,
		Clock:      cfg.Clock,
	}
	s.mux.HandleFunc("GET /healthz", s.handleHealthz)
	s.mux.HandleFunc("GET /{$}", s.handleGuidePage)
	s.mux.HandleFunc("GET /setup.md", s.handleSetupMarkdown)
	s.mux.HandleFunc("GET /ui", s.handleUIRedirect)
	s.mux.HandleFunc("GET /ui/", s.handleUIStatic)
	s.mux.HandleFunc("GET /ui/{name}", s.handleUIStatic)
	s.mux.HandleFunc("/api/", s.handleUIAPI)
	s.mux.HandleFunc("GET /v1/bootstrap/hub_client.py", s.handleHubClientPy)
	s.mux.HandleFunc("POST /v1/tools/{name}", s.handleToolHTTP)
	s.mux.HandleFunc("POST /v1/relay/register", s.handleRelayRegister)
	s.mux.HandleFunc("POST /v1/relay/poll", s.handleRelayPoll)
	s.mux.HandleFunc("POST /v1/relay/result", s.handleRelayResult)
	s.mux.Handle("/mcp", mcp)
	return s
}

// ServeHTTP dispatches HTTP requests via ServeMux.
func (s *Server) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	s.mux.ServeHTTP(w, r)
}

func (s *Server) writeHubHeaders(w http.ResponseWriter) {
	ver, _ := s.cfg.Store.DBVersion()
	w.Header().Set("X-Hub-Kit", tools.KitVersion)
	w.Header().Set("X-Hub-Version", s.cfg.HubVersion)
	w.Header().Set("X-Hub-Contract", tools.Contract)
	w.Header().Set("X-Hub-Db", fmt.Sprintf("%d", ver))
}

func writeJSONResponse(w http.ResponseWriter, status int, payload any) {
	var buf bytes.Buffer
	enc := json.NewEncoder(&buf)
	enc.SetEscapeHTML(false)
	_ = enc.Encode(payload)
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	_, _ = w.Write(buf.Bytes())
}

func bearerToken(h http.Header) string {
	raw := h.Get("Authorization")
	if len(raw) >= 7 && strings.EqualFold(raw[:7], "bearer ") {
		return strings.TrimSpace(raw[7:])
	}
	return ""
}

func (s *Server) handleHealthz(w http.ResponseWriter, _ *http.Request) {
	s.writeHubHeaders(w)
	ver, err := s.cfg.Store.DBVersion()
	if err != nil {
		writeJSONResponse(w, http.StatusInternalServerError, map[string]any{"ok": false, "error": err.Error()})
		return
	}
	writeJSONResponse(w, http.StatusOK, map[string]any{
		"ok":          true,
		"hub_version": s.cfg.HubVersion,
		"kit_version": tools.KitVersion,
		"contract":    tools.Contract,
		"db_version":  ver,
		"exposure":    s.cfg.Exposure,
		"public_url":  s.cfg.PublicURL,
		"web_token":   s.cfg.WebTokenName != "",
	})
}

func (s *Server) handleHubClientPy(w http.ResponseWriter, _ *http.Request) {
	w.Header().Set("Content-Type", "text/x-python; charset=utf-8")
	w.WriteHeader(http.StatusOK)
	_, _ = io.WriteString(w, assets.HubClientPy)
}

func (s *Server) handleToolHTTP(w http.ResponseWriter, r *http.Request) {
	s.writeHubHeaders(w)
	name := r.PathValue("name")

	if vals, hasContract := r.Header["X-Hub-Contract"]; hasContract {
		contract := ""
		if len(vals) > 0 {
			contract = vals[0]
		}
		if contract != tools.Contract {
			he := &store.HubError{
				Status:  http.StatusBadRequest,
				Code:    "unknown_contract",
				Message: fmt.Sprintf("모르는 계약 판: %q — 이 허브는 %s", contract, tools.Contract),
			}
			writeJSONResponse(w, he.Status, he.Payload())
			return
		}
	}

	limit := MaxBody
	if big, ok := BigBodyTools[name]; ok {
		limit = big
	}
	rawBody, err := io.ReadAll(io.LimitReader(r.Body, int64(limit)+1))
	if err != nil {
		he := &store.HubError{Status: http.StatusBadRequest, Code: "invalid_json", Message: fmt.Sprintf("본문 읽기 실패: %v", err)}
		writeJSONResponse(w, he.Status, he.Payload())
		return
	}
	if len(rawBody) > limit {
		he := &store.HubError{
			Status:  http.StatusRequestEntityTooLarge,
			Code:    "payload_too_large",
			Message: fmt.Sprintf("본문 상한 %d 바이트", limit),
			Detail:  map[string]any{"limit": limit},
		}
		writeJSONResponse(w, he.Status, he.Payload())
		return
	}

	var args any = map[string]any{}
	if len(bytes.TrimSpace(rawBody)) > 0 {
		decoded, decErr := tools.DecodeJSONValue(rawBody)
		if decErr != nil {
			he := &store.HubError{
				Status:  http.StatusBadRequest,
				Code:    "invalid_json",
				Message: fmt.Sprintf("본문이 JSON 이 아니다: %v", decErr),
			}
			writeJSONResponse(w, he.Status, he.Payload())
			return
		}
		args = decoded
	}

	now := s.cfg.Clock().UTC().Truncate(time.Second)
	tok := bearerToken(r.Header)
	clientVer := r.Header.Get("X-Hub-Client")
	var principal *store.Principal
	if tok != "" {
		principal, err = s.cfg.Store.Authenticate(tok, &now, clientVer)
		if err != nil {
			if he, ok := store.AsHubError(err); ok {
				writeJSONResponse(w, he.Status, he.Payload())
				return
			}
			writeJSONResponse(w, http.StatusInternalServerError, map[string]any{"error_code": "internal_error", "error": err.Error()})
			return
		}
	}

	spec := tools.Tools[name]
	if tok != "" && principal == nil && spec != nil && spec.Bundle != "bootstrap" {
		he := store.Unauthorized("토큰이 틀렸거나 거둔 토큰이다")
		writeJSONResponse(w, he.Status, he.Payload())
		return
	}

	ctx := store.Ctx{
		Now:           now,
		Via:           "http",
		Principal:     principal,
		ClientVersion: clientVer,
		PublicURL:     s.cfg.PublicURL,
	}
	var res map[string]any
	if name == "hub_wait" {
		res, err = waiter.Call(r.Context(), s.cfg.Store, args, ctx, s.cfg.Clock)
	} else {
		res, err = tools.Call(s.cfg.Store, name, args, ctx)
	}
	if err != nil {
		if r.Context().Err() != nil {
			return
		}
		if he, ok := store.AsHubError(err); ok {
			writeJSONResponse(w, he.Status, he.Payload())
			return
		}
		writeJSONResponse(w, http.StatusInternalServerError, map[string]any{"error_code": "internal_error", "error": err.Error()})
		return
	}
	writeJSONResponse(w, http.StatusOK, res)
}
