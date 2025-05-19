#!/bin/bash
# Test that configure succeeds when all dependencies are available

# Test name
TEST_NAME="configure succeeds with all dependencies"

# Run configure with normal PATH and capture exit code
"$OLDPWD/configure" >/dev/null 2>&1
EXIT_CODE=$?

# Check if it succeeded as expected
if [ "$EXIT_CODE" -eq 0 ]; then
    echo "PASS: $TEST_NAME"
    exit 0
else
    echo "FAIL: $TEST_NAME (expected exit code 0, got $EXIT_CODE)"
    exit 1
fi