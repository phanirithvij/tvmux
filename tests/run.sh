#!/bin/bash
# Test runner for tvmux

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Test tracking
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Arrays for failed tests
declare -a FAILED_TESTS
declare -a FAILED_OUTPUTS

# Get directories
TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$TEST_DIR")"

# Run a single test file
run_test() {
    local test_file="$1"
    local test_name="${test_file##*/}"
    test_name="${test_name%.sh}"

    TESTS_RUN=$((TESTS_RUN + 1))
    printf "."

    # Run test in subshell, capturing output
    local output
    local exit_code

    output=$(
        cd "$PROJECT_DIR" 2>&1
        source lib/lib_init.sh || exit 1
        source "$test_file" 2>&1
    )
    exit_code=$?

    if [[ $exit_code -eq 0 ]]; then
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        TESTS_FAILED=$((TESTS_FAILED + 1))
        FAILED_TESTS+=("$test_name")
        FAILED_OUTPUTS+=("$output")
    fi
}

# Get test pattern from command line
TEST_PATTERN="${1:-test_*.sh}"

# Main
echo -e "${YELLOW}Running tvmux tests${NC} (pattern: $TEST_PATTERN)"
echo

# Find and run matching test files
for test_file in "$TEST_DIR"/$TEST_PATTERN; do
    [[ -f "$test_file" ]] || continue
    [[ "$test_file" == "$TEST_DIR/run.sh" ]] && continue

    run_test "$test_file"
done

echo  # New line after dots
echo

# Show results
if [[ $TESTS_FAILED -eq 0 ]]; then
    printf "${GREEN}All tests passed!${NC} (%d/%d)\n" "$TESTS_PASSED" "$TESTS_RUN"
else
    printf "${RED}%d tests failed${NC} (%d passed, %d total)\n" "$TESTS_FAILED" "$TESTS_PASSED" "$TESTS_RUN"
    echo

    # Show failed test details
    for i in "${!FAILED_TESTS[@]}"; do
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        printf "${RED}FAILED:${NC} %s\n" "${FAILED_TESTS[$i]}"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "${FAILED_OUTPUTS[$i]}"
        echo
    done
fi

# Summary table
echo -e "┌─────────────┬────────┐"
echo -e "│ Total       │ $(printf "%6d" "$TESTS_RUN") │"
echo -e "│ ${GREEN}Passed${NC}      │ $(printf "%6d" "$TESTS_PASSED") │"
if [[ $TESTS_FAILED -gt 0 ]]; then
    echo -e "│ ${RED}Failed${NC}      │ $(printf "%6d" "$TESTS_FAILED") │"
else
    echo -e "│ Failed      │ $(printf "%6d" "$TESTS_FAILED") │"
fi
echo -e "└─────────────┴────────┘"

# Exit with failure if any tests failed
[[ $TESTS_FAILED -gt 0 ]] && exit 1
exit 0
