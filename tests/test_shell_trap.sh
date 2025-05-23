#!/bin/bash
# Test the shell_trap exit handler

# Get the directory of this script
TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_DIR="$(cd "$TEST_DIR/.." && pwd)"

# Source the library
source "$SCRIPT_DIR/lib/shell.sh"

# Test output file - use current directory (which is tmpdir from test runner)
TEST_OUTPUT="./shell_trap_test_output"
rm -f "$TEST_OUTPUT"

echo "Testing shell_trap..."

# Test 1: Basic trap functionality
echo -n "Test 1 - Basic trap: "
(
    shell_trap "echo 'trap1' >> '$TEST_OUTPUT'"
    exit 0
)
if grep -q "trap1" "$TEST_OUTPUT"; then
    echo "PASS"
else
    echo "FAIL - trap didn't execute"
    exit 1
fi

# Test 2: Multiple traps (stacking)
echo -n "Test 2 - Multiple traps: "
rm -f "$TEST_OUTPUT"
(
    shell_trap "echo 'trap1' >> '$TEST_OUTPUT'"
    shell_trap "echo 'trap2' >> '$TEST_OUTPUT'"
    shell_trap "echo 'trap3' >> '$TEST_OUTPUT'"
    exit 0
)
if [[ $(wc -l < "$TEST_OUTPUT") -eq 3 ]]; then
    echo "PASS"
else
    echo "FAIL - expected 3 lines, got $(wc -l < "$TEST_OUTPUT")"
    exit 1
fi

# Test 3: Trap on interrupt (Ctrl+C)
echo -n "Test 3 - Trap on INT signal: "
rm -f "$TEST_OUTPUT"
(
    shell_trap "echo 'interrupted' >> '$TEST_OUTPUT'"
    kill -INT $$
)
if grep -q "interrupted" "$TEST_OUTPUT"; then
    echo "PASS"
else
    echo "FAIL - trap didn't execute on INT"
    exit 1
fi

# Test 4: Trap on TERM signal
echo -n "Test 4 - Trap on TERM signal: "
rm -f "$TEST_OUTPUT"
bash -c "
    source '$SCRIPT_DIR/lib/shell.sh'
    shell_trap \"echo 'terminated' >> '$TEST_OUTPUT'\"
    kill -TERM \$\$
"
if grep -q "terminated" "$TEST_OUTPUT"; then
    echo "PASS"
else
    echo "FAIL - trap didn't execute on TERM"
    exit 1
fi

# Test 5: Trap execution order (LIFO)
echo -n "Test 5 - Execution order: "
rm -f "$TEST_OUTPUT"
(
    shell_trap "echo '1' >> '$TEST_OUTPUT'"
    shell_trap "echo '2' >> '$TEST_OUTPUT'"
    shell_trap "echo '3' >> '$TEST_OUTPUT'"
    exit 0
)
# Check if they execute in order (1, 2, 3)
if [[ $(cat "$TEST_OUTPUT" | tr '\n' ' ') == "1 2 3 " ]]; then
    echo "PASS"
else
    echo "FAIL - wrong order: $(cat "$TEST_OUTPUT" | tr '\n' ',')"
    exit 1
fi

# Cleanup
rm -f "$TEST_OUTPUT"

echo "All tests passed!"