#!/bin/bash
# Simple command dispatcher

declare -gA COMMANDS
declare -gA HELP_TEXT

args_add_arg() {
    local cmd="$1"
    local func="$2"
    local help="$3"

    COMMANDS["$cmd"]="$func"
    HELP_TEXT["$cmd"]="$help"
}

args_set_program() {
    PROGRAM_NAME="$1"
}

args_main() {
    local cmd="$1"
    shift

    if [[ -z "$cmd" || "$cmd" == "--help" || "$cmd" == "-h" ]]; then
        echo "Usage: $PROGRAM_NAME <command> [args]"
        echo "Commands:"
        for c in "${!COMMANDS[@]}"; do
            printf "  %-12s %s\n" "$c" "${HELP_TEXT[$c]}"
        done
        return 0
    fi

    if [[ -z "${COMMANDS[$cmd]}" ]]; then
        echo "Unknown command: $cmd" >&2
        return 1
    fi

    "${COMMANDS[$cmd]}" "$@"
}
