package relay

import (
	"bufio"
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"github.com/ykylee/standard_ai_workflow/hub-go/internal/pytext"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"slices"
	"strings"
	"sync"
	"syscall"
	"time"
)

var AdapterNames = []string{"claude-code", "codex", "fake"}

func IsKnownAdapter(name string) bool {
	return slices.Contains(AdapterNames, name)
}

type Handle struct {
	Harness          string
	Cmd              *exec.Cmd
	Stdin            io.WriteCloser
	Cwd              string
	Status           string
	HarnessSessionID string
	TurnID           string
	Sandbox          string
	SandboxPol       map[string]any
	Mu               sync.Mutex
	Done             chan struct{}

	nextID  int
	waiting map[int]chan map[string]any
}

func (h *Handle) Alive() bool {
	select {
	case <-h.Done:
		return false
	default:
		return true
	}
}

func (h *Handle) PID() int {
	if h.Cmd == nil || h.Cmd.Process == nil {
		return 0
	}
	return h.Cmd.Process.Pid
}

type Adapter interface {
	Name() string
	Probe() map[string]any
	Spawn(cwd, prompt, permissionMode string) (*Handle, error)
	Deliver(h *Handle, text string) (string, error)
	Status(h *Handle) string
	Stop(h *Handle) error
}

func GetAdapter(name string) (Adapter, error) {
	switch name {
	case "claude-code":
		return &ClaudeCodeAdapter{}, nil
	case "codex":
		return &CodexAdapter{}, nil
	case "fake":
		return &FakeAdapter{}, nil
	default:
		return nil, fmt.Errorf("모르는 어댑터: %s", name)
	}
}

func terminateProcess(cmd *exec.Cmd, done <-chan struct{}, timeout time.Duration) {
	if cmd == nil || cmd.Process == nil {
		return
	}
	select {
	case <-done:
		return
	default:
	}
	if err := cmd.Process.Signal(syscall.SIGTERM); err != nil {
		_ = cmd.Process.Kill()
	}
	select {
	case <-done:
		return
	case <-time.After(timeout):
		_ = cmd.Process.Kill()
		<-done
	}
}

// --- FakeAdapter ------------------------------------------------------------

// RunFakeWorker 는 relay 가 띄우는 테스트용 가짜 워커 하위 프로세스다.
func RunFakeWorker() int {
	sc := bufio.NewScanner(os.Stdin)
	sc.Buffer(make([]byte, 0, 64*1024), 4*1024*1024)
	for sc.Scan() {
		line := sc.Text() + "\n"
		f, err := os.OpenFile(".relay-fake.log", os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0o644)
		if err == nil {
			_, _ = f.WriteString(line)
			_ = f.Close()
		}
		_, _ = fmt.Fprintln(os.Stdout, "ok")
	}
	return 0
}

type FakeAdapter struct{}

func (a *FakeAdapter) Name() string { return "fake" }

func (a *FakeAdapter) Probe() map[string]any {
	return map[string]any{
		"harness": "fake",
		"version": "0",
		"actions": []string{"spawn", "deliver", "status", "stop"},
	}
}

func (a *FakeAdapter) Spawn(cwd, prompt, _permissionMode string) (*Handle, error) {
	exe, err := os.Executable()
	if err != nil {
		return nil, err
	}
	cmd := exec.Command(exe, "__fake-worker")
	cmd.Dir = cwd
	stdin, err := cmd.StdinPipe()
	if err != nil {
		return nil, err
	}
	if err := cmd.Start(); err != nil {
		_ = stdin.Close()
		return nil, err
	}
	h := &Handle{
		Harness: "fake",
		Cmd:     cmd,
		Stdin:   stdin,
		Cwd:     cwd,
		Status:  "idle",
		Done:    make(chan struct{}),
	}
	go func() {
		_ = cmd.Wait()
		h.Mu.Lock()
		h.Status = "ended"
		h.Mu.Unlock()
		close(h.Done)
	}()
	if _, err := a.Deliver(h, prompt); err != nil {
		_ = a.Stop(h)
		return nil, err
	}
	return h, nil
}

func (a *FakeAdapter) Deliver(h *Handle, text string) (string, error) {
	h.Mu.Lock()
	defer h.Mu.Unlock()
	if h.Stdin == nil {
		return "", errors.New("fake stdin closed")
	}
	clean := strings.ReplaceAll(text, "\n", " ") + "\n"
	if _, err := io.WriteString(h.Stdin, clean); err != nil {
		return "", err
	}
	return "stdin", nil
}

func (a *FakeAdapter) Status(h *Handle) string {
	if h.Alive() {
		return "idle"
	}
	return "ended"
}

