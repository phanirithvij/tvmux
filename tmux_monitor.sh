#!/bin/bash
set -e

# Script configuration
THIS_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
SCRIPT_PATH="$THIS_DIR/$(basename "${BASH_SOURCE[0]}")"

# Get base directory from second parameter if provided with 'start' command
if [[ "$1" == "start" && -n "$2" ]]; then
    BASE_DIR="$2"
else
    BASE_DIR="$THIS_DIR/.cache"
fi

log_msg() {
    echo "$@" 1>&2
}

# Kill a process and all its descendants, gracefully then forcefully
kill_tree() {
    local root_pid="$1"
    
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
    local pids=$(get_descendants "$root_pid")
    
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

# Function to get current tmux session ID
get_current_session_id() {
    tmux display-message -p '#{session_id}'
}

# Compute the recording directory path from session data
get_session_dir() {
    local session_start=$(tmux display-message -p '#{session_created}')
    local session_name=$(tmux display-message -p '#{session_name}')
    
    local session_dir=$(date -d "@$session_start" +%Y-%m/%Y%m%d_%H%M%S_$session_name)
    echo "$BASE_DIR/$session_dir"
}

# For compatibility - will be removed once all callers are updated
find_session_dir() {
    get_session_dir
}

# gets the root asciinema PID from session directory
get_asciinema_pid() {
    local session_dir="$1"
    local pid_file="$session_dir/asciinema_pid"
    
    if [[ -f "$pid_file" ]]; then
        cat "$pid_file" 2>/dev/null || true
    fi
}

# Check if recording is active for session dir
is_recording() {
    local session_dir=${1:-$(get_session_dir)}
    
    # Check if directory exists
    [[ ! -d "$session_dir" ]] && return 1
    
    # Check if asciinema process is running
    local pid=$(get_asciinema_pid "$session_dir")
    if [[ -z "$pid" ]] || ! kill -0 "$pid" 2>/dev/null; then
        return 1
    fi
    
    # Check if someone is reading from the FIFO
    local fifo="$session_dir/tmux_stream.fifo"
    [[ ! -p "$fifo" ]] && return 1
    
    # Check if tail process is running (since fuser might not detect FIFO readers)
    if pgrep -f "tail -F $fifo" >/dev/null; then
        return 0
    else
        return 1
    fi
}

# Clears the hooks that we added.
# We need to do this on cleardown or we're in an unknown state.
clear_hooks() {
    tmux set-hook -gu pane-focus-in
    tmux set-hook -gu window-pane-changed
}

# Set the hooks up.
# A nice place to keep them, specially if we need to add more in future
setup_hooks() {
    tmux set-hook -g window-pane-changed "run-shell '$SCRIPT_PATH pane-change'"
    tmux set-hook -g pane-focus-in       "run-shell '$SCRIPT_PATH pane-change'"
}

# If you don't stop the pipe it'll keep piping forever
stop_pipe() {
    tmux pipe-pane -t "$1" || true
}

# Set the active pane for recording, stopping previous if needed
set_active_pane() {
    local session_dir="$1"
    local pane_id="$2"
    local active_pane_file="$session_dir/active_pane"
    local fifo="$session_dir/tmux_stream.fifo"
    
    # Check if this is the same pane
    if [[ -f "$active_pane_file" ]]; then
        local prev_pane=$(cat "$active_pane_file")
        if [[ "$prev_pane" == "$pane_id" ]]; then
            # Same pane, no change needed
            return 0
        fi
        # Stop previous pane
        [[ -n "$prev_pane" ]] && stop_pipe "$prev_pane"
    fi
    
    # Set new active pane (none pauses recording)
    if [[ -n "$pane_id" ]]; then
        # Output current pane state
        output_pane "$pane_id" >> "$fifo" 2>&1
        
        echo "$pane_id" > "$active_pane_file"
        # Start capturing output
        tmux pipe-pane -t "$pane_id" "cat >> '$fifo'"
    else
        rm -f "$active_pane_file"
    fi
}

# If asciinema is terminated while writing a super long line, or is otherwise
# jammed up, or there's buffering issues, our recording will be missing a ']'
# on the final line. If that was the case, this will repair it.
fix_asciinema_file() {
    local cast_file="$1"
    
    # No changes needed?
    [[ ! -f "$cast_file" ]] && return 0
    if tail -n1 "$cast_file" | grep -q '\]$'; then
        return 0
    fi
    
    # Repair the file
    local temp_file="${cast_file}.tmp"
    head -n -1 "$cast_file" > "$temp_file"
    mv "$temp_file" "$cast_file"
}

# Stop recording and clean up all resources
stop_recording() {
    local session_dir="$1"
    
    # Stop the active pane recording
    set_active_pane "$session_dir" ""
    
    # Kill asciinema process
    local pid=$(get_asciinema_pid "$session_dir")
    
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
        kill_tree "$pid"
    fi
    
    # Kill any lingering processes for this session's FIFO
    local fifo="$session_dir/tmux_stream.fifo"
    if [[ -p "$fifo" ]]; then
        # Kill any tail processes reading from this FIFO
        pkill -f "tail -F $fifo" || true
        # Kill any processes using the FIFO
        fuser -k "$fifo" 2>/dev/null || true
    fi

    # Fix potentially truncated asciinema file
    fix_asciinema_file "$session_dir/session.cast"
    
    # Clean up files
    rm -f "$session_dir/asciinema_pid"
   
    # Remove FIFO
    if [[ -n "$fifo" ]]; then
        rm -f "$fifo" 2>/dev/null || true
    fi
}

# Writes the current pane state to stdout, including control codes
# that are required to things look the same
output_pane() {
    local pane_id="$1" width height
    
    # Get pane dimensions
    width=$(tmux display-message -p -t "$pane_id" '#{pane_width}')
    height=$(tmux display-message -p -t "$pane_id" '#{pane_height}')
    
    # Reset terminal state, clear screen and set terminal size
    # (attributes, scroll region, clear screen, home cursor, set size)
    printf "\033[0m\033[r\033[2J\033[H\033[8;${height};${width}t"
    
    # Dump current pane content
    # * Replace "\n" with "clear to end of line\n" to preserve bg colour
    # * Remove the final newline so it doesn't scroll the window
    tmux capture-pane -e -p -S 0 -E $((height - 1)) -t "$pane_id" | \
        sed 's/$/\x1b[K/' | \
        head -c -1
    
    # Copy cursor position
    local x y visible
    read  x y visible <<< $(tmux display-message -p -t "$pane_id" '#{cursor_x} #{cursor_y} #{cursor_flag}')
    printf "\033[%d;%dH" "$((y + 1))" "$((x + 1))"
    
    # Get cursor visibility state
    if [[ "$visible" == "0" ]]; then
        printf "\033[?25l"  # Hide cursor
    else
        printf "\033[?25h"  # Show cursor
    fi
}

# Wait for asciinema to be ready
wait_for_recording_ready() {
    local session_dir="$1"
    local max_retries="${2:-30}"  # 3 seconds default
    local retry_delay="${3:-0.1}"
    
    local retries=0
    while ((retries < max_retries)); do
        log_msg "DEBUG: Checking recording (attempt $((retries + 1))/$max_retries)"
        if is_recording "$session_dir"; then
            log_msg "DEBUG: Recording is ready!"
            return 0
        fi
        sleep "$retry_delay"
        retries=$((retries + 1))
    done
    
    log_msg "Warning: Recording may not be ready after ${max_retries} retries"
    return 1
}

# Start the asciinema recording process
start_recording_process() {
    local session_dir="$1"
    local session_id="$2"
    local fifo="$3"
    
    # Get terminal dimensions from active pane
    local width=$(tmux display-message -p '#{pane_width}')
    local height=$(tmux display-message -p '#{pane_height}')
    
    local asciinema_cmd="asciinema rec"
    if [[ -f "$session_dir/session.cast" ]]; then
        # Fix potentially truncated file before appending
        fix_asciinema_file "$session_dir/session.cast"
        asciinema_cmd="$asciinema_cmd --append"
    fi
    
    # Start the background process
    (
        # Set up exit trap for cleanup
        trap "stop_recording '$session_dir'; clear_hooks" EXIT
        
        # The script wrapper prevents asciinema from knowing it's connected to
        # a real terminal, if we don't do this it'll echo everything back to
        # our terminal. We need to do stty inside script so the correct .cast
        # header is created, or the web player and asciinema.org won't like it.
        script -qfc "stty rows $height cols $width 2>/dev/null; $asciinema_cmd \"$session_dir/session.cast\" -c \"stdbuf -o0 tail -F $fifo 2>&1\"" /dev/null &
        local asciinema_pid=$!
        echo "$asciinema_pid" > "$session_dir/asciinema_pid"

        # Monitor tmux session existence and asciinema process
        while tmux has-session -t "$session_id" 2>/dev/null && kill -0 "$asciinema_pid" 2>/dev/null; do
            sleep 1
        done
        
        log_msg "Recording ended: $session_dir"
    ) >/dev/null 2>&1 &
    
    # Wait for recording to actually be ready
    wait_for_recording_ready "$session_dir"
}

# Entrypoint for starting recording
handle_start_recording() {
    local session_id=$(get_current_session_id)
    local session_name=$(tmux display-message -p '#{session_name}')
    local session_start=$(tmux display-message -p '#{session_created}')
    local session_dir=$(get_session_dir)

    # Check if recording is already active for this session
    if is_recording; then
        local existing_dir=$(get_session_dir)
        log_msg "Recording already active for session $session_name at $existing_dir"
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
    start_recording_process "$session_dir" "$session_id" "$fifo"
    
    # Set up hooks for pane changes
    setup_hooks
    
    # Initial pane capture via handler
    "$SCRIPT_PATH" pane-change
    
    log_msg "Recording started in $session_dir"
}

# Called by the entrypoint when there's a pane change
handle_pane_change() {
    local session_dir=$(get_session_dir)
    
    # Check if directory exists
    [[ ! -d "$session_dir" ]] && exit 1
    
    # Get current active pane
    local current_pane=$(tmux display-message -p '#{pane_id}')
    
    # Update active pane
    set_active_pane "$session_dir" "$current_pane"
}

# Entrypoint for stopping the recording
handle_stop_recording() {
    # Get the session directory
    local session_dir=$(get_session_dir)

    clear_hooks
    
    # Check if directory exists and has recording files
    if [[ ! -d "$session_dir" ]] || [[ ! -f "$session_dir/asciinema_pid" ]]; then
        log_msg "No active recording for this session"
        exit 0
    fi
    
    # Stop recording (even if processes are partially dead)
    stop_recording "$session_dir"
    
    log_msg "Recording stopped: $session_dir"
}

# Entrypoint dispatch logic
case "$1" in
    start)
        handle_start_recording
        ;;
    pane-change)
        handle_pane_change
        ;;
    clear-hooks)
        clear_hooks
        log_msg "Hooks cleared"
        ;;
    stop)
        handle_stop_recording
        ;;
    *)
        echo "Usage:"
        echo "  $0 start [path] - Start recording the current tmux session (optional: specify recording path)"
        echo "  $0 stop         - Stop recording the current tmux session"
        echo "  $0 clear-hooks  - Just clear the tmux hooks without stopping recording"
        echo "  $0 pane-change  - Internal command for handling pane changes"
        echo
        echo "Default recording path: $THIS_DIR/.cache"
        exit 1
        ;;
esac
