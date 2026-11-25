package tools

import (
	"math/rand"
	"strings"
	"testing"
)

// applyDiff rebuilds both sides from the diff, so a hidden or invented line cannot pass.
func applyDiff(old, diff string) (string, string) {
	a := diffLines(old)
	var start int
	lines := diffLines(diff)
	var from, to []string
	head := lines[2]
	for _, r := range head[4:] {
		if r < '0' || r > '9' {
			break
		}
		start = start*10 + int(r-'0')
	}
	if start > 0 {
		start--
	}
	for i := 3; i < len(lines); i++ {
		text := lines[i][1:]
		if i+1 < len(lines) && strings.HasPrefix(lines[i+1], "\\ ") {
			text = strings.TrimSuffix(text, "\n")
		}
		switch lines[i][0] {
		case ' ':
			from, to = append(from, text), append(to, text)
		case '-':
			from = append(from, text)
		case '+':
			to = append(to, text)
		}
	}
	before, after := a[:start], []string{}
	if start+len(from) <= len(a) {
		after = a[start+len(from):]
	}
	join := func(mid []string) string {
		return strings.Join(before, "") + strings.Join(mid, "") + strings.Join(after, "")
	}
	return join(from), join(to)
}

func TestUnifiedDiffHidesNothing(t *testing.T) {
	r := rand.New(rand.NewSource(7))
	text := func() string {
		words := []string{"a", "b", "", "c\r", "d ", "e\u2028f"}
		var out []string
		for range r.Intn(12) {
			out = append(out, words[r.Intn(len(words))])
		}
		body := strings.Join(out, "\n")
		if r.Intn(2) == 0 {
			body += "\n"
		}
		return body
	}
	for range 5000 {
		old, next := text(), text()
		diff := UnifiedDiff(old, next, "v1", "v2")
		if (diff == "") != (old == next) {
			t.Fatalf("%q -> %q: empty=%v", old, next, diff == "")
		}
		if diff == "" {
			continue
		}
		if gotOld, gotNext := applyDiff(old, diff); gotOld != old || gotNext != next {
			t.Fatalf("%q -> %q\n%s\n%q %q", old, next, diff, gotOld, gotNext)
		}
	}
}
