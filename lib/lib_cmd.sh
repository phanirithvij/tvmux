#!/bin/bash
# Command implementations for tvmux

cmd_init() {
    local socket
    socket=$(daemon_get_socket 2>/dev/null)

    if [[ -n "$socket" ]]; then
        log_info "Daemon already running at $socket"
        return 0
    fi

    log_info "Starting tvmux daemon..."
    daemon_start

    socket=$(daemon_get_socket)
    log_info "Daemon started at $socket"
}

cmd_kill() {
    local socket
    socket=$(daemon_get_socket 2>/dev/null)

    if [[ -z "$socket" ]]; then
        log_info "No daemon running"
        return 0
    fi

    log_info "Stopping tvmux daemon..."

    # Get PID and kill it
    local pid
    pid=$(tmux show-environment TVMUX_DAEMON_PID 2>/dev/null | cut -d= -f2)

    if [[ -n "$pid" ]]; then
        proc_kill "$pid"
        log_info "Daemon stopped"
    fi

    # Clean up tmux environment
    tmux set-environment -u TVMUX_DAEMON_PID 2>/dev/null || true
    tmux set-environment -u TVMUX_DAEMON_SOCKET 2>/dev/null || true
}

cmd_record() {
    # Ensure daemon is running
    local socket
    socket=$(daemon_get_socket 2>/dev/null)

    if [[ -z "$socket" ]]; then
        log_info "Starting daemon..."
        daemon_start
    fi

    # Get current tmux context
    if [[ -z "$TMUX" ]]; then
        log_error "Not in a tmux session"
        return 1
    fi

    # Get current identifiers using tmux commands
    local session window pane
    session=$(tmux display-message -p '#S')
    window=$(tmux display-message -p '#I')
    pane=$(tmux display-message -p '#P')

    log_info "Recording session:$session window:$window pane:$pane"

    # Send record command to daemon
    local response
    response=$(daemon_send "record $session:$window.$pane")

    echo "$response"
}

cmd_status() {
    local socket
    socket=$(daemon_get_socket 2>/dev/null)

    if [[ -z "$socket" ]]; then
        echo "Daemon: not running"
        return 0
    fi

    echo "Daemon: running at $socket"

    # Get daemon status
    local daemon_status
    daemon_status=$(daemon_send "status" 2>/dev/null || echo "unreachable")
    echo "Status: $daemon_status"

    # Show active recordings
    local recordings
    recordings=$(tmux show-environment -g | grep "^TVMUX_RECORDING_" | cut -d= -f1,2)

    if [[ -n "$recordings" ]]; then
        echo ""
        echo "Active recordings:"
        while IFS= read -r recording; do
            local target="${recording#TVMUX_RECORDING_}"
            target="${target%=*}"
            local status="${recording#*=}"
            echo "  $target: $status"
        done <<< "$recordings"
    else
        echo ""
        echo "No active recordings"
    fi
}

cmd_build() {
    build_self "$@"
}
