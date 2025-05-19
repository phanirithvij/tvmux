#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_PATH="$SCRIPT_DIR/$(basename "${BASH_SOURCE[0]}")"
source "$SCRIPT_DIR/lib/lib.sh"


#
# TODO: this is bullshit
#
# Get base directory from second parameter if provided with 'start' command
if [[ "$1" == "start" && -n "$2" ]]; then
    BASE_DIR="$2"
fi


# Entrypoint for starting recording
handle_start() {
    local session_id=$(tmux_get_sid)
    local session_name=$(tmux display-message -p '#{session_name}')
    local session_start=$(tmux display-message -p '#{session_created}')
    local session_dir=$(tmux_get_session_dir)

    # Check if recording is already active for this session
    if rec_is_active; then
        local existing_dir=$(tmux_get_session_dir)
        log_info "Recording already active for session $session_name at $existing_dir"
        exit 0
    fi

    # Create directory structure
    mkdir -p "$session_dir"

    # Create FIFO
    local fifo="$session_dir/tmux_stream.fifo"
    [[ ! -p "$fifo" ]] && mkfifo "$fifo"
    
    # Store session metadata - still needed if we need to look up old recordings
    # The session_id helps us map to this directory (since ID isn't in the dir name)
    echo "$session_id" > "$session_dir/session_id"
    # Store name for display purposes only
    echo "$session_name" > "$session_dir/session_name"
    
    # Start recording process (waits until ready)
    rec_launch "$session_dir" "$session_id" "$fifo"
    
    # Set up hooks for pane changes
    tmux_hook
    
    # Initial pane capture via handler
    "$SCRIPT_PATH" pane-change
    
    log_info "Recording started in $session_dir"
}

# Called by the entrypoint when there's a pane change
handle_pane_change() {
    local session_dir=$(tmux_get_session_dir)
    
    # Check if directory exists
    [[ ! -d "$session_dir" ]] && exit 1
    
    # Get current active pane
    local current_pane=$(tmux display-message -p '#{pane_id}')
    
    # Update active pane
    tmux_pane_activate "$session_dir" "$current_pane"
}


# Entrypoint for stopping the recording
handle_stop() {
    # Get the session directory
    local session_dir=$(tmux_get_session_dir)

    tmux_unhook
    
    # Check if directory exists and has recording files
    if [[ ! -d "$session_dir" ]] || [[ ! -f "$session_dir/asciinema_pid" ]]; then
        log_info "No active recording for this session"
        exit 0
    fi
    
    # Stop recording (even if processes are partially dead)
    rec_stop "$session_dir"
    
    log_info "Recording stopped: $session_dir"
}

# Dispatch commands
cmd_dispatch "$@"
