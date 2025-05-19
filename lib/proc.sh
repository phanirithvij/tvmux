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
        local children=$(pgrep -P "$pid" 2>/dev/null)
        for child in $children; do
            get_descendants "$child"
        done
    }
    
    # Get all PIDs in the tree
    local pids=$(get_descendants "$pid")
    
    # Send SIGTERM to all
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
        kill -KILL $remaining 2>/dev/null || true
    fi
}
