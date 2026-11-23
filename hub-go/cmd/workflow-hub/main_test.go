package main

import (
	"bytes"
	"strings"
	"testing"
)

func TestVersion(t *testing.T) {
	for _, flag := range []string{"--version", "-v", "version"} {
		var out, errBuf bytes.Buffer
		rc := run([]string{flag}, &out, &errBuf)
		if rc != 0 {
			t.Fatalf("%s: got rc=%d, want 0 (stderr=%q)", flag, rc, errBuf.String())
		}
		want := "workflow-hub " + version
		if got := strings.TrimSpace(out.String()); got != want {
			t.Fatalf("%s: got %q, want %q", flag, got, want)
		}
		if errBuf.Len() != 0 {
			t.Fatalf("%s: unexpected stderr %q", flag, errBuf.String())
		}
	}
}

func TestHelpAndCommands(t *testing.T) {
	t.Run("help", func(t *testing.T) {
		for _, flag := range []string{"--help", "-h", "help"} {
			var out, errBuf bytes.Buffer
			rc := run([]string{flag}, &out, &errBuf)
			if rc != 0 {
				t.Fatalf("%s: got rc=%d, want 0", flag, rc)
			}
			for _, sub := range []string{"serve", "backup", "admin", "relay", "judge"} {
				if !strings.Contains(out.String(), sub) {
					t.Fatalf("%s: help output missing %q: %q", flag, sub, out.String())
				}
			}
		}
	})

	t.Run("no_args", func(t *testing.T) {
		var out, errBuf bytes.Buffer
		rc := run(nil, &out, &errBuf)
		if rc != 2 {
			t.Fatalf("no args: got rc=%d, want 2", rc)
		}
		if !strings.Contains(errBuf.String(), "usage: workflow-hub") {
			t.Fatalf("no args: unexpected stderr %q", errBuf.String())
		}
	})

	t.Run("relay_wired", func(t *testing.T) {
		t.Setenv("WORKFLOW_HUB_RELAY_HOME", t.TempDir())
		var out, errBuf bytes.Buffer
		rc := run([]string{"relay", "status"}, &out, &errBuf)
		if rc != 0 {
			t.Fatalf("relay status: got rc=%d, want 0 (stderr=%q)", rc, errBuf.String())
		}
		if !strings.Contains(out.String(), `"registered": false`) {
			t.Fatalf("relay status: unexpected stdout %q", out.String())
		}
	})

	t.Run("judge_wired", func(t *testing.T) {
		var out, errBuf bytes.Buffer
		rc := run([]string{"judge"}, &out, &errBuf)
		if rc != 2 {
			t.Fatalf("judge no op: got rc=%d, want 2", rc)
		}
		if !strings.Contains(out.String(), `"error_code":"invalid_args"`) {
			t.Fatalf("judge no op: unexpected stdout %q", out.String())
		}
	})

	t.Run("hub_commands_wired", func(t *testing.T) {
		tmp := t.TempDir()
		dbPath := tmp + "/hub.db"
		outPath := tmp + "/backup.db"

		// Missing flags return exit 2
		for _, args := range [][]string{{"serve"}, {"backup"}, {"admin"}} {
			var out, errBuf bytes.Buffer
			if rc := run(args, &out, &errBuf); rc != 2 {
				t.Fatalf("%v: got rc=%d, want 2", args, rc)
			}
		}

		// admin token issue & revoke + backup round-trip
		var out, errBuf bytes.Buffer
		if rc := run([]string{"admin", "--db", dbPath, "token", "issue", "--role", "admin", "--name", "ops"}, &out, &errBuf); rc != 0 {
			t.Fatalf("admin token issue failed rc=%d stderr=%q", rc, errBuf.String())
		}
		if !strings.Contains(out.String(), `"status":"ok"`) || !strings.Contains(out.String(), `"token":"wfh_`) {
			t.Fatalf("unexpected token issue output: %q", out.String())
		}

		out.Reset()
		errBuf.Reset()
		if rc := run([]string{"backup", "--db", dbPath, "--out", outPath}, &out, &errBuf); rc != 0 {
			t.Fatalf("backup failed rc=%d stderr=%q", rc, errBuf.String())
		}
		if !strings.Contains(out.String(), `"status":"ok"`) {
			t.Fatalf("unexpected backup output: %q", out.String())
		}

		out.Reset()
		errBuf.Reset()
		if rc := run([]string{"admin", "--db", dbPath, "token", "revoke", "--name", "ops"}, &out, &errBuf); rc != 0 {
			t.Fatalf("admin token revoke failed rc=%d stderr=%q", rc, errBuf.String())
		}
	})

	t.Run("unknown_command", func(t *testing.T) {
		var out, errBuf bytes.Buffer
		rc := run([]string{"bogus"}, &out, &errBuf)
		if rc != 2 {
			t.Fatalf("bogus: got rc=%d, want 2", rc)
		}
		if !strings.Contains(errBuf.String(), "unknown command") {
			t.Fatalf("bogus: unexpected stderr %q", errBuf.String())
		}
	})
}
