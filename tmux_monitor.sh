#!/bin/bash
set -e

# Base directory for recordings
BASE_DIR="$HOME/Videos/asciinema/tmux"

# Function to get the script's own path
get_script_path() {
    echo "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
}
SCRIPT_PATH=$(get_script_path)

# Handle different execution modes
if [[ "$1" == "init" ]]; then
    # Initialize recording for a new session
    
    # Get tmux session info
    SESSION_ID=$(tmux display-message -p '#{session_id}')
    SESSION_NAME=$(tmux display-message -p '#{session_name}')
    SESSION_START=$(tmux display-message -p '#{session_created}')
    
    # Create directory structure
    SESSION_DIR=$(date -d "@$SESSION_START" +%Y%m/%Y%m%d_%H%M%S_$SESSION_NAME)
    FULL_DIR="$BASE_DIR/$SESSION_DIR"
    mkdir -p "$FULL_DIR"
    
    # Create FIFO
    FIFO="$FULL_DIR/tmux_stream.fifo"
    mkfifo "$FIFO"
    
    # Save session info
    echo "$SESSION_ID" > "$FULL_DIR/session_id"
    echo "$SESSION_NAME" > "$FULL_DIR/session_name"
    echo "$FIFO" > "$FULL_DIR/fifo_path"
    
    # Start asciinema recording in background
    (
        asciinema rec "$FULL_DIR/session.cast" -c "stdbuf -o0 tail -F $FIFO" &
        asciinema_pid=$!
        echo "$asciinema_pid" > "$FULL_DIR/asciinema_pid"
        
        # Monitor tmux session existence and asciinema process
        while tmux has-session -t "$SESSION_ID" 2>/dev/null && kill -0 $asciinema_pid 2>/dev/null; do
            sleep 1
        done
        
        # Kill asciinema if still running
        if kill -0 $asciinema_pid 2>/dev/null; then
            kill $asciinema_pid
        fi
        rm -f "$FIFO"
        echo "Recording ended: $FULL_DIR"
    ) &
    
    # Set up hooks for pane changes
    tmux set-hook -g pane-focus-in "run-shell '$SCRIPT_PATH pane-change'"
    tmux set-hook -g window-pane-changed "run-shell '$SCRIPT_PATH pane-change'"
    
    # Initial pane capture
    "$SCRIPT_PATH" pane-change
    
    echo "Recording started in $FULL_DIR"
    exit 0

