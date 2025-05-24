#!/bin/bash
# Test protocol_set function

# Test 1: Check the escape sequence format
output=$(protocol_set "test_key" "test_value")
expected_output=$'\033_tvmux:set:test_key:test_value\033\\'
[[ "$output" == "$expected_output" ]] || {
    echo "Expected: $expected_output"
    echo "Got: $output"
    exit 1
}

# Test 2: Check that the global variable is set (run without subshell)
protocol_set "another_key" "another_value" >/dev/null

# Check that the global variable was set
[[ "$TVMUX_MODE_ANOTHER_KEY" == "another_value" ]] || {
    echo "Variable TVMUX_MODE_ANOTHER_KEY not set correctly"
    echo "Expected: another_value"
    echo "Got: $TVMUX_MODE_ANOTHER_KEY"
    exit 1
}
