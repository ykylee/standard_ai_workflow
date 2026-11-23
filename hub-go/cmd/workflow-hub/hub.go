package main

import (
	"bytes"
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"net"
	"net/http"
	"os"
	"os/signal"
	"strings"
	"syscall"
	"time"

	"github.com/ykylee/standard_ai_workflow/hub-go/internal/db"
	"github.com/ykylee/standard_ai_workflow/hub-go/internal/httpapi"
	"github.com/ykylee/standard_ai_workflow/hub-go/internal/store"
)

func utcNow() time.Time {
	return time.Now().UTC().Truncate(time.Second)
}

func isLoopbackHost(bind string) bool {
	if bind == "localhost" {
		return true
	}
	ip := net.ParseIP(bind)
	return ip != nil && ip.IsLoopback()
}

func writeJSONOut(w io.Writer, v any) {
	var buf bytes.Buffer
	enc := json.NewEncoder(&buf)
	enc.SetEscapeHTML(false)
	_ = enc.Encode(v)
	_, _ = w.Write(buf.Bytes())
}

func writeHubErrOut(stdout, stderr io.Writer, err error) int {
	if he, ok := store.AsHubError(err); ok {
		out := map[string]any{"status": "error"}
		for k, v := range he.Payload() {
			out[k] = v
		}
		writeJSONOut(stdout, out)
		return 1
	}
	fmt.Fprintf(stderr, "hub: %v\n", err)
	return 2
}

func newFlagSet(name string, stderr io.Writer) *flag.FlagSet {
	fs := flag.NewFlagSet(name, flag.ContinueOnError)
	fs.SetOutput(stderr)
	return fs
}

func cmdServe(args []string, stdout, stderr io.Writer) int {
	fs := newFlagSet("workflow-hub serve", stderr)
	dbPath := fs.String("db", "", "허브 SQLite DB 경로")
	bind := fs.String("bind", "127.0.0.1", "바인드 주소")
	port := fs.Int("port", 8770, "포트")
	publicURL := fs.String("public-url", "", "허브 공개 주소 (기본: http://<bind>:<port>)")
	webTokenName := fs.String("web-token-name", "", "화면 공용 web 토큰 이름")
	if err := fs.Parse(args); err != nil {
		if err == flag.ErrHelp {
			return 0
		}
		return 2
	}
	if strings.TrimSpace(*dbPath) == "" {
		fmt.Fprintln(stderr, "hub serve: --db 가 필수다")
		return 2
	}

	now := utcNow()
	copies, err := db.OpenDB(*dbPath, now)
	if err != nil {
		return writeHubErrOut(stdout, stderr, err)
	}
	st, err := store.New(*dbPath)
	if err != nil {
		return writeHubErrOut(stdout, stderr, err)
	}
	defer func() { _ = st.Close() }()

	loopback := isLoopbackHost(*bind)
	if !loopback {
		fmt.Fprintf(
			stderr,
			"hub: 경고 — loopback 이 아닌 %s 에 bind 한다. 이 허브에 닿는 누구나 프로젝트를 등록할 수 있다 (요구 R3.4 · R13.3). 바깥 노출은 프록시 뒤에서 한다.\n",
			*bind,
		)
	}
	for _, c := range copies {
		fmt.Fprintf(stderr, "hub: 이관 전 사본 %s\n", c)
	}
	if *webTokenName != "" {
		wp, wpErr := st.WebPrincipal(*webTokenName)
		if wpErr != nil {
			return writeHubErrOut(stdout, stderr, wpErr)
		}
		if wp == nil {
			fmt.Fprintf(stderr, "hub: 화면 공용 토큰이 없다: %s — `hub admin token issue --role web --name …` 로 먼저 발급한다\n", *webTokenName)
			return 2
		}
	}

	addr := fmt.Sprintf("%s:%d", *bind, *port)
	ln, err := net.Listen("tcp", addr)
	if err != nil {
		fmt.Fprintf(stderr, "hub serve: %v\n", err)
		return 2
	}
	actualPort := *port
	if tcpAddr, ok := ln.Addr().(*net.TCPAddr); ok {
		actualPort = tcpAddr.Port
	}
	listenURL := fmt.Sprintf("http://%s:%d", *bind, actualPort)
	pub := strings.TrimSpace(*publicURL)
	if pub == "" {
		pub = listenURL
	}
	exposure := "non-loopback"
	if loopback {
		exposure = "loopback"
	}
	srv := httpapi.New(httpapi.Config{
		Store:        st,
		PublicURL:    pub,
		Exposure:     exposure,
		WebTokenName: *webTokenName,
		Clock:        utcNow,
	})
	dbVer, _ := st.DBVersion()
	writeJSONOut(stdout, map[string]any{
		"status":     "serving",
		"url":        listenURL,
		"public_url": pub,
		"db_version": dbVer,
	})

	httpSrv := &http.Server{Handler: srv}
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()
	go func() {
		<-ctx.Done()
		shutCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		_ = httpSrv.Shutdown(shutCtx)
	}()

	if err := httpSrv.Serve(ln); err != nil && err != http.ErrServerClosed {
		fmt.Fprintf(stderr, "hub serve: %v\n", err)
		return 2
	}
	return 0
}