elif [[ "$1" == "pane-change" ]]; then
    # Handle pane change event
    
    # Find the session info
    for session_dir in $(find "$BASE_DIR" -type d -name "*" -mtime -1); do
        if [[ -f "$session_dir/session_id" ]]; then
            stored_session_id=$(cat "$session_dir/session_id" 2>/dev/null || continue)
            current_session_id=$(tmux display-message -p '#{session_id}')
            
            if [[ "$stored_session_id" == "$current_session_id" ]]; then
                FIFO=$(cat "$session_dir/fifo_path" 2>/dev/null || continue)
                CAST_FILE="$session_dir/session.cast"
                ACTIVE_PANE_FILE="$session_dir/active_pane"
                FOUND_SESSION=true
                break
            fi
        fi
    done
    
    # If we didn't find the session info, exit
    if [[ -z "$FIFO" || -z "$FOUND_SESSION" ]]; then
        exit 1
    fi
    
    # Get current active pane
    CURRENT_PANE=$(tmux display-message -p '#{pane_id}')
    
    # Check if this is a new pane
    if [[ -f "$ACTIVE_PANE_FILE" ]]; then
        PREV_PANE=$(cat "$ACTIVE_PANE_FILE")
        if [[ "$PREV_PANE" == "$CURRENT_PANE" ]]; then
            # Same pane, no change needed
            exit 0
        fi
        
        # Stop capture on previous pane
        tmux pipe-pane -t "$PREV_PANE"
    fi
    
    # Update active pane file
    echo "$CURRENT_PANE" > "$ACTIVE_PANE_FILE"
    
    # Append pane change event to cast file
    TIMESTAMP=$(date +%s.%N)
    echo "[$TIMESTAMP, \"o\", \"\\n\\033[1;30m-- PANE SWITCH: $CURRENT_PANE --\\033[0m\\n\"]" >> "$CAST_FILE"
    
    # Get pane dimensions
    WIDTH=$(tmux display-message -p -t "$CURRENT_PANE" '#{pane_width}')
    HEIGHT=$(tmux display-message -p -t "$CURRENT_PANE" '#{pane_height}')
    
    # First send a sync marker to help with buffering issues
    echo -e "\n\033[1;30m-- SYNC MARKER --\033[0m\n" > "$FIFO" || true
    sync
    
    # Clear screen and set terminal size
    echo -e "\033[2J\033[H\033[8;${HEIGHT};${WIDTH}t" > "$FIFO" || true
    sync
    
    # Output pane identifier
    echo -e "\033[1;30m-- PANE: $CURRENT_PANE (${WIDTH}x${HEIGHT}) --\033[0m" > "$FIFO" || true
    sync
    
    # Dump current pane content with escape sequences preserved
    tmux capture-pane -e -p -t "$CURRENT_PANE" > "$FIFO" || true
    sync
    
    # Get cursor position (adding 1 to convert from 0-based to 1-based)
    CURSOR_Y=$(tmux display-message -p -t "$CURRENT_PANE" '#{cursor_y}')
    CURSOR_X=$(tmux display-message -p -t "$CURRENT_PANE" '#{cursor_x}')
    CURSOR_Y=$((CURSOR_Y + 1))
    CURSOR_X=$((CURSOR_X + 1))
    
    # Position cursor with explicit sequence
    echo -e "\033[${CURSOR_Y};${CURSOR_X}H" > "$FIFO" || true
    sync
    
    # Start capturing output with unbuffered cat (with timeout to prevent blocking)
    tmux pipe-pane -t "$CURRENT_PANE" "stdbuf -o0 timeout --preserve-status 3600 cat > $FIFO"
    
    exit 0

elif [[ "$1" == "clear-hooks" ]]; then
    # Clear tmux hooks without stopping recording
    tmux set-hook -gu pane-focus-in
    tmux set-hook -gu window-pane-changed
    echo "Hooks cleared"
    exit 0

elif [[ "$1" == "stop" ]]; then
    # Stop recording for a session
    SESSION_ID=$(tmux display-message -p '#{session_id}')
    
    # Clear the hooks first
    tmux set-hook -gu pane-focus-in
    tmux set-hook -gu window-pane-changed
    
    for session_dir in $(find "$BASE_DIR" -type d -name "*" -mtime -1); do
        if [[ -f "$session_dir/session_id" ]]; then
            stored_session_id=$(cat "$session_dir/session_id" 2>/dev/null || continue)
            
            if [[ "$stored_session_id" == "$SESSION_ID" ]]; then
                # Stop any active pipe
                if [[ -f "$session_dir/active_pane" ]]; then
                    ACTIVE_PANE=$(cat "$session_dir/active_pane" 2>/dev/null || true)
                    [[ -n "$ACTIVE_PANE" ]] && tmux pipe-pane -t "$ACTIVE_PANE"
                fi
                
                # Kill asciinema
                if [[ -f "$session_dir/asciinema_pid" ]]; then
                    ASCIINEMA_PID=$(cat "$session_dir/asciinema_pid" 2>/dev/null || true)
                    if [[ -n "$ASCIINEMA_PID" ]] && kill -0 $ASCIINEMA_PID 2>/dev/null; then
                        kill $ASCIINEMA_PID
                    fi
                fi
                
                # Remove FIFO
                if [[ -f "$session_dir/fifo_path" ]]; then
                    FIFO=$(cat "$session_dir/fifo_path" 2>/dev/null || true)
                    [[ -n "$FIFO" ]] && rm -f "$FIFO"
                fi
                
                echo "Recording stopped: $session_dir"
                exit 0
            fi
        fi
    done
    
    echo "No active recording found for this session"
    exit 1

else
    # Display usage
    echo "Usage:"
    echo "  $0 init        - Start recording the current tmux session"
    echo "  $0 stop        - Stop recording the current tmux session"
    echo "  $0 clear-hooks - Just clear the tmux hooks without stopping recording"
    echo "  $0 pane-change - Internal command for handling pane changes"
    exit 1
fi