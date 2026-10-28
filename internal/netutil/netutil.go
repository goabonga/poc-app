// SPDX-License-Identifier: MIT
// Copyright (c) 2026 Chris <goabonga@pm.me>

// Package netutil measures TCP connect latency for the pinger binary.
package netutil

import (
	"net"
	"time"
)

// Ping opens a TCP connection to addr and returns how long the handshake
// took. It closes the connection before returning.
func Ping(addr string, timeout time.Duration) (time.Duration, error) {
	start := time.Now()
	conn, err := net.DialTimeout("tcp", addr, timeout)
	if err != nil {
		return 0, err
	}
	defer func() { _ = conn.Close() }()
	return time.Since(start), nil
}
