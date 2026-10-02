// SPDX-License-Identifier: MIT
// Copyright (c) 2026 Chris <goabonga@pm.me>

// Package greeting renders the greeting message the hello binary prints.
package greeting

import "fmt"

// For renders a greeting addressed to name. An empty name greets the world.
func For(name string) string {
	if name == "" {
		name = "World"
	}
	return fmt.Sprintf("Hello, %s!", name)
}
