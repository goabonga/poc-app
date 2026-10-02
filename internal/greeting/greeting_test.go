// SPDX-License-Identifier: MIT
// Copyright (c) 2026 Chris <goabonga@pm.me>

package greeting

import "testing"

func TestFor(t *testing.T) {
	cases := map[string]string{
		"":      "Hello, World!",
		"Chris": "Hello, Chris!",
	}
	for name, want := range cases {
		if got := For(name); got != want {
			t.Errorf("For(%q) = %q, want %q", name, got, want)
		}
	}
}
