package relay

import (
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"strconv"
	"strings"
)

func printPrettyJSON(w io.Writer, v any) {
	enc := json.NewEncoder(w)
	enc.SetEscapeHTML(false)
	enc.SetIndent("", "  ")
	_ = enc.Encode(v)
}

type parsedFlags struct {
	values map[string][]string
	bools  map[string]bool
	pos    []string
}

func parseArgs(args []string, valueFlags, boolFlags map[string]bool) (*parsedFlags, error) {
	pf := &parsedFlags{
		values: map[string][]string{},
		bools:  map[string]bool{},
		pos:    []string{},
	}
	for i := 0; i < len(args); i++ {
		arg := args[i]
		if arg == "--" {
			pf.pos = append(pf.pos, args[i+1:]...)
			break
		}
		if strings.HasPrefix(arg, "--") {
			name := arg
			hasEq := false
			eqVal := ""
			if idx := strings.IndexByte(arg, '='); idx >= 0 {
				name = arg[:idx]
				eqVal = arg[idx+1:]
				hasEq = true
			}
			if boolFlags[name] {
				if hasEq {
					b, err := strconv.ParseBool(eqVal)
					if err != nil {
						return nil, fmt.Errorf("invalid boolean value %q for %s", eqVal, name)
					}
					pf.bools[name] = b
				} else {
					pf.bools[name] = true
				}
				continue
			}
			if valueFlags[name] {
				if hasEq {
					pf.values[name] = append(pf.values[name], eqVal)
				} else {
					if i+1 >= len(args) {
						return nil, fmt.Errorf("flag %s requires a value", name)
					}
					i++
					pf.values[name] = append(pf.values[name], args[i])
				}
				continue
			}
			return nil, fmt.Errorf("unknown flag: %s", name)
		}
		if arg == "-h" {
			pf.bools["--help"] = true
			continue
		}
		if strings.HasPrefix(arg, "-") && len(arg) > 1 {
			return nil, fmt.Errorf("unknown flag: %s", arg)
		}
		pf.pos = append(pf.pos, arg)
	}
	return pf, nil
}

func (pf *parsedFlags) get(name, def string) string {
	vals := pf.values[name]
	if len(vals) == 0 {
		return def
	}
	return vals[len(vals)-1]
}

func (pf *parsedFlags) all(name string) []string {
	return pf.values[name]
}

func printRelayHelp(w io.Writer) {
	fmt.Fprintln(w, "usage: workflow-hub relay {init,allow,serve,pause,resume,status} [args...]")
}

func Main(args []string, stdout, stderr io.Writer) int {
	if len(args) == 0 {
		printRelayHelp(stderr)
		return 2
	}
	cmd := args[0]
	rest := args[1:]
	if cmd == "-h" || cmd == "--help" || cmd == "help" {
		printRelayHelp(stdout)
		return 0
	}

	switch cmd {
	case "init":
		return runInit(rest, stdout, stderr)
	case "allow":
		return runAllow(rest, stdout, stderr)
	case "pause", "resume":
		return runPauseResume(cmd == "pause", rest, stdout, stderr)
	case "status":
		return runStatus(rest, stdout, stderr)
	case "serve":
		return runServe(rest, stdout, stderr)
	default:
		fmt.Fprintf(stderr, "relay: unknown subcommand %q\n", cmd)
		return 2
	}
}

func runInit(args []string, stdout, stderr io.Writer) int {
	pf, err := parseArgs(
		args,
		map[string]bool{"--hub": true, "--invite": true, "--name": true, "--harness": true},
		map[string]bool{"--help": true},
	)
	if err != nil {
		fmt.Fprintf(stderr, "relay: %v\n", err)
		return 2
	}
	if pf.bools["--help"] {
		fmt.Fprintln(stdout, "usage: workflow-hub relay init --hub URL --invite CODE [--name NAME] [--harness H]")
		return 0
	}
	hubURL := pf.get("--hub", "")
	invite := pf.get("--invite", "")
	if hubURL == "" || invite == "" {
		fmt.Fprintln(stderr, "relay: --hub 와 --invite 는 필수다")
		return 2
	}
	name := pf.get("--name", "")
	if name == "" {
		hn, _ := os.Hostname()
		name = hn
	}
	harnesses := pf.all("--harness")
	if len(harnesses) == 0 {
		harnesses = []string{"claude-code", "codex"}
	}
	var bad []string
	for _, h := range harnesses {
		if !IsKnownAdapter(h) {
			bad = append(bad, h)
		}
	}
	if len(bad) > 0 {
		fmt.Fprintf(stderr, "relay: 모르는 어댑터 %v\n", bad)
		return 2
	}
	got, err := Post(hubURL, "/v1/relay/register", map[string]any{
		"invite":    invite,
		"name":      name,
		"harnesses": harnesses,
	}, "", 0)
	if err != nil {
		var hubErr *HubError
		var hubUnreach *HubUnreachable
		if errors.As(err, &hubErr) {
			fmt.Fprintf(stderr, "relay: 등록 거절 — %v\n", err)
			return 1
		}
		if errors.As(err, &hubUnreach) {
			fmt.Fprintf(stderr, "relay: 허브에 닿지 않는다 — %v\n", err)
			return 2
		}
		fmt.Fprintf(stderr, "relay: %v\n", err)
		return 2
	}
	token, _ := got["token"].(string)
	if err := WriteToken(token); err != nil {
		fmt.Fprintf(stderr, "relay: 토큰 저장 실패 — %v\n", err)
		return 2
	}
	if err := WriteJSON("relay.json", map[string]any{
		"hub":        hubURL,
		"host_id":    got["host_id"],
		"project_id": got["project_id"],
		"name":       name,
		"harnesses":  harnesses,
	}); err != nil {
		fmt.Fprintf(stderr, "relay: 설정 저장 실패 — %v\n", err)
		return 2
	}
	printPrettyJSON(stdout, map[string]any{
		"status":     "ok",
		"host_id":    got["host_id"],
		"project_id": got["project_id"],
		"config":     Home(),
		"next":       "hub relay allow add … → hub relay serve",
	})
	return 0
}

