package httpapi

import (
	"bytes"
	"encoding/json"
	"net/http"
	"sync"
	"time"

	"github.com/ykylee/standard_ai_workflow/hub-go/internal/store"
)

// A2A 스트림(SSE) — Python hub/app.py a2a_rpc 와 같은 이벤트. 상한에서 닫히면 클라이언트가 다시 구독한다.

const (
	a2aStreamCap         = 50 * time.Second
	a2aStreamPoll        = time.Second
	a2aStreamKeepalive   = 15 * time.Second
	a2aStreamCapacity    = 64
	a2aStreamPerCallsign = 8
)

type streamSlots struct {
	mu    sync.Mutex
	total int
	by    map[string]int
}

var a2aStreams = &streamSlots{by: map[string]int{}}

func (t *streamSlots) take(key string) bool {
	t.mu.Lock()
	defer t.mu.Unlock()
	if t.total >= a2aStreamCapacity || t.by[key] >= a2aStreamPerCallsign {
		return false
	}
	t.total++
	t.by[key]++
	return true
}

func (t *streamSlots) release(key string) {
	t.mu.Lock()
	defer t.mu.Unlock()
	t.total--
	if t.by[key]--; t.by[key] == 0 {
		delete(t.by, key)
	}
}

func a2aMethod(raw []byte) string {
	var req struct {
		Method any `json:"method"`
	}
	_ = json.Unmarshal(raw, &req)
	method, _ := req.Method.(string)
	return method
}

func a2aStatus(task map[string]any) map[string]any {
	status, _ := task["status"].(map[string]any)
	return status
}

func a2aTerminal(task map[string]any) bool {
	switch a2aStatus(task)["state"] {
	case "TASK_STATE_COMPLETED", "TASK_STATE_FAILED", "TASK_STATE_CANCELED", "TASK_STATE_REJECTED":
		return true
	}
	return false
}

func encodeCompact(v any) []byte {
	var buf bytes.Buffer
	enc := json.NewEncoder(&buf)
	enc.SetEscapeHTML(false)
	_ = enc.Encode(v)
	return bytes.TrimRight(buf.Bytes(), "\n")
}

func (s *Server) a2aStream(w http.ResponseWriter, r *http.Request, ctx store.Ctx, token string, id any, task map[string]any) {
	w.Header().Set("Content-Type", "text/event-stream; charset=utf-8")
	w.Header().Set("X-Accel-Buffering", "no")
	w.WriteHeader(http.StatusOK)
	flush := http.NewResponseController(w)
	send := func(result any) bool {
		_, err := w.Write(append(append([]byte("data: "), encodeCompact(map[string]any{"jsonrpc": "2.0", "id": id, "result": result})...), '\n', '\n'))
		return err == nil && flush.Flush() == nil
	}
	if !send(map[string]any{"task": task}) {
		return
	}
	start, beat := time.Now(), time.Now()
	for !a2aTerminal(task) && time.Since(start) < a2aStreamCap {
		select {
		case <-r.Context().Done():
			return
		case <-time.After(a2aStreamPoll):
		}
		// 거둔 토큰 · 봉인된 프로젝트는 스트림도 닫는다
		ctx.Now = s.cfg.Clock().UTC().Truncate(time.Second)
		p, err := s.cfg.Store.Authenticate(token, &ctx.Now, ctx.ClientVersion)
		if err != nil || p == nil {
			return
		}
		ctx.Principal = p
		if moved, err := s.cfg.Store.ProjectMoved(p.ProjectID); err != nil || moved != "" {
			return
		}
		fresh, err := s.cfg.Store.A2AGet(ctx, map[string]any{"id": task["id"]})
		if err != nil {
			return
		}
		if !bytes.Equal(encodeCompact(a2aStatus(task)), encodeCompact(a2aStatus(fresh))) {
			artifacts, _ := fresh["artifacts"].([]any)
			for _, a := range artifacts {
				if !send(map[string]any{"artifactUpdate": map[string]any{"taskId": fresh["id"], "contextId": fresh["contextId"], "artifact": a, "append": false, "lastChunk": true}}) {
					return
				}
			}
			if !send(map[string]any{"statusUpdate": map[string]any{"taskId": fresh["id"], "contextId": fresh["contextId"], "status": fresh["status"]}}) {
				return
			}
		}
		task = fresh
		if time.Since(beat) >= a2aStreamKeepalive {
			beat = time.Now()
			if _, err := w.Write([]byte(": keep-alive\n\n")); err != nil || flush.Flush() != nil {
				return
			}
		}
	}
}
