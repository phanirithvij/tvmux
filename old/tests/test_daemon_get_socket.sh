#!/bin/bash
# Test daemon_get_socket with valid socket and pid

tmpdir=$(mktemp -d)
trap "rm -rf '$tmpdir'" EXIT

# Create a mock socket
test_socket="$tmpdir/daemon.sock"
perl -e "$DAEMON_PERL_USE $DAEMON_PERL_CREATE_SOCKET" -e 'create_socket($ARGV[0])' "$test_socket"

# Set tmux environment variables
tmux set-environment TVMUX_DAEMON_PID $$
tmux set-environment TVMUX_DAEMON_SOCKET "$test_socket"

# Test getting socket
socket=$(daemon_get_socket)

# Cleanup tmux vars
tmux set-environment -u TVMUX_DAEMON_PID
tmux set-environment -u TVMUX_DAEMON_SOCKET

[[ "$socket" == "$test_socket" ]]
