package main

import (
	"crypto/rand"
	"encoding/hex"
	"flag"
	"fmt"
	"io"
	"os"
	"time"

	"github.com/ykylee/standard_ai_workflow/hub-go/internal/db"
	"github.com/ykylee/standard_ai_workflow/hub-go/internal/store"
	"github.com/ykylee/standard_ai_workflow/hub-go/internal/tools"
)

// cmdAdminProject mirrors `hub admin project {export|import|seal|unseal|invite}` of the Python hub.
func cmdAdminProject(st *store.Store, dbPath, action string, args []string, now time.Time, stdout, stderr io.Writer) int {
	fs := newAdminFlagSet("workflow-hub admin project", stderr)
	project := fs.String("project", "", "프로젝트 ID")
	out := fs.String("out", "", "묶음 파일")
	sealTo := fs.String("seal-to", "", "새 허브 주소 — 주면 봉인한 뒤 묶음을 뜬다")
	publicURL := fs.String("public-url", "", "이 허브의 공개 주소")
	file := fs.String("file", "", "들일 묶음 파일")
	to := fs.String("to", "", "새 허브 주소")
	hours := fs.Int("hours", 24, "초대 코드 유효 시간")
	note := fs.String("note", "", "메모")
	if err := fs.Parse(args); err != nil {
		if err == flag.ErrHelp {
			return 0
		}
		return 2
	}
	need := func(ok bool, what string) bool {
		if !ok {
			fmt.Fprintf(stderr, "hub admin project %s: %s 가 필수다\n", action, what)
		}
		return ok
	}
	var res map[string]any
	var err error
	switch action {
	case "export":
		if !need(*project != "" && *out != "", "--project 와 --out") {
			return 2
		}
		var sealed any
		if *sealTo != "" {
			if sealed, err = st.Seal(*project, *sealTo, now); err != nil {
				return writeHubErrOut(stdout, stderr, err)
			}
		}
		bundle, err := st.ExportBundle(*project, now, *publicURL)
		if err != nil {
			return writeHubErrOut(stdout, stderr, err)
		}
		text, err := store.EncodeJSON(bundle)
		if err == nil { // 토큰 해시 · 프로젝트 기록이 들어 있다 — 소유자만 읽는다
			err = os.WriteFile(*out, []byte(text+"\n"), 0o600)
		}
		if err == nil {
			err = os.Chmod(*out, 0o600)
		}
		if err != nil {
			fmt.Fprintf(stderr, "hub admin project export: %v\n", err)
			return 2
		}
		res = map[string]any{"out": *out, "sealed": sealed, "counts": bundle["counts"], "digest": bundle["digest"]}
	case "import":
		if !need(*file != "", "--file") {
			return 2
		}
		raw, readErr := os.ReadFile(*file)
		if readErr != nil {
			fmt.Fprintf(stderr, "hub admin project import: %v\n", readErr)
			return 2
		}
		bundle, decodeErr := tools.DecodeJSONValue(raw)
		if decodeErr != nil {
			return writeHubErrOut(stdout, stderr, &store.HubError{Status: 400, Code: "invalid_bundle", Message: "묶음이 JSON 이 아니다"})
		}
		var mark [3]byte
		_, _ = rand.Read(mark[:])
		if backupErr := db.Backup(dbPath, dbPath+".pre-import-"+now.Format("20060102T150405Z")+"-"+hex.EncodeToString(mark[:])); backupErr != nil {
			return writeHubErrOut(stdout, stderr, backupErr)
		}
		res, err = st.ImportBundle(bundle, now, nil)
	case "seal":
		if !need(*project != "" && *to != "", "--project 와 --to") {
			return 2
		}
		res, err = st.Seal(*project, *to, now)
	case "unseal":
		if !need(*project != "", "--project") {
			return 2
		}
		res, err = st.Unseal(*project, now)
	case "invite":
		if !need(*project != "", "--project") {
			return 2
		}
		if res, err = st.IssueProjectInvite(*project, now, *hours, *note); err == nil {
			res["note"] = "코드는 지금 한 번만 보인다 — 소유자에게 전한다"
		}
	default:
		fmt.Fprintln(stderr, "hub admin project: 모르는 동작 (export · import · seal · unseal · invite)")
		return 2
	}
	if err != nil {
		return writeHubErrOut(stdout, stderr, err)
	}
	payload := map[string]any{"status": "ok"}
	for k, v := range res {
		payload[k] = v
	}
	writeJSONOut(stdout, payload)
	return 0
}
