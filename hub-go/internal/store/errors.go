package store

import (
	"fmt"
	"sort"
	"strings"
)

// HubError represents an API/tool error mapped identically across HTTP status codes and MCP payloads.
type HubError struct {
	Status  int
	Code    string
	Message string
	Detail  map[string]any
}

func (e *HubError) Error() string {
	return fmt.Sprintf("%s: %s", e.Code, e.Message)
}

func (e *HubError) Payload() map[string]any {
	d := e.Detail
	if d == nil {
		d = map[string]any{}
	}
	return map[string]any{
		"error_code": e.Code,
		"message":    e.Message,
		"detail":     d,
	}
}

func Unauthorized(message string) *HubError {
	if message == "" {
		message = "토큰이 없거나 틀렸거나 거둔 토큰이다"
	}
	return &HubError{Status: 401, Code: "unauthorized", Message: message}
}

func Forbidden(message string) *HubError {
	return &HubError{Status: 403, Code: "forbidden", Message: message}
}

func NotFound(message string) *HubError {
	return &HubError{Status: 404, Code: "not_found", Message: message}
}

func InvalidField(field, message string) *HubError {
	return &HubError{
		Status:  400,
		Code:    "invalid_field",
		Message: fmt.Sprintf("%s: %s", field, message),
		Detail:  map[string]any{"field": field},
	}
}

func UnknownField(fields []string) *HubError {
	cp := make([]string, len(fields))
	copy(cp, fields)
	sort.Strings(cp)
	return &HubError{
		Status:  400,
		Code:    "unknown_field",
		Message: "모르는 필드: " + strings.Join(cp, ", "),
		Detail:  map[string]any{"fields": cp},
	}
}

func VersionConflict(currentVersion int, current map[string]any) *HubError {
	return &HubError{
		Status:  409,
		Code:    "version_conflict",
		Message: fmt.Sprintf("version 이 달라요 — 지금 %d", currentVersion),
		Detail:  map[string]any{"current_version": currentVersion, "current": current},
	}
}
