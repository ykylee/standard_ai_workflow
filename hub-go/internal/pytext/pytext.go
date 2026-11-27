// Package pytext mirrors Python str whitespace handling so both hubs read the same input the same way.
//
// Python str.isspace() and Go unicode.IsSpace differ on exactly U+001C–001F (Python treats the
// information separators as whitespace). Every hub check that the Python hub writes as x.strip()
// uses Strip / IsBlank here instead of strings.TrimSpace (TASK-2026-11-27-claude-plex-004).
package pytext

import (
	"strings"
	"unicode"
)

// IsSpace reports whether r is whitespace for Python str.isspace().
func IsSpace(r rune) bool {
	return unicode.IsSpace(r) || r >= 0x1c && r <= 0x1f
}

// Strip is Python str.strip() with no arguments.
func Strip(s string) string { return strings.TrimFunc(s, IsSpace) }

// RStrip is Python str.rstrip() with no arguments.
func RStrip(s string) string { return strings.TrimRightFunc(s, IsSpace) }

// IsBlank reports whether Python `not s.strip()` holds.
func IsBlank(s string) bool { return Strip(s) == "" }
