package store

import (
	"crypto/rand"
	"encoding/hex"
	"fmt"
	"regexp"
	"strings"
)

const LocalPrefix = "local:"

var (
	CaseInsensitiveHosts = map[string]bool{
		"github.com":    true,
		"gitlab.com":    true,
		"bitbucket.org": true,
	}
	scpRe        = regexp.MustCompile(`^([^@/\s]+@)?([^:/\s]+):([^\s]+)$`)
	urlRe        = regexp.MustCompile(`^([a-zA-Z][a-zA-Z0-9+.-]*)://(.+)$`)
	driveRe      = regexp.MustCompile(`^[A-Za-z]:[\\/]`)
	portSuffixRe = regexp.MustCompile(`:\d*$`)
	multiSlashRe = regexp.MustCompile(`/+`)
)

func invalidRemote(url, why string) *HubError {
	return &HubError{
		Status:  400,
		Code:    "invalid_remote",
		Message: fmt.Sprintf("git 원격 주소로 읽을 수 없다 (%s): '%s'", why, url),
		Detail:  map[string]any{"remote_url": url},
	}
}

// NormalizeGitRemote converts a git remote URL or SCP spec into canonical host/path form.
func NormalizeGitRemote(remoteURL string) (string, error) {
	raw := strings.TrimSpace(remoteURL)
	if raw == "" {
		return "", invalidRemote(remoteURL, "비었다")
	}

	var host, p string
	if m := urlRe.FindStringSubmatch(raw); m != nil {
		scheme := strings.ToLower(m[1])
		if scheme == "file" {
			return "", invalidRemote(remoteURL, "로컬 경로는 원격이 아니다 — 원격을 먼저 만든다")
		}
		rest := m[2]
		authority, after, _ := strings.Cut(rest, "/")
		p = after
		if idx := strings.LastIndexByte(authority, '@'); idx >= 0 {
			authority = authority[idx+1:]
		}
		host = portSuffixRe.ReplaceAllString(authority, "")
	} else {
		if strings.HasPrefix(raw, "/") || strings.HasPrefix(raw, ".") || strings.HasPrefix(raw, "~") || driveRe.MatchString(raw) {
			return "", invalidRemote(remoteURL, "로컬 경로는 원격이 아니다 — 원격을 먼저 만든다")
		}
		s := scpRe.FindStringSubmatch(raw)
		if s == nil || strings.HasPrefix(s[3], "//") {
			return "", invalidRemote(remoteURL, "스킴도 scp 형식도 아니다")
		}
		host = s[2]
		p = s[3]
	}

	host = strings.ToLower(strings.TrimSpace(host))
	if host == "" {
		return "", invalidRemote(remoteURL, "호스트가 없다")
	}
	p = multiSlashRe.ReplaceAllString(strings.Trim(p, "/"), "/")
	p = strings.TrimSuffix(p, ".git")
	p = strings.Trim(p, "/")
	if p == "" {
		return "", invalidRemote(remoteURL, "경로가 없다")
	}
	if CaseInsensitiveHosts[host] {
		p = strings.ToLower(p)
	}
	return host + "/" + p, nil
}

// LocalKey returns a random key for local projects without a git remote.
func LocalKey() (string, error) {
	var b [8]byte
	if _, err := rand.Read(b[:]); err != nil {
		return "", err
	}
	return LocalPrefix + hex.EncodeToString(b[:]), nil
}
