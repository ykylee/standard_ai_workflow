package httpapi

import (
	"encoding/json"
	"io"
	"net/http"
	"strconv"
	"strings"
	"time"
	"unicode/utf8"

	"github.com/ykylee/standard_ai_workflow/hub-go/internal/store"
)

const relayPollCap = 25 * time.Second
const relayPollStep = 250 * time.Millisecond

func (s *Server) handleRelayRegister(w http.ResponseWriter, r *http.Request) {
	s.writeHubHeaders(w)
	body, err := readRelayBody(r)
	if err != nil {
		writeRelayError(w, err)
		return
	}
	result, err := s.cfg.Store.RelayRegister(s.cfg.Clock().UTC().Truncate(time.Second), body)
	if err != nil {
		writeRelayError(w, err)
		return
	}
	writeJSONResponse(w, http.StatusOK, result)
}

func (s *Server) handleRelayPoll(w http.ResponseWriter, r *http.Request) {
	s.writeHubHeaders(w)
	host, err := s.relayHost(r)
	if err != nil {
		writeRelayError(w, err)
		return
	}
	body, err := readRelayBody(r)
	if err != nil {
		writeRelayError(w, err)
		return
	}
	args, ok := body.(map[string]any)
	if !ok {
		writeRelayError(w, store.InvalidField("arguments", "객체여야 해요"))
		return
	}
	for key := range args {
		if key != "wait_s" && key != "sessions" && key != "allow_digest" {
			writeRelayError(w, &store.HubError{Status: 400, Code: "unknown_field", Message: "wait_s · sessions · allow_digest 만 받아요"})
			return
		}
	}
	waitS := 25
	if raw, exists := args["wait_s"]; exists {
		n, valid := raw.(json.Number)
		if !valid {
			writeRelayError(w, store.InvalidField("wait_s", "0 이상 정수"))
			return
		}
		parsed, e := strconv.Atoi(n.String())
		if e != nil || parsed < 0 {
			writeRelayError(w, store.InvalidField("wait_s", "0 이상 정수"))
			return
		}
		waitS = parsed
		if waitS > 25 {
			waitS = 25
		}
	}
	if raw, exists := args["sessions"]; exists && raw != nil {
		if _, ok := raw.([]any); !ok {
			writeRelayError(w, store.InvalidField("sessions", "세션 상태 목록"))
			return
		}
	}
	started := time.Now()
	got, err := s.cfg.Store.RelayPollOnce(s.cfg.Clock().UTC().Truncate(time.Second), host, args)
	if err != nil {
		writeRelayError(w, err)
		return
	}
	light := map[string]any{}
	if v, ok := args["allow_digest"].(string); ok {
		light["allow_digest"] = v
	}
	deadline := started.Add(time.Duration(waitS) * time.Second)
	for !relayPollReady(got) && time.Now().Before(deadline) {
		timer := time.NewTimer(relayPollStep)
		select {
		case <-r.Context().Done():
			timer.Stop()
			return
		case <-timer.C:
		}
		got, err = s.cfg.Store.RelayPollOnce(s.cfg.Clock().UTC().Truncate(time.Second), host, light)
		if err != nil {
			writeRelayError(w, err)
			return
		}
	}
	got["waited_s"] = int(time.Since(started).Seconds())
	writeJSONResponse(w, http.StatusOK, got)
}

func (s *Server) handleRelayResult(w http.ResponseWriter, r *http.Request) {
	s.writeHubHeaders(w)
	host, err := s.relayHost(r)
	if err != nil {
		writeRelayError(w, err)
		return
	}
	body, err := readRelayBody(r)
	if err != nil {
		writeRelayError(w, err)
		return
	}
	result, err := s.cfg.Store.RelayResult(s.cfg.Clock().UTC().Truncate(time.Second), host, body)
	if err != nil {
		writeRelayError(w, err)
		return
	}
	writeJSONResponse(w, http.StatusOK, result)
}

func (s *Server) relayHost(r *http.Request) (*store.RelayHost, error) {
	host, err := s.cfg.Store.RelayAuthenticate(bearerToken(r.Header))
	if err != nil {
		return nil, err
	}
	if host == nil {
		return nil, store.Unauthorized("중계 토큰이 없거나 틀렸거나 거둔 토큰이에요")
	}
	return host, nil
}

func readRelayBody(r *http.Request) (any, error) {
	raw, err := io.ReadAll(io.LimitReader(r.Body, MaxBody+1))
	if err != nil {
		return nil, err
	}
	if len(raw) > MaxBody {
		return nil, &store.HubError{Status: http.StatusRequestEntityTooLarge, Code: "payload_too_large", Message: "본문 상한 262144 바이트", Detail: map[string]any{"limit": MaxBody}}
	}
	if !utf8.Valid(raw) {
		return nil, &store.HubError{Status: http.StatusBadRequest, Code: "invalid_json", Message: "본문이 JSON 이 아니에요: UTF-8 이 아니에요"}
	}
	if len(strings.TrimSpace(string(raw))) == 0 {
		return map[string]any{}, nil
	}
	var body any
	dec := json.NewDecoder(strings.NewReader(string(raw)))
	dec.UseNumber()
	if err := dec.Decode(&body); err != nil {
		return nil, &store.HubError{Status: http.StatusBadRequest, Code: "invalid_json", Message: "본문이 JSON 이 아니에요: " + err.Error()}
	}
	var extra any
	if err := dec.Decode(&extra); err != io.EOF {
		return nil, &store.HubError{Status: http.StatusBadRequest, Code: "invalid_json", Message: "본문이 JSON 이 아니에요"}
	}
	return body, nil
}

func writeRelayError(w http.ResponseWriter, err error) {
	if he, ok := err.(*store.HubError); ok {
		writeJSONResponse(w, he.Status, he.Payload())
		return
	}
	writeJSONResponse(w, http.StatusInternalServerError, map[string]any{"error_code": "internal_error", "message": err.Error(), "detail": map[string]any{}})
}

func relayPollReady(got map[string]any) bool {
	dispatch, _ := got["dispatch"].([]map[string]any)
	deliver, _ := got["deliver"].([]map[string]any)
	return len(dispatch) > 0 || len(deliver) > 0
}
