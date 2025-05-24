#!/bin/bash
# Test daemon_get_socket with stale pid

tmpdir=$(mktemp -d)
trap "rm -rf '$tmpdir'" EXIT

# Create a mock socket
test_socket="$tmpdir/daemon.sock"
perl -e "$DAEMON_PERL_USE $DAEMON_PERL_CREATE_SOCKET" -e 'create_socket($ARGV[0])' "$test_socket"

# Set tmux environment with dead PID
tmux set-environment TVMUX_DAEMON_PID 999999
tmux set-environment TVMUX_DAEMON_SOCKET "$test_socket"

# Test should clean up and return empty
socket=$(daemon_get_socket)

# Verify cleanup happened
pid_cleared=$(tmux show-environment TVMUX_DAEMON_PID 2>&1 | grep -c "unknown variable")
socket_cleared=$(tmux show-environment TVMUX_DAEMON_SOCKET 2>&1 | grep -c "unknown variable")

[[ -z "$socket" && "$pid_cleared" -eq 1 && "$socket_cleared" -eq 1 && ! -e "$test_socket" ]]
