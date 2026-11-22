package relay

import (
	"errors"
	"fmt"
	"strings"
	"sync"
	"time"
)

func FormatFirstPrompt(requestID, harness, prompt string) string {
	if prompt == "" {
		prompt = "(없음)"
	}
	return fmt.Sprintf(
		"이 세션은 PC 중계가 워크플로우 허브의 세션 요청 %s 로 띄운 **일하는 세션**이다. 먼저 "+
			`hub_session_start(session={"harness": "%s", "kind": "worker", `+
			`"delivery": ["adapter", "piggyback", "wait"], "spawn_request": "%s"}) 를 부르고, 진입 파일의 `+
			"워크플로우 허브 규칙을 따른다. 오케스트레이터가 남긴 지시: %s",
		requestID, harness, requestID, prompt,
	)
}

type Relay struct {
	Cfg       map[string]any
	Token     string
	Handles   map[string]*Handle
	AliasOf   map[string]string
	SessionOf map[string]string
	Seen      map[string]map[string]bool
	Recent    []string
	Last      map[string]any
	LogFn     func(string)

	Mu     sync.Mutex
	pollMu sync.Mutex
}

func NewRelay(logFn func(string)) (*Relay, error) {
	cfg, err := ReadJSON("relay.json")
	if err != nil {
		return nil, err
	}
	token, hasToken := ReadToken()
	hubURL, _ := cfg["hub"].(string)
	if hubURL == "" || !hasToken || token == "" {
		return nil, errors.New("relay: 등록 전이다 — `workflow-hub relay init --hub URL --invite CODE --name NAME`")
	}
	if logFn == nil {
		logFn = func(string) {}
	}
	return &Relay{
		Cfg:       cfg,
		Token:     token,
		Handles:   map[string]*Handle{},
		AliasOf:   map[string]string{},
		SessionOf: map[string]string{},
		Seen:      map[string]map[string]bool{},
		Recent:    []string{},
		Last:      map[string]any{},
		LogFn:     logFn,
	}, nil
}

func (r *Relay) Log(msg string) {
	line := fmt.Sprintf("%s %s", time.Now().Format("15:04:05"), msg)
	r.Mu.Lock()
	r.Recent = append(r.Recent, line)
	if len(r.Recent) > 200 {
		r.Recent = r.Recent[len(r.Recent)-200:]
	}
	fn := r.LogFn
	r.Mu.Unlock()
	if fn != nil {
		fn(msg)
	}
}

func (r *Relay) post(path string, body any, timeout time.Duration) (map[string]any, error) {
	hubURL, _ := r.Cfg["hub"].(string)
	return Post(hubURL, path, body, r.Token, timeout)
}

func (r *Relay) sessionStates() []map[string]string {
	r.Mu.Lock()
	defer r.Mu.Unlock()
	out := make([]map[string]string, 0, len(r.SessionOf))
	for sid, rid := range r.SessionOf {
		h := r.Handles[rid]
		if h == nil {
			continue
		}
		ad, err := GetAdapter(h.Harness)
		if err != nil {
			continue
		}
		out = append(out, map[string]string{
			"session": sid,
			"status":  ad.Status(h),
		})
	}
	return out
}

func (r *Relay) Once(waitS int) (map[string]any, error) {
	r.pollMu.Lock()
	defer r.pollMu.Unlock()

	st, err := ReadJSON("relay-state.json")
	if err != nil {
		return nil, err
	}
	if paused, _ := st["paused"].(bool); paused {
		return map[string]any{"paused": true}, nil
	}
	entries, err := LoadAllow()
	if err != nil {
		return nil, err
	}
	got, err := r.post("/v1/relay/poll", map[string]any{
		"wait_s":       waitS,
		"sessions":     r.sessionStates(),
		"allow_digest": AllowDigest(entries),
	}, time.Duration(waitS+15)*time.Second)
	if err != nil {
		return nil, err
	}

	if sessRaw, ok := got["sessions"].([]any); ok {
		r.Mu.Lock()
		for _, item := range sessRaw {
			if m, ok := item.(map[string]any); ok {
				sid, _ := m["session"].(string)
				rid, _ := m["request"].(string)
				if sid != "" && rid != "" {
					r.SessionOf[sid] = rid
				}
			}
		}
		r.Mu.Unlock()
	}

	if dispRaw, ok := got["dispatch"].([]any); ok {
		for _, item := range dispRaw {
			if d, ok := item.(map[string]any); ok {
				r.dispatch(d, entries)
			}
		}
	}

	if delivRaw, ok := got["deliver"].([]any); ok {
		for _, item := range delivRaw {
			if s, ok := item.(map[string]any); ok {
				r.DeliverSession(s)
			}
		}
	}

	r.Mu.Lock()
	r.Last = got
	r.Mu.Unlock()
	return got, nil
}

