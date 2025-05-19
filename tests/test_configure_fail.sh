#!/bin/bash
# Test that configure properly fails when dependencies are missing

# Test name
TEST_NAME="configure fails with missing dependencies"

# Create a minimal PATH that excludes asciinema
export PATH=/bin:/usr/bin

# Run configure and capture exit code
"$OLDPWD/configure" 2>&1
EXIT_CODE=$?

# Check if it failed as expected
if [ "$EXIT_CODE" -eq 1 ]; then
    echo "PASS: $TEST_NAME"
    exit 0
else
    echo "FAIL: $TEST_NAME (expected exit code 1, got $EXIT_CODE)"
    exit 1
fi