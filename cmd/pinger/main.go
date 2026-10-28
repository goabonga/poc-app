// SPDX-License-Identifier: MIT
// Copyright (c) 2026 Chris <goabonga@pm.me>

// Command pinger reports the TCP connect latency to the address given as its
// first argument (host:port).
package main

import (
	"fmt"
	"os"
	"time"

	"github.com/goabonga/poc-app/internal/netutil"
)

func main() {
	if len(os.Args) > 1 && (os.Args[1] == "--version" || os.Args[1] == "-v") {
		fmt.Println(Version)
		return
	}
	if len(os.Args) > 1 && (os.Args[1] == "--help" || os.Args[1] == "-h") {
		fmt.Println("usage: pinger host:port")
		return
	}
	if len(os.Args) < 2 {
		fmt.Fprintln(os.Stderr, "usage: pinger host:port")
		os.Exit(2)
	}
	d, err := netutil.Ping(os.Args[1], 5*time.Second)
	if err != nil {
		fmt.Fprintf(os.Stderr, "pinger: %v\n", err)
		os.Exit(1)
	}
	fmt.Printf("%s: %s\n", os.Args[1], d)
}