func (r *Relay) sendResult(d map[string]any, state string, result map[string]any) {
	_, _ = r.post("/v1/relay/result", map[string]any{
		"project_id": d["project_id"],
		"request":    d["request"],
		"state":      state,
		"result":     result,
	}, 40*time.Second)
}

func (r *Relay) dispatch(d map[string]any, entries []AllowEntry) {
	target, _ := d["target"].(map[string]any)
	if target == nil {
		target = map[string]any{}
	}
	kind, _ := d["kind"].(string)
	reqID, _ := d["request"].(string)
	projectID, _ := d["project_id"].(string)

	if kind == "stop" {
		targetSession, _ := target["session"].(string)
		r.Mu.Lock()
		rid := r.SessionOf[targetSession]
		h := r.Handles[rid]
		r.Mu.Unlock()
		if h == nil {
			r.sendResult(d, "failed", map[string]any{"reason": "이 중계가 띄운 세션을 찾지 못했다"})
			return
		}
		ad, err := GetAdapter(h.Harness)
		if err == nil {
			_ = ad.Stop(h)
		}
		r.sendResult(d, "done", map[string]any{"stopped": targetSession})
		r.Log("stop " + targetSession)
		return
	}

	r.Mu.Lock()
	liveCount := 0
	byAlias := map[string]int{}
	for rid, h := range r.Handles {
		if h.Alive() {
			liveCount++
			byAlias[r.AliasOf[rid]]++
		}
	}
	r.Mu.Unlock()

	if liveCount >= MaxSessions {
		r.sendResult(d, "refused_by_host", map[string]any{
			"reason": fmt.Sprintf("이 PC 의 동시 세션 상한 %d", MaxSessions),
		})
		return
	}

	entry, why := CheckRequest(entries, projectID, target, byAlias)
	if entry == nil {
		r.sendResult(d, "refused_by_host", map[string]any{"reason": why})
		r.Log(fmt.Sprintf("refuse %s: %s", reqID, why))
		return
	}

	harness, _ := target["harness"].(string)
	prompt, _ := target["prompt"].(string)
	mode, _ := target["permission_mode"].(string)
	if mode == "" {
		mode = "default"
	}

	ad, err := GetAdapter(harness)
	if err != nil {
		msg := err.Error()
		if len(msg) > 300 {
			msg = msg[:300]
		}
		r.sendResult(d, "failed", map[string]any{"reason": msg})
		return
	}
	h, err := ad.Spawn(entry.Path, FormatFirstPrompt(reqID, harness, prompt), mode)
	if err != nil {
		msg := err.Error()
		if len(msg) > 300 {
			msg = msg[:300]
		}
		r.sendResult(d, "failed", map[string]any{"reason": msg})
		return
	}

	r.Mu.Lock()
	r.Handles[reqID] = h
	r.AliasOf[reqID] = entry.Alias
	h.Mu.Lock()
	hsid := h.HarnessSessionID
	h.Mu.Unlock()
	r.Mu.Unlock()

	r.sendResult(d, "done", map[string]any{
		"harness":            harness,
		"pid":                h.PID(),
		"harness_session_id": hsid,
	})
	r.Log(fmt.Sprintf("spawn %s → %s pid %d", reqID, harness, h.PID()))
}

func formatMessageBody(body any) string {
	switch v := body.(type) {
	case string:
		return v
	case nil:
		return ""
	default:
		raw, err := compactJSON(v)
		if err != nil {
			return fmt.Sprint(v)
		}
		return string(raw)
	}
}