func (a *FakeAdapter) Stop(h *Handle) error {
	h.Mu.Lock()
	stdin := h.Stdin
	h.Stdin = nil
	h.Mu.Unlock()
	if stdin != nil {
		_ = stdin.Close()
	}
	terminateProcess(h.Cmd, h.Done, 10*time.Second)
	h.Mu.Lock()
	h.Status = "ended"
	h.Mu.Unlock()
	return nil
}

// --- ClaudeCodeAdapter ------------------------------------------------------

type ClaudeCodeAdapter struct{}

func (a *ClaudeCodeAdapter) Name() string { return "claude-code" }

func (a *ClaudeCodeAdapter) Probe() map[string]any {
	exe, err := exec.LookPath("claude")
	if err != nil {
		return map[string]any{"harness": a.Name(), "available": false}
	}
	out, _ := exec.Command(exe, "--version").Output()
	return map[string]any{
		"harness":          a.Name(),
		"available":        true,
		"version":          pytext.Strip(string(out)),
		"actions":          []string{"spawn", "deliver", "status", "stop"},
		"deliver_mid_turn": "unmeasured",
	}
}

func (a *ClaudeCodeAdapter) Spawn(cwd, prompt, permissionMode string) (*Handle, error) {
	exe, err := exec.LookPath("claude")
	if err != nil {
		exe = "claude"
	}
	cmd := exec.Command(
		exe, "-p",
		"--input-format", "stream-json",
		"--output-format", "stream-json",
		"--verbose",
		"--permission-mode", permissionMode,
	)
	cmd.Dir = cwd
	stdin, err := cmd.StdinPipe()
	if err != nil {
		return nil, err
	}
	stdout, err := cmd.StdoutPipe()
	if err != nil {
		_ = stdin.Close()
		return nil, err
	}
	if err := cmd.Start(); err != nil {
		_ = stdin.Close()
		return nil, err
	}
	h := &Handle{
		Harness: a.Name(),
		Cmd:     cmd,
		Stdin:   stdin,
		Cwd:     cwd,
		Status:  "busy",
		Done:    make(chan struct{}),
	}
	go a.readLoop(h, stdout)
	if _, err := a.Deliver(h, prompt); err != nil {
		_ = a.Stop(h)
		return nil, err
	}
	return h, nil
}

func (a *ClaudeCodeAdapter) readLoop(h *Handle, stdout io.ReadCloser) {
	defer func() {
		_ = h.Cmd.Wait()
		h.Mu.Lock()
		h.Status = "ended"
		h.Mu.Unlock()
		close(h.Done)
	}()
	sc := bufio.NewScanner(stdout)
	sc.Buffer(make([]byte, 0, 64*1024), 4*1024*1024)
	for sc.Scan() {
		var ev map[string]any
		if err := json.Unmarshal(sc.Bytes(), &ev); err != nil {
			continue
		}
		typ, _ := ev["type"].(string)
		sub, _ := ev["subtype"].(string)
		sid, _ := ev["session_id"].(string)
		h.Mu.Lock()
		if typ == "system" && sub == "init" && sid != "" {
			h.HarnessSessionID = sid
		} else if typ == "result" {
			h.Status = "idle"
		}
		h.Mu.Unlock()
	}
}

func (a *ClaudeCodeAdapter) Deliver(h *Handle, text string) (string, error) {
	payload := map[string]any{
		"type": "user",
		"message": map[string]any{
			"role":    "user",
			"content": text,
		},
	}
	raw, err := compactJSON(payload)
	if err != nil {
		return "", err
	}
	h.Mu.Lock()
	defer h.Mu.Unlock()
	if h.Stdin == nil {
		return "", errors.New("claude stdin closed")
	}
	if _, err := h.Stdin.Write(append(raw, '\n')); err != nil {
		return "", err
	}
	was := h.Status
	h.Status = "busy"
	if was == "busy" {
		return "next_turn", nil
	}
	return "stdin", nil
}

func (a *ClaudeCodeAdapter) Status(h *Handle) string {
	if !h.Alive() {
		return "ended"
	}
	h.Mu.Lock()
	defer h.Mu.Unlock()
	return h.Status
}

func (a *ClaudeCodeAdapter) Stop(h *Handle) error {
	h.Mu.Lock()
	stdin := h.Stdin
	h.Stdin = nil
	h.Mu.Unlock()
	if stdin != nil {
		_ = stdin.Close()
	}
	terminateProcess(h.Cmd, h.Done, 10*time.Second)
	h.Mu.Lock()
	h.Status = "ended"
	h.Mu.Unlock()
	return nil
}

// --- CodexAdapter -----------------------------------------------------------

var codexSandboxByMode = map[string]string{
	"default":     "workspace-write",
	"acceptEdits": "workspace-write",
	"plan":        "read-only",
}

