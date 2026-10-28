// SPDX-License-Identifier: MIT
// Copyright (c) 2026 Chris <goabonga@pm.me>

// Command hello prints a greeting for the name given as its first argument.
package main

import (
	"fmt"
	"os"

	"github.com/fatih/color"

	"github.com/goabonga/poc-app/internal/greeting"
)

func main() {
	if len(os.Args) > 1 && (os.Args[1] == "--version" || os.Args[1] == "-v") {
		fmt.Println(Version)
		return
	}
	if len(os.Args) > 1 && (os.Args[1] == "--help" || os.Args[1] == "-h") {
		fmt.Println("usage: hello [name]")
		return
	}
	name := ""
	if len(os.Args) > 1 {
		name = os.Args[1]
	}
	color.Green(greeting.For(name))
}
