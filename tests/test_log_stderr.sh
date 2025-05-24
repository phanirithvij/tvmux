#!/bin/bash
# Test that log output goes to stderr

# Check that stdout is empty and stderr has content
stdout=$(log_error "test" 2>/dev/null)
stderr=$(log_error "test" 2>&1 1>/dev/null)

[[ -z "$stdout" ]] || { echo "Log output found on stdout"; exit 1; }
[[ -n "$stderr" ]] || { echo "Log output not found on stderr"; exit 1; }