func SandboxForPermissionMode(mode string) string {
	if sb, ok := codexSandboxByMode[mode]; ok {
		return sb
	}
	return "read-only"
}

func GitWritableRoots(cwd string) []string {
	exe, err := exec.LookPath("git")
	if err != nil {
		return nil
	}
	out, err := exec.Command(exe, "-C", cwd, "rev-parse", "--path-format=absolute", "--git-dir", "--git-common-dir").Output()
	if err != nil {
		return nil
	}
	var roots []string
	for _, raw := range strings.Split(string(out), "\n") {
		line := pytext.Strip(raw)
		if line != "" && !slices.Contains(roots, line) {
			roots = append(roots, line)
		}
	}
	return roots
}

func SandboxPolicy(sandbox, cwd string) map[string]any {
	if sandbox != "workspace-write" {
		return nil
	}
	roots := []string{cwd}
	for _, r := range GitWritableRoots(cwd) {
		if !slices.Contains(roots, r) {
			roots = append(roots, r)
		}
	}
	return map[string]any{
		"type":          "workspaceWrite",
		"writableRoots": roots,
	}
}

type CodexAdapter struct{}

func (a *CodexAdapter) Name() string { return "codex" }

func (a *CodexAdapter) Probe() map[string]any {
	exe, err := exec.LookPath("codex")
	if err != nil {
		return map[string]any{"harness": a.Name(), "available": false}
	}
	out, _ := exec.Command(exe, "--version").Output()
	return map[string]any{
		"harness":   a.Name(),
		"available": true,
		"version":   pytext.Strip(string(out)),
		"actions":   []string{"spawn", "deliver", "deliver_mid_turn", "status", "stop"},
	}
}

func (a *CodexAdapter) Spawn(cwd, prompt, permissionMode string) (*Handle, error) {
	exe, err := exec.LookPath("codex")
	if err != nil {
		exe = "codex"
	}
	cmd := exec.Command(exe, "app-server")
	cmd.Dir = cwd
	stdin, err := cmd.StdinPipe()
	if err != nil {
		return nil, err
	}
	stdout, err := cmd.StdoutPipe()
	if err != nil {
		_ = stdin.Close()
		return nil, err
	}
	if err := cmd.Start(); err != nil {
		_ = stdin.Close()
		return nil, err
	}
	sb := SandboxForPermissionMode(permissionMode)
	h := &Handle{
		Harness:    a.Name(),
		Cmd:        cmd,
		Stdin:      stdin,
		Cwd:        cwd,
		Status:     "busy",
		Sandbox:    sb,
		SandboxPol: SandboxPolicy(sb, cwd),
		Done:       make(chan struct{}),
		waiting:    map[int]chan map[string]any{},
	}
	go a.readLoop(h, stdout)

	if _, err := a.request(h, "initialize", map[string]any{
		"clientInfo": map[string]any{"name": "workflow-hub-relay", "version": "1"},
	}, 60*time.Second); err != nil {
		_ = a.Stop(h)
		return nil, err
	}
	if err := a.send(h, map[string]any{"method": "initialized"}); err != nil {
		_ = a.Stop(h)
		return nil, err
	}
	r, err := a.request(h, "thread/start", map[string]any{
		"cwd":            cwd,
		"sandbox":        sb,
		"approvalPolicy": "never",
	}, 60*time.Second)
	if err != nil {
		_ = a.Stop(h)
		return nil, err
	}
	if res, ok := r["result"].(map[string]any); ok {
		if thread, ok := res["thread"].(map[string]any); ok {
			if tid, ok := thread["id"].(string); ok {
				h.HarnessSessionID = tid
			}
		}
	}
	if _, err := a.Deliver(h, prompt); err != nil {
		_ = a.Stop(h)
		return nil, err
	}
	return h, nil
}

func (a *CodexAdapter) send(h *Handle, msg map[string]any) error {
	raw, err := compactJSON(msg)
	if err != nil {
		return err
	}
	h.Mu.Lock()
	defer h.Mu.Unlock()
	if h.Stdin == nil {
		return errors.New("codex stdin closed")
	}
	_, err = h.Stdin.Write(append(raw, '\n'))
	return err
}

