#!/bin/bash
# tvmux - Terminal session recorder for tmux

TVMUX_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$TVMUX_SCRIPT_DIR/lib/lib_init.sh" || exit 1

# Set up argument parser
args_set_program "tvmux"

# Define commands
args_add_arg "start" "cmd_start" "Start recording a tmux window"
args_add_arg "stop" "cmd_stop" "Stop recording"
args_add_arg "status" "cmd_status" "Show recording status"
args_add_arg "configure" "cmd_configure" "Check dependencies"
args_add_arg "build" "build_self" "Build standalone script"

# Main entry point
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    args_main "$@"
fi
