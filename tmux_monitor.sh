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

kill_tree() {
    local pid="$1"
    local sig="${2:--TERM}"
    local children=$(pgrep -P "$pid")
    for child in $children; do
        kill_tree "$child" "$sig"
    done
    kill -"$sig" "$pid" 2>/dev/null || true
}

# Function to get current tmux session ID
get_current_session_id() {
    tmux display-message -p '#{session_id}'
}

# Function to find session directory for given session ID
find_session_dir() {
    local session_id="$1"
   
    # 
    # todo:
    # this will become grossly inefficient over time
    # there will be many many recordings as I collect data, and looping over them in bash is a bad idea
    # also mtime -1? I haven't rebooted my AI box in 3 months.
    #
    for session_dir in $(find "$BASE_DIR" -type d -name "*" -mtime -1 2>/dev/null); do
        if [[ -f "$session_dir/session_id" ]]; then
            local stored_id=$(cat "$session_dir/session_id" 2>/dev/null || continue)
            if [[ "$stored_id" == "$session_id" ]]; then
                echo "$session_dir"
                return 0
            fi
        fi
    done
    return 1
}

# Function to get asciinema PID from session directory
get_asciinema_pid() {
    local session_dir="$1"
    local pid_file="$session_dir/asciinema_pid"
    
    if [[ -f "$pid_file" ]]; then
        cat "$pid_file" 2>/dev/null || true
    fi
}

# Function to check if recording is active for session
is_recording_active() {
    local session_id="$1"
    local session_dir
    
    if ! session_dir=$(find_session_dir "$session_id"); then
        return 1
    fi
    
    # Check if asciinema process is running
    local pid=$(get_asciinema_pid "$session_dir")
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
        return 0
    fi
    
    return 1
}

# Function to clear all hooks
clear_hooks() {
    tmux set-hook -gu pane-focus-in
    tmux set-hook -gu window-pane-changed
}

# Function to set up hooks for recording
setup_hooks() {
    tmux set-hook -g window-pane-changed "run-shell '$SCRIPT_PATH pane-change'"
    tmux set-hook -g pane-focus-in       "run-shell '$SCRIPT_PATH pane-change'"
}

# Function to stop pipe on a pane
stop_pipe() {
    tmux pipe-pane -t "$1" || true
}

# Function to fix truncated asciinema files
fix_asciinema_file() {
    local cast_file="$1"
    
    if [[ ! -f "$cast_file" ]]; then
        return 0
    fi
    
    # Check if the last line ends with ]
    if tail -n1 "$cast_file" | grep -q '\]$'; then
        return 0
    fi
    
    # Remove the last line if it doesn't end with ]
    local temp_file="${cast_file}.tmp"
    head -n -1 "$cast_file" > "$temp_file"
    mv "$temp_file" "$cast_file"
}

# Function to kill asciinema process and clean up files
cleanup_recording() {
    local session_dir="$1"
    
    # Kill asciinema process
    local pid=$(get_asciinema_pid "$session_dir")

    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
        kill_tree "$pid"
        sleep 1
        kill -0 "$pid" >/dev/null 2>&1 && kill_tree "$pid" -KILL
    fi

    # Fix potentially truncated asciinema file
    fix_asciinema_file "$session_dir/session.cast"
    
    # Clean up files
    rm -f "$session_dir/asciinema_pid"
    rm -f "$session_dir/recording.lock"
    rm -f "$session_dir/active_pane"
   
    fifo="$session_dir/tmux_stream.fifo"
    # Remove FIFO
    if [[ -n "$fifo" ]]; then
        # Kill any processes using the FIFO to prevent broken pipe errors
        fuser -k "$fifo" 2>/dev/null || true
        rm -f "$fifo" 2>/dev/null    || true
    fi
}

# Function to output pane content
output_pane() {
    local pane_id="$1"
    
    # Get pane dimensions
    local width=$(tmux display-message -p -t "$pane_id" '#{pane_width}')
    local height=$(tmux display-message -p -t "$pane_id" '#{pane_height}')
    
    # Clear screen and set terminal size  
    printf "\033[2J\033[H\033[8;${height};${width}t"
    
    # Dump current pane content with escape sequences preserved
    # Add clear-to-end-of-line after each line
    # Use printf to avoid adding a trailing newline
    tmux capture-pane -e -p -S 0 -E $((height - 1)) -t "$pane_id" | sed 's/$/\x1b[K/' | head -c -1
    
    # Get cursor position (adding 1 to convert from 0-based to 1-based)
    local cursor_y=$(tmux display-message -p -t "$pane_id" '#{cursor_y}')
    local cursor_x=$(tmux display-message -p -t "$pane_id" '#{cursor_x}')
    cursor_y=$((cursor_y + 1))
    cursor_x=$((cursor_x + 1))
    
    # Position cursor with explicit sequence
    printf "\033[%d;%dH" "$cursor_y" "$cursor_x"
}

