#!/bin/bash
# Test that proc_trap runs handlers in correct order

# This test will fail until the variable name bug is fixed
# proc_trap uses _PROC_EXIT_$$ but __proc_exit uses _SHELL_EXIT_$$

# Output file to track execution order
output_file=$(mktemp)
trap "rm -f $output_file" EXIT

# Test in a subshell to avoid affecting parent
(
    # Register multiple traps
    proc_trap "echo 'first' >> $output_file"
    proc_trap "echo 'second' >> $output_file"
    proc_trap "echo 'third' >> $output_file"

    # Exit the subshell to trigger traps
    exit 0
)

# Check if anything was written
if [[ ! -s $output_file ]]; then
    echo "ERROR: proc_trap handlers not executed (variable name mismatch bug)"
    exit 1
fi

# Check order - should be in order registered (first, second, third)
result=$(cat $output_file)
expected=$'first\nsecond\nthird'

if [[ "$result" != "$expected" ]]; then
    echo "Trap execution order incorrect"
    echo "Expected: $expected"
    echo "Got: $result"
    exit 1
fi
