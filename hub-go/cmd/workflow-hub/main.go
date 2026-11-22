package main

import (
	"fmt"
	"io"
	"os"
	"strings"

	"github.com/ykylee/standard_ai_workflow/hub-go/internal/judge"
	"github.com/ykylee/standard_ai_workflow/hub-go/internal/relay"
)

// version 은 -ldflags "-X main.version=<판>" 로 덮어쓴다 (hub_go_spec.md §7).
var version = "2.1.0"

var subcommands = []string{"serve", "backup", "admin", "relay", "judge"}

func printUsage(w io.Writer) {
	fmt.Fprintf(w, "usage: workflow-hub <command> [args...]\n\n")
	fmt.Fprintf(w, "commands:\n")
	fmt.Fprintf(w, "  %s\n", strings.Join(subcommands, " | "))
	fmt.Fprintf(w, "  --version    print version and exit\n")
	fmt.Fprintf(w, "  --help       print this help and exit\n")
}

func isKnownSubcommand(cmd string) bool {
	for _, s := range subcommands {
		if s == cmd {
			return true
		}
	}
	return false
}

func run(args []string, stdout, stderr io.Writer) int {
	if len(args) == 0 {
		printUsage(stderr)
		return 2
	}
	switch args[0] {
	case "__fake-worker":
		return relay.RunFakeWorker()
	case "--version", "-v", "version":
		fmt.Fprintf(stdout, "workflow-hub %s\n", version)
		return 0
	case "--help", "-h", "help":
		printUsage(stdout)
		return 0
	case "relay":
		return relay.Main(args[1:], stdout, stderr)
	case "judge":
		return judge.Main(args[1:], os.Stdin, stdout, stderr)
	}
	cmd := args[0]
	if isKnownSubcommand(cmd) {
		fmt.Fprintf(stderr, "workflow-hub %s: not implemented yet\n", cmd)
		return 2
	}
	fmt.Fprintf(stderr, "workflow-hub: unknown command %q\n", cmd)
	return 2
}

func main() {
	os.Exit(run(os.Args[1:], os.Stdout, os.Stderr))
}
