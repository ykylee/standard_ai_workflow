package judge

// SplitLines mirrors Python str.splitlines() for callers outside this package.
func SplitLines(s string) []string { return splitPyLines(s) }

// Strip mirrors Python str.strip().
func Strip(s string) string { return pyStrip(s) }
