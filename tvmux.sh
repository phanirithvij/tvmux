#!/bin/bash
# tvmux - Terminal session recorder for tmux

TVMUX_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$TVMUX_SCRIPT_DIR/lib/lib_init.sh" || exit 1

# Set up argument parser
args_set_program "tvmux"

# Define MVP commands
args_add_arg "init" "cmd_init" "Start the tvmux daemon"
args_add_arg "kill" "cmd_kill" "Stop the daemon and all recordings"
args_add_arg "status" "cmd_status" "Show daemon and recording status"
args_add_arg "record" "cmd_record" "Record current tmux window"
args_add_arg "build" "cmd_build" "Build standalone script"
args_add_arg "configure" "cmd_configure" "Check dependencies"

# Main entry point
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    args_main "$@"
fi
