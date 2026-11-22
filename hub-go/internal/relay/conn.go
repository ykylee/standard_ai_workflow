package relay

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"
)

type HubUnreachable struct {
	Err error
}

func (e *HubUnreachable) Error() string {
	return e.Err.Error()
}

func (e *HubUnreachable) Unwrap() error {
	return e.Err
}

type HubError struct {
	Status  int
	Payload map[string]any
}

func (e *HubError) Error() string {
	return fmt.Sprintf("%d %v: %v", e.Status, e.Payload["error_code"], e.Payload["message"])
}

func Post(base, path string, body any, token string, timeout time.Duration) (map[string]any, error) {
	if timeout <= 0 {
		timeout = 40 * time.Second
	}
	var buf bytes.Buffer
	enc := json.NewEncoder(&buf)
	enc.SetEscapeHTML(false)
	if err := enc.Encode(body); err != nil {
		return nil, err
	}
	url := strings.TrimRight(base, "/") + path
	req, err := http.NewRequest(http.MethodPost, url, &buf)
	if err != nil {
		return nil, &HubUnreachable{Err: err}
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-Hub-Client", "workflow-hub-relay/1")
	if token != "" {
		req.Header.Set("Authorization", "Bearer "+token)
	}
	client := &http.Client{Timeout: timeout}
	resp, err := client.Do(req)
	if err != nil {
		return nil, &HubUnreachable{Err: err}
	}
	defer resp.Body.Close()

	raw, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, &HubUnreachable{Err: err}
	}
	if resp.StatusCode >= 400 {
		var payload map[string]any
		if uerr := json.Unmarshal(raw, &payload); uerr != nil || payload == nil {
			payload = map[string]any{
				"error_code": "http_error",
				"message":    fmt.Sprintf("HTTP %d", resp.StatusCode),
			}
		}
		return nil, &HubError{Status: resp.StatusCode, Payload: payload}
	}
	var out map[string]any
	if err := json.Unmarshal(raw, &out); err != nil {
		return nil, err
	}
	if out == nil {
		out = map[string]any{}
	}
	return out, nil
}