func runAllow(args []string, stdout, stderr io.Writer) int {
	if len(args) == 0 {
		fmt.Fprintln(stderr, "usage: workflow-hub relay allow {add,remove,list}")
		return 2
	}
	action := args[0]
	rest := args[1:]
	if action == "-h" || action == "--help" {
		fmt.Fprintln(stdout, "usage: workflow-hub relay allow {add,remove,list}")
		return 0
	}

	entries, err := LoadAllow()
	if err != nil {
		fmt.Fprintf(stderr, "relay: 허용 목록 읽기 실패 — %v\n", err)
		return 2
	}

	switch action {
	case "list":
		printPrettyJSON(stdout, map[string]any{
			"dir":    entries,
			"digest": AllowDigest(entries),
		})
		return 0
	case "remove":
		pf, err := parseArgs(rest, map[string]bool{"--alias": true}, map[string]bool{"--help": true})
		if err != nil {
			fmt.Fprintf(stderr, "relay: %v\n", err)
			return 2
		}
		if pf.bools["--help"] {
			fmt.Fprintln(stdout, "usage: workflow-hub relay allow remove --alias ALIAS")
			return 0
		}
		alias := pf.get("--alias", "")
		if alias == "" {
			fmt.Fprintln(stderr, "relay: --alias 는 필수다")
			return 2
		}
		kept := make([]AllowEntry, 0, len(entries))
		for _, e := range entries {
			if e.Alias != alias {
				kept = append(kept, e)
			}
		}
		if err := SaveAllow(kept); err != nil {
			fmt.Fprintf(stderr, "relay: 허용 목록 저장 실패 — %v\n", err)
			return 2
		}
		printPrettyJSON(stdout, map[string]any{
			"status":  "ok",
			"removed": len(entries) - len(kept),
		})
		return 0
	case "add":
		pf, err := parseArgs(
			rest,
			map[string]bool{
				"--alias": true, "--path": true, "--project": true,
				"--harness": true, "--permission-mode": true, "--max-sessions": true,
			},
			map[string]bool{"--help": true},
		)
		if err != nil {
			fmt.Fprintf(stderr, "relay: %v\n", err)
			return 2
		}
		if pf.bools["--help"] {
			fmt.Fprintln(stdout, "usage: workflow-hub relay allow add --alias ALIAS --path DIR --harness H [--project P] [--permission-mode M] [--max-sessions N]")
			return 0
		}
		alias := pf.get("--alias", "")
		path := pf.get("--path", "")
		harnesses := pf.all("--harness")
		if alias == "" || path == "" || len(harnesses) == 0 {
			fmt.Fprintln(stderr, "relay: --alias · --path · --harness 는 필수다")
			return 2
		}
		project := pf.get("--project", "")
		if project == "" {
			cfg, _ := ReadJSON("relay.json")
			project, _ = cfg["project_id"].(string)
		}
		modes := pf.all("--permission-mode")
		if len(modes) == 0 {
			modes = []string{"default"}
		}
		maxSessions := 1
		if rawMax := pf.get("--max-sessions", ""); rawMax != "" {
			n, convErr := strconv.Atoi(rawMax)
			if convErr != nil {
				fmt.Fprintf(stderr, "relay: --max-sessions 는 정수여야 한다: %q\n", rawMax)
				return 2
			}
			maxSessions = n
		}
		entry := AllowEntry{
			Alias:           alias,
			Harnesses:       harnesses,
			MaxSessions:     maxSessions,
			Path:            path,
			PermissionModes: modes,
			Project:         project,
		}
		if errMsg := ValidateEntry(entry); errMsg != "" {
			fmt.Fprintf(stderr, "relay: 허용 목록 거절 — %s\n", errMsg)
			return 2
		}
		updated := make([]AllowEntry, 0, len(entries)+1)
		for _, e := range entries {
			if e.Alias != alias {
				updated = append(updated, e)
			}
		}
		updated = append(updated, entry)
		if err := SaveAllow(updated); err != nil {
			fmt.Fprintf(stderr, "relay: 허용 목록 저장 실패 — %v\n", err)
			return 2
		}
		printPrettyJSON(stdout, map[string]any{
			"status": "ok",
			"entry":  entry,
		})
		return 0
	default:
		fmt.Fprintf(stderr, "relay: unknown allow action %q\n", action)
		return 2
	}
}

