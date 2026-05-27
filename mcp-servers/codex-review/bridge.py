#!/usr/bin/env python3
"""Windows-side stdio↔TCP bridge for Codex MCP server running inside WSL.

Claude Code on Windows spawns this bridge via .mcp.json stdio transport.
The bridge forwards MCP protocol messages to the real server listening on
a TCP port inside WSL, solving the WSL stdin-forwarding issue.

Usage:
    python bridge.py [--port 9876] [--auto-start-wsl]

With --auto-start-wsl, the bridge starts the WSL-side TCP server on first
connection if it's not already running.
"""

import argparse
import json
import os
import socket
import subprocess
import sys
import time


SERVER_HOST = os.environ.get("CODEX_MCP_HOST", "127.0.0.1")
SERVER_PORT = int(os.environ.get("CODEX_MCP_PORT", "9876"))
WSL_DISTRO = os.environ.get("CODEX_WSL_DISTRO", "Ubuntu-20.04")
SERVER_SCRIPT = "/root/Projects/aris/Auto-research-in-sleep/aris-orangmood-edition/mcp-servers/codex-review/server.py"


def server_is_alive():
    """Check if the TCP MCP server is listening."""
    try:
        with socket.create_connection((SERVER_HOST, SERVER_PORT), timeout=2):
            return True
    except (ConnectionRefusedError, OSError):
        return False


def start_wsl_server():
    """Launch the MCP server inside WSL in TCP mode."""
    if server_is_alive():
        return True
    cmd = [
        "wsl", "-d", WSL_DISTRO, "--",
        "bash", "-c",
        f"nohup python3 {SERVER_SCRIPT} --tcp {SERVER_PORT} > /tmp/codex-mcp-tcp.log 2>&1 &"
    ]
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # Wait for server to start
    for _ in range(20):
        time.sleep(0.3)
        if server_is_alive():
            return True
    return False


def bridge():
    """Forward MCP protocol between stdin/stdout and TCP server."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(300)
    try:
        sock.connect((SERVER_HOST, SERVER_PORT))
    except (ConnectionRefusedError, OSError) as e:
        sys.stderr.write(f"Bridge: cannot connect to MCP server at {SERVER_HOST}:{SERVER_PORT}: {e}\n")
        sys.exit(1)

    # Set stdin/stdout to binary unbuffered for MCP Content-Length framing
    sys.stdin = os.fdopen(sys.stdin.fileno(), "rb", buffering=0)
    sys.stdout = os.fdopen(sys.stdout.fileno(), "wb", buffering=0)

    try:
        while True:
            # Read Content-Length header from stdin
            line = sys.stdin.readline()
            if not line:
                break
            text = line.decode("utf-8").rstrip("\r\n")
            if not text.lower().startswith("content-length:"):
                continue
            try:
                cl = int(text.split(":", 1)[1].strip())
            except ValueError:
                continue
            # Blank line
            while True:
                h = sys.stdin.readline()
                if not h or h in {b"\r\n", b"\n"}:
                    break
            body = sys.stdin.read(cl)
            # Forward to server
            header = f"Content-Length: {cl}\r\n\r\n".encode("utf-8")
            sock.sendall(header + body)
            # Read response from server
            resp_line = b""
            while not resp_line.endswith(b"\r\n\r\n"):
                ch = sock.recv(1)
                if not ch:
                    return
                resp_line += ch
            resp_text = resp_line.decode("utf-8")
            if not resp_text.lower().startswith("content-length:"):
                continue
            resp_cl = int(resp_text.split(":", 1)[1].strip())
            resp_body = b""
            while len(resp_body) < resp_cl:
                chunk = sock.recv(resp_cl - len(resp_body))
                if not chunk:
                    return
                resp_body += chunk
            # Write to stdout
            sys.stdout.write(resp_line + resp_body)
            sys.stdout.flush()
    except (BrokenPipeError, ConnectionResetError, OSError):
        pass
    finally:
        sock.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=SERVER_PORT)
    ap.add_argument("--auto-start-wsl", action="store_true")
    opts = ap.parse_args()

    SERVER_PORT = opts.port

    if opts.auto_start_wsl:
        if not start_wsl_server():
            sys.stderr.write("Bridge: WSL server did not start\n")
            sys.exit(1)

    bridge()
