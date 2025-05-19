#!/bin/bash

#
# Command dispatch  
#

# Command handlers - these will be properly renamed once reorganized
cmd_start() { handle_start "$@"; }
cmd_pane_change() { handle_pane_change "$@"; }
cmd_clear_hooks() { tmux_unhook; log_info "Hooks cleared"; }
cmd_stop() { handle_stop "$@"; }


#
# fuck me this is a monster!
# probably need to break it up into different functions in respective
# areas.
#

# Entrypoint for showing recording status
cmd_status() {
    local session_name=$(tmux display-message -p '#{session_name}')
    local session_dir=$(tmux_get_session_dir)
    local cast_file="$session_dir/session.cast"
    
    echo "Session: $session_name"
    echo "Directory: $session_dir"
    
    # Check recording status (less strict than is_recording)
    local recording_status="NOT RECORDING"
    if [[ -d "$session_dir" ]]; then
        local pid=$(rec_get_pid "$session_dir")
        if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
            recording_status="RECORDING (PID: $pid)"
        fi
    fi
    echo "Status: $recording_status"
    
    #
    # TODO: none of your fucking business.
    #

    # Check if cast file exists
    if [[ -f "$cast_file" ]]; then
        # Get file size in human readable format
        local size=$(du -h "$cast_file" | cut -f1)
        echo "Cast file size: $size"
        
        # Get duration from last timestamp
        local duration=$(tail -n1 "$cast_file" | cut -d',' -f1 | cut -d'[' -f2)
        if [[ -n "$duration" ]]; then
            # Convert to human readable format (HH:MM:SS)
            local hours=$((${duration%.*} / 3600))
            local minutes=$(((${duration%.*} % 3600) / 60))
            local seconds=$((${duration%.*} % 60))
            printf "Duration: %02d:%02d:%02d\n" "$hours" "$minutes" "$seconds"
        else
            echo "Duration: unknown"
        fi
    else
        echo "Cast file: not found"
    fi
    
    # Debug info if not recording
    if [[ "$recording_status" == "NOT RECORDING" ]] && [[ -d "$session_dir" ]]; then
        echo ""
        echo "Debug info:"
        echo "  PID file exists: $([[ -f "$session_dir/asciinema_pid" ]] && echo "yes" || echo "no")"
        echo "  FIFO exists: $([[ -p "$session_dir/tmux_stream.fifo" ]] && echo "yes" || echo "no")"
        echo "  Active pane file: $([[ -f "$session_dir/active_pane" ]] && echo "yes" || echo "no")"
    fi
}



# Get base directory from second parameter if provided with 'start' command
# Base directory will be set by lib.sh if not already set
BASE_DIR="${BASE_DIR:-$SCRIPT_DIR/.cache}"

cmd_dispatch() {
    # Entrypoint dispatch logic
    case "$1" in
        start)
            cmd_start
            ;;
        pane-change)
            cmd_pane_change
            ;;
        clear-hooks)
            cmd_clear_hooks
            ;;
        stop)
            cmd_stop
            ;;
        status)
            cmd_status
            ;;
        *)
            echo "Usage:"
            echo "  $0 start [path] - Start recording the current tmux session (optional: specify recording path)"
            echo "  $0 stop         - Stop recording the current tmux session"
            echo "  $0 status       - Show current recording status and information"
            echo "  $0 clear-hooks  - Just clear the tmux hooks without stopping recording"
            echo "  $0 pane-change  - Internal command for handling pane changes"
            echo
            echo "Default recording path: $SCRIPT_DIR/.cache"
            exit 1
            ;;
    esac
}
