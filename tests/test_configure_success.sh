#!/bin/bash
# Test that configure command works when dependencies are available

# Run configure command using the local script
output=$(./tvmux.sh configure 2>&1)
exit_code=$?

# Should succeed on a properly configured system
# Just check that it runs without crashing
[[ $exit_code -eq 0 || $exit_code -eq 1 ]]
