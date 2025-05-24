#!/bin/bash
# Test that built script works with --help

# Create a temporary output file
output_file=$(mktemp)
trap "rm -f $output_file" EXIT

# Set TVMUX_SCRIPT_DIR to find tvmux.sh
export TVMUX_SCRIPT_DIR="."

# Build the script
build_self "$output_file" >/dev/null 2>&1

# Run with --help
output=$("$output_file" --help 2>&1)
exit_code=$?

# Should succeed and show help
[[ $exit_code -eq 0 ]] && [[ "$output" =~ "Commands:" ]]
