package relay

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"slices"
	"strings"
)

const (
	HomeEnv     = "WORKFLOW_HUB_RELAY_HOME"
	MaxSessions = 3
)

var PermissionModes = []string{"default", "acceptEdits", "plan"}

// AllowEntry 는 relay-allow.json 의 dir 항목이다.
// Python AllowDigest (json.dumps(..., sort_keys=True)) 와 바이트 일치를 위해
// JSON 키의 알파벳순으로 필드를 선언한다.
type AllowEntry struct {
	Alias           string   `json:"alias"`
	Harnesses       []string `json:"harnesses"`
	MaxSessions     int      `json:"max_sessions"`
	Path            string   `json:"path"`
	PermissionModes []string `json:"permission_modes"`
	Project         string   `json:"project"`
}

func Home() string {
	if raw := os.Getenv(HomeEnv); raw != "" {
		return raw
	}
	h, err := os.UserHomeDir()
	if err != nil || h == "" {
		return filepath.Join(".", ".config", "workflow-hub")
	}
	return filepath.Join(h, ".config", "workflow-hub")
}

func writeAtomic(path string, data []byte, mode os.FileMode) error {
	dir := filepath.Dir(path)
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return err
	}
	f, err := os.CreateTemp(dir, filepath.Base(path)+".")
	if err != nil {
		return err
	}
	tmpName := f.Name()
	cleanup := true
	defer func() {
		if cleanup {
			_ = os.Remove(tmpName)
		}
	}()
	if err := os.Chmod(tmpName, mode); err != nil {
		_ = f.Close()
		return err
	}
	if _, err := f.Write(data); err != nil {
		_ = f.Close()
		return err
	}
	if err := f.Close(); err != nil {
		return err
	}
	if err := os.Rename(tmpName, path); err != nil {
		return err
	}
	cleanup = false
	return nil
}

func ReadJSON(name string) (map[string]any, error) {
	path := filepath.Join(Home(), name)
	raw, err := os.ReadFile(path)
	if err != nil {
		if os.IsNotExist(err) {
			return map[string]any{}, nil
		}
		return nil, err
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

func WriteJSON(name string, value any) error {
	var buf bytes.Buffer
	enc := json.NewEncoder(&buf)
	enc.SetEscapeHTML(false)
	enc.SetIndent("", "  ")
	if err := enc.Encode(value); err != nil {
		return err
	}
	return writeAtomic(filepath.Join(Home(), name), buf.Bytes(), 0o600)
}

func ReadToken() (string, bool) {
	path := filepath.Join(Home(), "relay.token")
	raw, err := os.ReadFile(path)
	if err != nil {
		return "", false
	}
	return strings.TrimSpace(string(raw)), true
}

func WriteToken(token string) error {
	return writeAtomic(filepath.Join(Home(), "relay.token"), []byte(token+"\n"), 0o600)
}

func LoadAllow() ([]AllowEntry, error) {
	path := filepath.Join(Home(), "relay-allow.json")
	raw, err := os.ReadFile(path)
	if err != nil {
		if os.IsNotExist(err) {
			return []AllowEntry{}, nil
		}
		return nil, err
	}
	var doc struct {
		Dir []AllowEntry `json:"dir"`
	}
	if err := json.Unmarshal(raw, &doc); err != nil {
		return nil, err
	}
	if doc.Dir == nil {
		return []AllowEntry{}, nil
	}
	return doc.Dir, nil
}

func SaveAllow(entries []AllowEntry) error {
	if entries == nil {
		entries = []AllowEntry{}
	}
	return WriteJSON("relay-allow.json", map[string]any{"dir": entries})
}

func compactJSON(v any) ([]byte, error) {
	var buf bytes.Buffer
	enc := json.NewEncoder(&buf)
	enc.SetEscapeHTML(false)
	if err := enc.Encode(v); err != nil {
		return nil, err
	}
	return bytes.TrimSuffix(buf.Bytes(), []byte("\n")), nil
}

func AllowDigest(entries []AllowEntry) string {
	if entries == nil {
		entries = []AllowEntry{}
	}
	normalized := make([]AllowEntry, len(entries))
	for i, e := range entries {
		if e.Harnesses == nil {
			e.Harnesses = []string{}
		}
		if e.PermissionModes == nil {
			e.PermissionModes = []string{}
		}
		normalized[i] = e
	}
	raw, err := compactJSON(normalized)
	if err != nil {
		raw = []byte("[]")
	}
	sum := sha256.Sum256(raw)
	return "sha256:" + hex.EncodeToString(sum[:])
}

func ValidateEntry(e AllowEntry) string {
	if strings.TrimSpace(e.Alias) == "" {
		return "alias 가 비었다"
	}
	if e.Path == "" || !filepath.IsAbs(e.Path) {
		return "path 는 절대 경로"
	}
	info, err := os.Stat(e.Path)
	if err != nil || !info.IsDir() {
		return fmt.Sprintf("디렉터리가 없다: %s", e.Path)
	}
	if e.Project == "" {
		return "project 가 비었다"
	}
	if len(e.Harnesses) == 0 {
		return "harnesses 가 비었다"
	}
	modes := e.PermissionModes
	if len(modes) == 0 {
		modes = []string{"default"}
	}
	var bad []string
	for _, m := range modes {
		if !slices.Contains(PermissionModes, m) {
			bad = append(bad, m)
		}
	}
	if len(bad) > 0 {
		return fmt.Sprintf("받지 않는 권한 모드: %v — %s 만 (bypass 계열 불가)", bad, strings.Join(PermissionModes, " · "))
	}
	if e.MaxSessions < 1 || e.MaxSessions > MaxSessions {
		return fmt.Sprintf("max_sessions 는 1~%d", MaxSessions)
	}
	return ""
}

func CheckRequest(entries []AllowEntry, projectID string, target map[string]any, runningByAlias map[string]int) (*AllowEntry, string) {
	alias, _ := target["dir_alias"].(string)
	var entry *AllowEntry
	for i := range entries {
		if entries[i].Alias == alias {
			entry = &entries[i]
			break
		}
	}
	if entry == nil {
		return nil, fmt.Sprintf("허용 목록에 없는 별칭: %s", alias)
	}
	if entry.Project != projectID {
		return nil, fmt.Sprintf("%s 는 다른 프로젝트의 별칭이다", alias)
	}
	harness, _ := target["harness"].(string)
	if !slices.Contains(entry.Harnesses, harness) {
		return nil, fmt.Sprintf("%s 에 허용되지 않은 하네스: %s", alias, harness)
	}
	mode, _ := target["permission_mode"].(string)
	if mode == "" {
		mode = "default"
	}
	allowedModes := entry.PermissionModes
	if len(allowedModes) == 0 {
		allowedModes = []string{"default"}
	}
	if !slices.Contains(allowedModes, mode) || !slices.Contains(PermissionModes, mode) {
		return nil, fmt.Sprintf("%s 에 허용되지 않은 권한 모드: %s", alias, mode)
	}
	maxSess := entry.MaxSessions
	if maxSess <= 0 {
		maxSess = 1
	}
	if runningByAlias[alias] >= maxSess {
		return nil, fmt.Sprintf("%s 의 동시 세션 상한 %d", alias, maxSess)
	}
	return entry, ""
}
