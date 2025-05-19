#!/bin/bash
# Run all test_*.sh scripts in individual temporary directories

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RESET='\033[0m'

# Counters
PASSED=0
FAILED=0
TOTAL=0

# Get the test directory
TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$TEST_DIR")"

echo "Running tests from $TEST_DIR"
echo

# Find all test scripts
for test_script in "$TEST_DIR"/test_*.sh; do
    # Skip if no test scripts found
    [ -f "$test_script" ] || continue
    
    TOTAL=$((TOTAL + 1))
    test_name=$(basename "$test_script")
    
    # Create temporary directory for this test
    tmpdir=$(mktemp -d)
    
    echo "Running $test_name..."
    
    # Run test in temporary directory
    (
        cd "$tmpdir"
        # Make project directory available as OLDPWD for tests
        export OLDPWD="$PROJECT_DIR"
        bash "$test_script"
    )
    
    # Check exit code
    if [ $? -eq 0 ]; then
        printf "${GREEN}[PASS]${RESET} %s\n" "$test_name"
        PASSED=$((PASSED + 1))
    else
        printf "${RED}[FAIL]${RESET} %s\n" "$test_name"
        FAILED=$((FAILED + 1))
    fi
    
    # Clean up temporary directory
    rm -rf "$tmpdir"
    echo
done

# Summary
echo "=== Test Summary ==="
printf "Total:  %d\n" "$TOTAL"
printf "${GREEN}Passed: %d${RESET}\n" "$PASSED"
if [ "$FAILED" -gt 0 ]; then
    printf "${RED}Failed: %d${RESET}\n" "$FAILED"
else
    printf "Failed: %d\n" "$FAILED"
fi

# Exit with failure if any tests failed
if [ "$FAILED" -gt 0 ]; then
    exit 1
else
    exit 0
fi