// SPDX-License-Identifier: MIT
// Copyright (c) 2026 Chris <goabonga@pm.me>

package netutil

import (
	"net"
	"testing"
	"time"
)

func TestPing(t *testing.T) {
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatalf("listen: %v", err)
	}
	defer ln.Close()
	go func() {
		for {
			conn, err := ln.Accept()
			if err != nil {
				return
			}
			conn.Close()
		}
	}()

	d, err := Ping(ln.Addr().String(), time.Second)
	if err != nil {
		t.Fatalf("Ping: %v", err)
	}
	if d <= 0 {
		t.Errorf("Ping duration = %v, want > 0", d)
	}
}

func TestPingUnreachable(t *testing.T) {
	if _, err := Ping("127.0.0.1:1", 100*time.Millisecond); err == nil {
		t.Error("Ping to an unreachable address: got nil error, want one")
	}
}
