#!/bin/bash

#
# Process related functions
#

# Kill a process and all its descendants, gracefully then forcefully
proc_kill() {
    local pid="$1"

    # Get all descendants recursively
    get_descendants() {
        local pid=$1
        echo "$pid"
        local children
        children=$(pgrep -P "$pid" 2>/dev/null)
        for child in $children; do
            get_descendants "$child"
        done
    }

    # Get all PIDs in the tree
    local pids
    pids=$(get_descendants "$pid")

    # Send SIGTERM to all
    # shellcheck disable=SC2086
    kill -TERM $pids 2>/dev/null || true

    # Check if any are still alive after a brief pause
    sleep 0.1
    local remaining=""
    for pid in $pids; do
        kill -0 "$pid" 2>/dev/null && remaining="$remaining $pid"
    done

    # If any survived, wait a bit more then force kill
    if [[ -n "$remaining" ]]; then
        sleep 0.9
        # shellcheck disable=SC2086
        kill -KILL $remaining 2>/dev/null || true
    fi
}

# Add an exit handler to this pid
# Usage: shell_trap "command goes here"
proc_trap() {
    local name="_PROC_EXIT_$$"
    if ! declare -p "$name" &>/dev/null; then
        declare -g -a "$name"
        trap __proc_exit EXIT INT TERM HUP
    fi

    local -n stack="$name"
    [[ -n "$1" ]] && stack+=("$1")
}

# called internally when the shell exits
__proc_exit() {
    local name="_PROC_EXIT_$$"

    # Skip if not defined
    declare -p "$name" &>/dev/null || return

    # shellcheck disable=SC2178
    local -n stack="$name"
    for fn in "${stack[@]}"; do
        eval "$fn" || true
    done
}
