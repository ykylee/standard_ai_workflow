package pytext

import "testing"

// The whitespace set must be exactly Python's str.isspace() — listed from CPython 3.14.
func TestIsSpaceMatchesPython(t *testing.T) {
	want := map[rune]bool{}
	for _, r := range []rune{0x9, 0xa, 0xb, 0xc, 0xd, 0x1c, 0x1d, 0x1e, 0x1f, 0x20, 0x85, 0xa0, 0x1680,
		0x2000, 0x2001, 0x2002, 0x2003, 0x2004, 0x2005, 0x2006, 0x2007, 0x2008, 0x2009, 0x200a,
		0x2028, 0x2029, 0x202f, 0x205f, 0x3000} {
		want[r] = true
	}
	for r := rune(0); r < 0x110000; r++ {
		if IsSpace(r) != want[r] {
			t.Fatalf("IsSpace(%#x) = %v, Python says %v", r, IsSpace(r), want[r])
		}
	}
	if !IsBlank("\x1c\x1d \t") || IsBlank("a") || Strip("\x1fab\x1e") != "ab" || RStrip("a\x1c") != "a" {
		t.Fatal("Strip / RStrip / IsBlank")
	}
}
