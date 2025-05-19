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

# TODO: this is needed because asciinema spawns multiple processes.
# is there a cleaner way to kill a process group?
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

# Get the recording dir for the current tmux session
# TODO: rename this to "get_session_dir" and get rid of the search.
#       Use the function to 
find_session_dir() {
    local session_id="$1"
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

# gets the root asciinema PID from session directory
get_asciinema_pid() {
    local session_dir="$1"
    local pid_file="$session_dir/asciinema_pid"
    
    if [[ -f "$pid_file" ]]; then
        cat "$pid_file" 2>/dev/null || true
    fi
}

# Check if recording is active for session
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

# If asciinema is terminated while writing a super long line, or is otherwise
# jammed up, or there's buffering issues, our recording will be missing a ']'
# on the final line. If that was the case, this will repair it.
#
# TODO: this really shouldn't be run if asciinema is recording; we should bail
# out if it is.
fix_asciinema_file() {
    local cast_file="$1"
    
    # No changes needed?
    [[ ! -f "$cast_file" ]]                     && return 0
    [[ tail -n1 "$cast_file" | grep -q '\]$' ]] && return 0
    
    # Repair the file
    local temp_file="${cast_file}.tmp"
    head -n -1 "$cast_file" > "$temp_file"
    mv "$temp_file" "$cast_file"
}

# Kill the asciinema process and clean up pid files
cleanup_recording() {
    local session_dir="$1"
    
    # Kill asciinema process
    local pid=$(get_asciinema_pid "$session_dir")

    # todo: we should really move this into the kill_tree function
    #
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
        kill_tree "$pid"
        # Give processes time to clean up gracefully before force killing
        # This helps avoid file corruption and ensures FIFOs are properly closed
        # TODO: this sleep is run every time and 
        sleep 1
        # Force kill if process is still alive
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

# Run asciinema in a subshell and wreap it
start_asciinema_background() {
    local full_dir="$1"
    local session_id="$2"
    local fifo="$3"
    
    (
        # Set up exit trap for cleanup
        trap "cleanup_recording '$full_dir'; clear_hooks" EXIT
        
        # Get terminal dimensions from active pane
        local width=$(tmux display-message -p '#{pane_width}')
        local height=$(tmux display-message -p '#{pane_height}')
        
        local asciinema_cmd="asciinema rec"
        if [[ -f "$full_dir/session.cast" ]]; then
            # Fix potentially truncated file before appending
            fix_asciinema_file "$full_dir/session.cast"
            asciinema_cmd="$asciinema_cmd --append"
        fi
        
        # The script wrapper prevents asciinema from knowing it's connected to
        # a real terminal, if we don't do this it'll echo everything back to
        # our terminal. We need to do stty inside script so the correct .cast
        # header is created, or the web player and asciinema.org won't like it.
        script -qfc "stty rows $height cols $width 2>/dev/null; $asciinema_cmd \"$full_dir/session.cast\" -c \"stdbuf -o0 tail -F $fifo 2>&1\"" /dev/null &
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
    
    # JUSTIFICATION: session_id file needed to map tmux session to recording directory
    # This allows us to find the right recording when handling pane switches
    # TODO: the session id is in the name of the dir, so this is crazy and the justification
    # does not hold. Also why do we need to store the name?! I don't like it
    echo "$session_id"   > "$full_dir/session_id"
    echo "$session_name" > "$full_dir/session_name"
    
    # JUSTIFICATION: lock file ensures recording is fully initialized before pane-change events
    # Without this, early pane switches could try to access incomplete recording setup
    # TODO: I'm not sure about this. we have "is_recording_active" so this seems redundant
    local lock_file="$full_dir/recording.lock"
    echo $$ > "$lock_file"
    
    # Start asciinema recording in background
    start_asciinema_background "$full_dir" "$session_id" "$fifo"
    
    # Set up hooks for pane changes
    setup_hooks
    
    # Prime the fifo. If we don't do this then for some reason we don't get the
    # first pane's output at all. 
    # TODO: investigate and understand this because it's really wierd and seems
    # like a dirty hack.
    echo "" > "$fifo"
    
    # Initial pane capture
    "$SCRIPT_PATH" pane-change
    
    log_msg "Recording started in $full_dir"
}

# Called by the entrypoint when there's a pane change
handle_pane_change() {
    local session_id=$(get_current_session_id)
    # Find the session directory
    local session_dir

    # TODO: call the function to create the name rather than find it
    if ! session_dir=$(find_session_dir "$session_id"); then
        exit 1
    fi
    
    # Check lock file to ensure init is complete
    # TODO: is_recording_active ought to handle this right?
    if [[ ! -f "$session_dir/recording.lock" ]]; then
        exit 0
    fi
    
    # Get FIFO path
    local fifo="$session_dir/tmux_stream.fifo"
    local active_pane_file="$session_dir/active_pane"
    
    # Get current active pane
    local current_pane=$(tmux display-message -p '#{pane_id}')
    
    # JUSTIFICATION: active_pane file tracks which pane is currently being recorded
    # This prevents duplicate captures and ensures we stop pipe-pane on the old pane
    # before starting on the new one, avoiding FIFO conflicts
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

    # Start capturing output
    tmux pipe-pane -t "$current_pane" "cat > '$fifo'"
}

# Entrypoint for stopping the recording
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
    # TODO: this is ugly ass shit
    local session_dir
    session_dir=$(find_session_dir "$session_id")
    
    # Stop any active pipe
    # TODO: Pretty sure that cleanup_recording should handle this instead of us
    if [[ -f "$session_dir/active_pane" ]]; then
        local active_pane=$(cat "$session_dir/active_pane" 2>/dev/null || true)
        stop_pipe "$active_pane"
    fi
    
    # Clean up recording
    cleanup_recording "$session_dir"
    
    log_msg "Recording stopped: $session_dir"
}

# Entrypoint dispatch logic
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