func cmdBackup(args []string, stdout, stderr io.Writer) int {
	fs := newFlagSet("workflow-hub backup", stderr)
	dbPath := fs.String("db", "", "원본 허브 SQLite DB 경로")
	outPath := fs.String("out", "", "백업 출력 파일 경로")
	if err := fs.Parse(args); err != nil {
		if err == flag.ErrHelp {
			return 0
		}
		return 2
	}
	if strings.TrimSpace(*dbPath) == "" || strings.TrimSpace(*outPath) == "" {
		fmt.Fprintln(stderr, "hub backup: --db 와 --out 이 필수다")
		return 2
	}
	if err := db.Backup(*dbPath, *outPath); err != nil {
		return writeHubErrOut(stdout, stderr, err)
	}
	writeJSONOut(stdout, map[string]any{"status": "ok", "backup": *outPath})
	return 0
}

func cmdMigrate(args []string, stdout, stderr io.Writer) int {
	fs := newFlagSet("workflow-hub migrate", stderr)
	source := fs.String("from-sqlite", "", "원본 SQLite DB 경로")
	target := fs.String("to-postgres", "", "대상 PostgreSQL URL")
	if err := fs.Parse(args); err != nil {
		if err == flag.ErrHelp {
			return 0
		}
		return 2
	}
	if strings.TrimSpace(*source) == "" || strings.TrimSpace(*target) == "" {
		fmt.Fprintln(stderr, "hub migrate: --from-sqlite 와 --to-postgres 가 필요하다")
		return 2
	}
	summary, err := db.CopySQLiteToPostgres(*source, *target, utcNow())
	if err != nil {
		return writeHubErrOut(stdout, stderr, err)
	}
	writeJSONOut(stdout, summary)
	return 0
}

func cmdAdmin(args []string, stdout, stderr io.Writer) int {
	fs := newFlagSet("workflow-hub admin", stderr)
	dbPath := fs.String("db", "", "허브 SQLite DB 경로")
	if err := fs.Parse(args); err != nil {
		if err == flag.ErrHelp {
			return 0
		}
		return 2
	}
	if strings.TrimSpace(*dbPath) == "" {
		fmt.Fprintln(stderr, "hub admin: --db 가 필수다")
		return 2
	}
	rest := fs.Args()
	if len(rest) < 2 {
		fmt.Fprintln(stderr, "hub admin: token {issue|revoke} 또는 callsign revoke 를 지정한다")
		return 2
	}

	now := utcNow()
	if _, err := db.OpenDB(*dbPath, now); err != nil {
		return writeHubErrOut(stdout, stderr, err)
	}
	st, err := store.New(*dbPath)
	if err != nil {
		return writeHubErrOut(stdout, stderr, err)
	}
	defer func() { _ = st.Close() }()

	what, action := rest[0], rest[1]
	subArgs := rest[2:]
	switch what {
	case "token":
		switch action {
		case "issue":
			tfs := newFlagSet("workflow-hub admin token issue", stderr)
			role := tfs.String("role", "", "토큰 역할 (web|admin)")
			name := tfs.String("name", "", "토큰 이름")
			if err := tfs.Parse(subArgs); err != nil {
				if err == flag.ErrHelp {
					return 0
				}
				return 2
			}
			if (*role != "web" && *role != "admin") || strings.TrimSpace(*name) == "" {
				fmt.Fprintln(stderr, "hub admin token issue: --role {web|admin} 과 --name 이 필수다")
				return 2
			}
			tok, err := st.IssueHubToken(*role, *name, now)
			if err != nil {
				return writeHubErrOut(stdout, stderr, err)
			}
			writeJSONOut(stdout, map[string]any{"status": "ok", "name": *name, "role": *role, "token": tok})
			return 0
		case "revoke":
			tfs := newFlagSet("workflow-hub admin token revoke", stderr)
			name := tfs.String("name", "", "토큰 이름")
			if err := tfs.Parse(subArgs); err != nil {
				if err == flag.ErrHelp {
					return 0
				}
				return 2
			}
			if strings.TrimSpace(*name) == "" {
				fmt.Fprintln(stderr, "hub admin token revoke: --name 이 필수다")
				return 2
			}
			if err := st.RevokeHubToken(*name, now); err != nil {
				return writeHubErrOut(stdout, stderr, err)
			}
			writeJSONOut(stdout, map[string]any{"status": "ok", "revoked": *name})
			return 0
		default:
			fmt.Fprintf(stderr, "hub admin token: 모르는 동작 %q\n", action)
			return 2
		}
	case "callsign":
		if action != "revoke" {
			fmt.Fprintf(stderr, "hub admin callsign: 모르는 동작 %q\n", action)
			return 2
		}
		cfs := newFlagSet("workflow-hub admin callsign revoke", stderr)
		project := cfs.String("project", "", "프로젝트 ID")
		callsign := cfs.String("callsign", "", "콜사인")
		if err := cfs.Parse(subArgs); err != nil {
			if err == flag.ErrHelp {
				return 0
			}
			return 2
		}
		if strings.TrimSpace(*project) == "" || strings.TrimSpace(*callsign) == "" {
			fmt.Fprintln(stderr, "hub admin callsign revoke: --project 와 --callsign 이 필수다")
			return 2
		}
		res, err := st.RevokeCallsign(store.Ctx{Now: now, Via: "admin"}, *project, *callsign)
		if err != nil {
			return writeHubErrOut(stdout, stderr, err)
		}
		out := map[string]any{"status": "ok"}
		for k, v := range res {
			out[k] = v
		}
		writeJSONOut(stdout, out)
		return 0
	default:
		fmt.Fprintf(stderr, "hub admin %s %s: Go 허브에 아직 포팅되지 않았다\n", what, action)
		return 2
	}
}
