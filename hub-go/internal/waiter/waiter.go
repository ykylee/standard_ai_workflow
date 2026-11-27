// Package waiter implements the transport-level long poll for hub_wait.
package waiter

import (
	"context"
	"time"

	"github.com/ykylee/standard_ai_workflow/hub-go/internal/store"
	"github.com/ykylee/standard_ai_workflow/hub-go/internal/tools"
)

const (
	capacity = 64
	pollStep = 500 * time.Millisecond
	maxWait  = 50 * time.Second
)

var slots = make(chan struct{}, capacity)

// Call validates hub_wait arguments, then polls outside the hub's request worker until work arrives or timeout.
func Call(requestCtx context.Context, st *store.Store, args any, base store.Ctx, clock func() time.Time) (map[string]any, error) {
	_, clean, err := tools.Prepare(st, "hub_wait", args, base)
	if err != nil {
		return nil, err
	}
	timeout := maxWait
	if raw, ok := clean["timeout_s"]; ok && raw != nil {
		var seconds int
		switch value := raw.(type) {
		case int:
			seconds = value
		case int64:
			seconds = int(value)
		default:
			return nil, store.InvalidField("timeout_s", "1 이상")
		}
		if seconds < 1 {
			return nil, store.InvalidField("timeout_s", "1 이상")
		}
		if time.Duration(seconds)*time.Second < timeout {
			timeout = time.Duration(seconds) * time.Second
		}
	}
	select {
	case slots <- struct{}{}:
		defer func() { <-slots }()
	default:
		return nil, &store.HubError{Status: 429, Code: "wait_capacity", Message: "허브의 동시 대기 상한 64 — 잠시 뒤 다시 불러요", Detail: map[string]any{"limit": capacity}}
	}
	sessionID, _ := clean["session"].(string)
	current := base
	if clock != nil {
		current.Now = clock().UTC().Truncate(time.Second)
	}
	start := time.Now()
	got, err := st.WaitPoll(current, sessionID, true)
	if err != nil {
		return nil, err
	}
	for got == nil && time.Since(start) < timeout {
		timer := time.NewTimer(pollStep)
		select {
		case <-requestCtx.Done():
			timer.Stop()
			clearCtx := current
			if clock != nil {
				clearCtx.Now = clock().UTC().Truncate(time.Second)
			}
			_ = st.WaitClear(clearCtx, sessionID)
			return nil, requestCtx.Err()
		case <-timer.C:
		}
		if clock != nil {
			current.Now = clock().UTC().Truncate(time.Second)
		}
		got, err = st.WaitPoll(current, sessionID, false)
		if err != nil {
			return nil, err
		}
	}
	waited := int(time.Since(start).Seconds())
	if got == nil {
		return st.WaitTimeout(current, sessionID, waited)
	}
	got["waited_s"] = waited
	return got, nil
}
