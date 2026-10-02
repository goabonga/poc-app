// SPDX-License-Identifier: MIT
// Copyright (c) 2026 Chris <goabonga@pm.me>

// Command greeter prints a greeting for the name given as its first argument.
package main

import (
	"fmt"
	"os"

	"github.com/goabonga/poc-app/internal/greeting"
)

func main() {
	name := ""
	if len(os.Args) > 1 {
		name = os.Args[1]
	}
	fmt.Println(greeting.For(name))
}