func runPauseResume(paused bool, args []string, stdout, stderr io.Writer) int {
	pf, err := parseArgs(args, map[string]bool{}, map[string]bool{"--help": true})
	if err != nil {
		fmt.Fprintf(stderr, "relay: %v\n", err)
		return 2
	}
	if pf.bools["--help"] {
		fmt.Fprintln(stdout, "usage: workflow-hub relay pause|resume")
		return 0
	}
	st, err := ReadJSON("relay-state.json")
	if err != nil {
		fmt.Fprintf(stderr, "relay: 상태 읽기 실패 — %v\n", err)
		return 2
	}
	st["paused"] = paused
	if err := WriteJSON("relay-state.json", st); err != nil {
		fmt.Fprintf(stderr, "relay: 상태 저장 실패 — %v\n", err)
		return 2
	}
	printPrettyJSON(stdout, map[string]any{
		"status": "ok",
		"paused": paused,
	})
	return 0
}

func runStatus(args []string, stdout, stderr io.Writer) int {
	pf, err := parseArgs(args, map[string]bool{}, map[string]bool{"--help": true})
	if err != nil {
		fmt.Fprintf(stderr, "relay: %v\n", err)
		return 2
	}
	if pf.bools["--help"] {
		fmt.Fprintln(stdout, "usage: workflow-hub relay status")
		return 0
	}
	cfg, err := ReadJSON("relay.json")
	if err != nil {
		fmt.Fprintf(stderr, "relay: 설정 읽기 실패 — %v\n", err)
		return 2
	}
	st, _ := ReadJSON("relay-state.json")
	entries, _ := LoadAllow()
	_, hasToken := ReadToken()
	hostID, _ := cfg["host_id"].(string)

	allowAliases := make([]string, 0, len(entries))
	for _, e := range entries {
		allowAliases = append(allowAliases, e.Alias)
	}

	adapterInfo := map[string]any{}
	if harnessesRaw, ok := cfg["harnesses"].([]any); ok {
		for _, item := range harnessesRaw {
			if name, ok := item.(string); ok {
				if ad, aerr := GetAdapter(name); aerr == nil {
					adapterInfo[name] = ad.Probe()
				}
			}
		}
	}
	paused, _ := st["paused"].(bool)

	printPrettyJSON(stdout, map[string]any{
		"registered": hostID != "" && hasToken,
		"hub":        cfg["hub"],
		"host_id":    cfg["host_id"],
		"project_id": cfg["project_id"],
		"name":       cfg["name"],
		"harnesses":  cfg["harnesses"],
		"paused":     paused,
		"allow":      allowAliases,
		"adapters":   adapterInfo,
	})
	return 0
}

func runServe(args []string, stdout, stderr io.Writer) int {
	pf, err := parseArgs(
		args,
		map[string]bool{"--wait": true, "--ui-port": true},
		map[string]bool{"--once": true, "--help": true},
	)
	if err != nil {
		fmt.Fprintf(stderr, "relay: %v\n", err)
		return 2
	}
	if pf.bools["--help"] {
		fmt.Fprintln(stdout, "usage: workflow-hub relay serve [--once] [--wait N] [--ui-port PORT]")
		return 0
	}
	waitS := 25
	if rawWait := pf.get("--wait", ""); rawWait != "" {
		n, convErr := strconv.Atoi(rawWait)
		if convErr != nil {
			fmt.Fprintf(stderr, "relay: --wait 는 정수여야 한다: %q\n", rawWait)
			return 2
		}
		waitS = n
	}
	uiPort := 0
	if rawPort := pf.get("--ui-port", ""); rawPort != "" {
		n, convErr := strconv.Atoi(rawPort)
		if convErr != nil {
			fmt.Fprintf(stderr, "relay: --ui-port 는 정수여야 한다: %q\n", rawPort)
			return 2
		}
		uiPort = n
	}
	r, err := NewRelay(func(m string) {
		fmt.Fprintf(stderr, "relay: %s\n", m)
	})
	if err != nil {
		fmt.Fprintln(stderr, err.Error())
		return 2
	}
	return r.Serve(pf.bools["--once"], waitS, uiPort)
}