func (r *Relay) DeliverSession(s map[string]any) {
	sid, _ := s["session"].(string)
	r.Mu.Lock()
	rid := r.SessionOf[sid]
	h := r.Handles[rid]
	r.Mu.Unlock()
	if h == nil || !h.Alive() {
		return
	}

	ad, err := GetAdapter(h.Harness)
	if err != nil {
		return
	}

	msgs, _ := s["messages"].([]any)
	for _, rawM := range msgs {
		m, ok := rawM.(map[string]any)
		if !ok {
			continue
		}
		mid, _ := m["id"].(string)
		if mid == "" {
			continue
		}

		r.Mu.Lock()
		seen := r.Seen[sid]
		if seen == nil {
			seen = map[string]bool{}
			r.Seen[sid] = seen
		}
		already := seen[mid]
		if !already {
			seen[mid] = true
		}
		r.Mu.Unlock()
		if already {
			continue
		}

		kind, _ := m["kind"].(string)
		fromObj, _ := m["from"].(map[string]any)
		callsign, _ := fromObj["callsign"].(string)
		orchSuffix := ""
		if isOrch, _ := fromObj["orchestrator"].(bool); isOrch {
			orchSuffix = " (오케스트레이터)"
		}
		bodyText := formatMessageBody(m["body"])
		text := fmt.Sprintf(
			"[워크플로우 허브 받은편지함 — %s %s · from %s%s] %s — 확인: hub_inbox_ack(session=%q, message_id=%q, decision=…)",
			kind, mid, callsign, orchSuffix, bodyText, sid, mid,
		)
		how, err := ad.Deliver(h, text)
		if err != nil {
			r.Mu.Lock()
			delete(r.Seen[sid], mid)
			r.Mu.Unlock()
			r.Log(fmt.Sprintf("deliver %s → %s error: %v", mid, sid, err))
			continue
		}
		r.Log(fmt.Sprintf("deliver %s → %s (%s)", mid, sid, how))
	}
}

func (r *Relay) StopAll() {
	r.Mu.Lock()
	handles := make([]*Handle, 0, len(r.Handles))
	for _, h := range r.Handles {
		handles = append(handles, h)
	}
	r.Mu.Unlock()

	for _, h := range handles {
		if h.Alive() {
			if ad, err := GetAdapter(h.Harness); err == nil {
				_ = ad.Stop(h)
			}
		}
	}
}

func (r *Relay) Serve(once bool, waitS int, uiPort int) int {
	backoff := 1 * time.Second
	if uiPort > 0 {
		srv, actualPort, err := StartUI(r, uiPort)
		if err != nil {
			r.Log(fmt.Sprintf("로컬 화면 기동 실패: %v", err))
			return 1
		}
		defer func() {
			_ = srv.Close()
		}()
		r.Log(fmt.Sprintf("로컬 화면 http://127.0.0.1:%d/", actualPort))
	}
	defer func() {
		if !once {
			r.StopAll()
		}
	}()

	for {
		_, err := r.Once(waitS)
		if err == nil {
			backoff = 1 * time.Second
		} else {
			var hubUnreach *HubUnreachable
			var hubErr *HubError
			if errors.As(err, &hubUnreach) {
				r.Log(fmt.Sprintf("허브에 닿지 않는다: %v — %.0f초 뒤 다시", err, backoff.Seconds()))
				time.Sleep(backoff)
				backoff *= 2
				if backoff > 60*time.Second {
					backoff = 60 * time.Second
				}
			} else if errors.As(err, &hubErr) {
				r.Log(fmt.Sprintf("허브 오류: %v", err))
				if hubErr.Status == 401 {
					return 3
				}
				time.Sleep(5 * time.Second)
			} else {
				r.Log(fmt.Sprintf("오류: %v", err))
				time.Sleep(5 * time.Second)
			}
		}
		if once {
			return 0
		}
		if st, rerr := ReadJSON("relay-state.json"); rerr == nil {
			if paused, _ := st["paused"].(bool); paused {
				time.Sleep(2 * time.Second)
			}
		}
	}
}

var _ = strings.TrimSpace
