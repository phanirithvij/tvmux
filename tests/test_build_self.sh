#!/bin/bash
# Test build_self function

# Create a temporary output file
output_file=$(mktemp)
trap "rm -f $output_file" EXIT

# Set TVMUX_SCRIPT_DIR to find tvmux.sh
export TVMUX_SCRIPT_DIR="."

# Build the script
build_self "$output_file"

# Check it exists and is executable
[[ -f "$output_file" ]] && [[ -x "$output_file" ]] || exit 1

# Check it runs with --help
"$output_file" --help >/dev/null 2>&1