func (a *CodexAdapter) request(h *Handle, method string, params map[string]any, timeout time.Duration) (map[string]any, error) {
	h.Mu.Lock()
	h.nextID++
	rid := h.nextID
	ch := make(chan map[string]any, 1)
	if h.waiting == nil {
		h.waiting = map[int]chan map[string]any{}
	}
	h.waiting[rid] = ch
	h.Mu.Unlock()

	if err := a.send(h, map[string]any{"id": rid, "method": method, "params": params}); err != nil {
		h.Mu.Lock()
		delete(h.waiting, rid)
		h.Mu.Unlock()
		return nil, err
	}
	select {
	case got := <-ch:
		return got, nil
	case <-h.Done:
		h.Mu.Lock()
		delete(h.waiting, rid)
		h.Mu.Unlock()
		return nil, errors.New("codex process exited")
	case <-time.After(timeout):
		h.Mu.Lock()
		delete(h.waiting, rid)
		h.Mu.Unlock()
		return nil, nil
	}
}

func (a *CodexAdapter) readLoop(h *Handle, stdout io.ReadCloser) {
	defer func() {
		_ = h.Cmd.Wait()
		h.Mu.Lock()
		h.Status = "ended"
		h.Mu.Unlock()
		close(h.Done)
	}()
	sc := bufio.NewScanner(stdout)
	sc.Buffer(make([]byte, 0, 64*1024), 4*1024*1024)
	for sc.Scan() {
		var m map[string]any
		if err := json.Unmarshal(bytes.TrimSpace(sc.Bytes()), &m); err != nil {
			continue
		}
		_, hasID := m["id"]
		method, hasMethod := m["method"].(string)
		if hasID && hasMethod && method != "" {
			_ = a.send(h, map[string]any{
				"id":    m["id"],
				"error": map[string]any{"code": -32000, "message": "relay declines — no human"},
			})
			continue
		}
		if hasID {
			if idFloat, ok := m["id"].(float64); ok {
				rid := int(idFloat)
				h.Mu.Lock()
				ch := h.waiting[rid]
				if ch != nil {
					delete(h.waiting, rid)
				}
				h.Mu.Unlock()
				if ch != nil {
					ch <- m
				}
			}
			continue
		}
		if method == "turn/started" {
			h.Mu.Lock()
			if params, ok := m["params"].(map[string]any); ok {
				if turn, ok := params["turn"].(map[string]any); ok {
					if tid, ok := turn["id"].(string); ok {
						h.TurnID = tid
					}
				}
			}
			h.Status = "busy"
			h.Mu.Unlock()
		} else if method == "turn/completed" {
			h.Mu.Lock()
			h.TurnID = ""
			h.Status = "idle"
			h.Mu.Unlock()
		}
	}
}

func (a *CodexAdapter) Deliver(h *Handle, text string) (string, error) {
	items := []map[string]any{{"type": "text", "text": text}}
	h.Mu.Lock()
	turn := h.TurnID
	sid := h.HarnessSessionID
	pol := h.SandboxPol
	h.Mu.Unlock()

	if turn != "" {
		r, err := a.request(h, "turn/steer", map[string]any{
			"threadId":       sid,
			"expectedTurnId": turn,
			"input":          items,
		}, 60*time.Second)
		if err == nil && r != nil {
			if _, ok := r["result"]; ok {
				return "steer", nil
			}
		}
	}

	h.Mu.Lock()
	h.Status = "busy"
	h.Mu.Unlock()

	params := map[string]any{
		"threadId": sid,
		"input":    items,
	}
	if pol != nil {
		params["sandboxPolicy"] = pol
	}
	r, err := a.request(h, "turn/start", params, 60*time.Second)
	if err != nil {
		return "turn", err
	}
	if r != nil {
		if res, ok := r["result"].(map[string]any); ok {
			if turnObj, ok := res["turn"].(map[string]any); ok {
				if tid, ok := turnObj["id"].(string); ok && tid != "" {
					h.Mu.Lock()
					h.TurnID = tid
					h.Mu.Unlock()
				}
			}
		}
	}
	return "turn", nil
}

func (a *CodexAdapter) Status(h *Handle) string {
	if !h.Alive() {
		return "ended"
	}
	h.Mu.Lock()
	defer h.Mu.Unlock()
	return h.Status
}

func (a *CodexAdapter) Stop(h *Handle) error {
	h.Mu.Lock()
	turn := h.TurnID
	sid := h.HarnessSessionID
	h.Mu.Unlock()
	if turn != "" && h.Alive() {
		_, _ = a.request(h, "turn/interrupt", map[string]any{
			"threadId": sid,
			"turnId":   turn,
		}, 10*time.Second)
		time.Sleep(500 * time.Millisecond)
	}
	h.Mu.Lock()
	stdin := h.Stdin
	h.Stdin = nil
	h.Mu.Unlock()
	if stdin != nil {
		_ = stdin.Close()
	}
	terminateProcess(h.Cmd, h.Done, 10*time.Second)
	h.Mu.Lock()
	h.Status = "ended"
	h.Mu.Unlock()
	return nil
}

var _ = filepath.Join
