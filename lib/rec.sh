#!/bin/bash

#
# Recording functions
#

# gets the root asciinema PID from session directory
rec_get_pid() {
    local session_dir="$1"
    local pid_file="$session_dir/asciinema_pid"
    
    if [[ -f "$pid_file" ]]; then
        cat "$pid_file" 2>/dev/null || true
    fi
}

# Check if recording is active for session dir
rec_is_active() {
    local session_dir=${1:-$(tmux_get_session_dir)}
    
    # Check if directory exists
    [[ ! -d "$session_dir" ]] && return 1
    
    # Check if asciinema process is running
    local pid=$(rec_get_pid "$session_dir")
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

# If asciinema is terminated while writing a super long line, or is otherwise
# jammed up, or there's buffering issues, our recording will be missing a ']'
# on the final line. If that was the case, this will repair it.
rec_fix_cast() {
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
rec_stop() {
    local session_dir="$1"
    
    # Stop the active pane recording
    tmux_pane_activate "$session_dir" ""
    
    # Kill asciinema process
    local pid=$(rec_get_pid "$session_dir")
    
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
        proc_kill "$pid"
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
    rec_fix_cast "$session_dir/session.cast"
    
    # Clean up files
    rm -f "$session_dir/asciinema_pid"
   
    # Remove FIFO
    if [[ -n "$fifo" ]]; then
        rm -f "$fifo" 2>/dev/null || true
    fi
}

# Wait for asciinema to be ready
rec_wait_ready() {
    local session_dir="$1"
    local max_retries="${2:-30}"  # 3 seconds default
    local retry_delay="${3:-0.1}"
    
    local retries=0
    while ((retries < max_retries)); do
        log_debug "Checking recording (attempt $((retries + 1))/$max_retries)"
        if rec_is_active "$session_dir"; then
            log_debug "Recording is ready!"
            return 0
        fi
        sleep "$retry_delay"
        retries=$((retries + 1))
    done
    
    log_warn "Recording may not be ready after ${max_retries} retries"
    return 1
}

# Start the asciinema recording process
rec_launch() {
    local session_dir="$1"
    local session_id="$2"
    local fifo="$3"
    
    # Get terminal dimensions from active pane
    local width=$(tmux display-message -p '#{pane_width}')
    local height=$(tmux display-message -p '#{pane_height}')
    
    local asciinema_cmd="asciinema rec"
    if [[ -f "$session_dir/session.cast" ]]; then
        # Fix potentially truncated file before appending
        rec_fix_cast "$session_dir/session.cast"
        asciinema_cmd="$asciinema_cmd --append"
    fi
    
    # Start the background process
    (
        # Set up exit trap for cleanup
        shell_trap "rec_stop '$session_dir'; tmux_unhook"
        
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
        
        log_info "Recording ended: $session_dir"
    ) >/dev/null 2>&1 &
    
    # Wait for recording to actually be ready
    rec_wait_ready "$session_dir"
}