# Function to start asciinema background process
start_asciinema_background() {
    local full_dir="$1"
    local session_id="$2"
    local fifo="$3"
    
    (
        # Set up exit trap for cleanup
        trap "cleanup_recording '$full_dir'; clear_hooks" EXIT
        
        local asciinema_cmd="asciinema rec"
        if [[ -f "$full_dir/session.cast" ]]; then
            # Fix potentially truncated file before appending
            fix_asciinema_file "$full_dir/session.cast"
            asciinema_cmd="$asciinema_cmd --append"
        fi
        script -qfc "$asciinema_cmd \"$full_dir/session.cast\" -c \"stdbuf -o0 tail -F $fifo 2>&1\"" /dev/null &
        local asciinema_pid=$!
        echo "$asciinema_pid" > "$full_dir/asciinema_pid"
        
        # Monitor tmux session existence and asciinema process
        while tmux has-session -t "$session_id" 2>/dev/null && kill -0 "$asciinema_pid" 2>/dev/null; do
            sleep 1
        done
        
        log_msg "Recording ended: $full_dir"
    ) >/dev/null 2>&1 &
}

# Start recording for the current session
start_recording() {
    local session_id=$(get_current_session_id)
    local session_name=$(tmux display-message -p '#{session_name}')
    
    # Check if recording is already active for this session
    if is_recording_active "$session_id"; then
        local existing_dir=$(find_session_dir "$session_id")
        log_msg "Recording already active for session $session_name at $existing_dir"
        exit 0
    fi
    
    # Get session start time
    local session_start=$(tmux display-message -p '#{session_created}')
    
    # Create directory structure
    local session_dir=$(date -d "@$session_start" +%Y-%m/%Y%m%d_%H%M%S_$session_name)
    local full_dir="$BASE_DIR/$session_dir"
    mkdir -p "$full_dir"
    
    # Create FIFO
    local fifo="$full_dir/tmux_stream.fifo"
    [[ ! -f "$fifo" ]] && mkfifo "$fifo"
    
    # Save session info
    echo "$session_id" > "$full_dir/session_id"
    echo "$session_name" > "$full_dir/session_name"
    
    # Create lock file for this session
    local lock_file="$full_dir/recording.lock"
    echo $$ > "$lock_file"
    
    # Start asciinema recording in background
    start_asciinema_background "$full_dir" "$session_id" "$fifo"
    
    # Set up hooks for pane changes
    setup_hooks
    
    # Send a newline to "prime" the FIFO for tail -F
    echo "" > "$fifo"
    
    # Initial pane capture
    "$SCRIPT_PATH" pane-change
    
    log_msg "Recording started in $full_dir"
}

# Handle pane change event
handle_pane_change() {
    local session_id=$(get_current_session_id)
    # Find the session directory
    local session_dir
    if ! session_dir=$(find_session_dir "$session_id"); then
        exit 1
    fi
    
    # Check lock file to ensure init is complete
    if [[ ! -f "$session_dir/recording.lock" ]]; then
        exit 0
    fi
    
    # Get FIFO path
    local fifo="$session_dir/tmux_stream.fifo"
    local active_pane_file="$session_dir/active_pane"
    
    # Get current active pane
    local current_pane=$(tmux display-message -p '#{pane_id}')
    
    # Check if this is a new pane
    if [[ -f "$active_pane_file" ]]; then
        local prev_pane=$(cat "$active_pane_file")
        if [[ "$prev_pane" == "$current_pane" ]]; then
            # Same pane, no change needed
            exit 0
        fi
        
        # Stop capture on previous pane
        stop_pipe "$prev_pane"
    fi
    
    # Update active pane file
    echo "$current_pane" > "$active_pane_file"
    
    # Send pane info to FIFO
    output_pane "$current_pane" > "$fifo" 2>&1
    output_pane "$current_pane" > "$session_dir/$(date +%s%N)"

    # Start capturing output
    tmux pipe-pane -t "$current_pane" "cat > '$fifo'"
}

# Stop recording for the current session
stop_recording() {
    local session_id=$(get_current_session_id)
    
    # Clear hooks
    clear_hooks
    
    # Check if recording is active
    if ! is_recording_active "$session_id"; then
        log_msg "No active recording for this session"
        exit 0
    fi
    
    # Find the session directory
    local session_dir
    session_dir=$(find_session_dir "$session_id")
    
    # Stop any active pipe
    if [[ -f "$session_dir/active_pane" ]]; then
        local active_pane=$(cat "$session_dir/active_pane" 2>/dev/null || true)
        stop_pipe "$active_pane"
    fi
    
    # Clean up recording
    cleanup_recording "$session_dir"
    
    log_msg "Recording stopped: $session_dir"
}

# Main script logic
case "$1" in
    start)
        start_recording
        ;;
    pane-change)
        handle_pane_change
        ;;
    clear-hooks)
        clear_hooks
        log_msg "Hooks cleared"
        ;;
    stop)
        stop_recording
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
