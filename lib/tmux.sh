#!/bin/bash

#
# tmux interaction
#

#
# TODO: give these sane names.
# 
# example: get_current_session_id -> tmux_get_sid
#

# Function to get current tmux session ID
tmux_get_sid() {
    tmux display-message -p '#{session_id}'
}

#
# Not sure if this belongs here. keep it for now?
# We may need a state management lib file
#

# Compute the recording directory path from session data
tmux_get_session_dir() {
    local session_start=$(tmux display-message -p '#{session_created}')
    local session_name=$(tmux display-message -p '#{session_name}')
    
    local session_dir=$(date -d "@$session_start" +%Y-%m/%Y%m%d_%H%M%S_$session_name)
    echo "$BASE_DIR/$session_dir"
}

# Clears the hooks that we added.
# We need to do this on cleardown or we're in an unknown state.
tmux_unhook() {
    tmux set-hook -gu pane-focus-in
    tmux set-hook -gu window-pane-changed
}

# Set the hooks up.
tmux_hook() {
    tmux set-hook -g window-pane-changed "run-shell '$SCRIPT_PATH pane-change'"
    tmux set-hook -g pane-focus-in       "run-shell '$SCRIPT_PATH pane-change'"
}

# If you don't stop the pipe it'll keep piping forever
tmux_unpipe() {
    tmux pipe-pane -t "$1" || true
}

# Set the active pane for recording, stopping previous if needed
tmux_pane_activate() {
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
        [[ -n "$prev_pane" ]] && tmux_unpipe "$prev_pane"
    fi
    
    # Set new active pane (none pauses recording)
    if [[ -n "$pane_id" ]]; then
        # Output current pane state
        tmux_get_pane "$pane_id" >> "$fifo" 2>&1
        
        echo "$pane_id" > "$active_pane_file"
        # Start capturing output
        tmux pipe-pane -t "$pane_id" "cat >> '$fifo'"
    else
        rm -f "$active_pane_file"
    fi
}

# Writes the current pane state to stdout, including control codes
# that are required to things look the same
tmux_get_pane() {
    local pane_id="$1" width height

    # Get pane dimensions
    width=$(tmux display-message -p -t "$pane_id" '#{pane_width}')
    height=$(tmux display-message -p -t "$pane_id" '#{pane_height}')

    tvmux_set dump 1

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

    tvmux_set dump 0
}

