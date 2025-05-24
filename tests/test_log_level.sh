#!/bin/bash
# Test log level filtering

# Set log level to INFO (20)
LOG_LEVEL=20

# Debug (10) should not show
output=$(log_debug "debug message" 2>&1)
[[ -z "$output" ]] || { echo "Debug message shown when LOG_LEVEL=20"; exit 1; }

# Info (20) should show
output=$(log_info "info message" 2>&1)
[[ -n "$output" ]] || { echo "Info message not shown when LOG_LEVEL=20"; exit 1; }

# Warn (30) should show
output=$(log_warn "warn message" 2>&1)
[[ -n "$output" ]] || { echo "Warn message not shown when LOG_LEVEL=20"; exit 1; }

# Error (40) should show
output=$(log_error "error message" 2>&1)
[[ -n "$output" ]] || { echo "Error message not shown when LOG_LEVEL=20"; exit 1; }
