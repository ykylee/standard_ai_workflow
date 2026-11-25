package httpapi

import (
	"net/http"

	"github.com/ykylee/standard_ai_workflow/hub-go/internal/store"
	"github.com/ykylee/standard_ai_workflow/hub-go/internal/tools"
)

// screenIdeas serves the idea box: reads for viewers, writes for a logged-in approved human.
func (s *Server) screenIdeas(r *http.Request, parts []string, read, write store.Ctx) (map[string]any, error) {
	if r.Method == http.MethodGet {
		if len(parts) == 4 {
			return s.cfg.Store.IdeaGet(read, parts[3])
		}
		var status any
		if r.URL.Query().Has("status") {
			status = r.URL.Query().Get("status")
		}
		return s.cfg.Store.IdeaList(read, status)
	}
	body, err := readScreenJSON(r)
	if err != nil {
		return nil, err
	}
	if len(parts) == 3 {
		return s.cfg.Store.IdeaAdd(write, body["body"], body["request_id"], true)
	}
	bridge := &tools.JudgeBridge{Store: s.cfg.Store}
	return s.cfg.Store.IdeaAct(write, parts[3], body, bridge.PrepareCreate)
}
