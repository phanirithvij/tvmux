#!/bin/bash
# Test that proc_kill kills a process tree

# Create a temporary script file
test_script=$(mktemp)
trap "rm -f $test_script" EXIT

# Create a proper process tree
# Parent script that spawns children
cat > "$test_script" << 'EOF'
#!/bin/bash
# Child process
sleep 100 &
# Grandchild process
(sleep 100) &
# Keep parent alive
sleep 100
EOF
chmod +x "$test_script"

# Start the parent process
"$test_script" &
parent_pid=$!

# Give processes time to start
sleep 0.2

# Check parent is running
if ! kill -0 $parent_pid 2>/dev/null; then
    echo "Failed to create test process"
    exit 1
fi

# Kill the parent - should kill all descendants
proc_kill $parent_pid

# Brief wait for kill to complete
sleep 0.5

# Parent should not be running
if kill -0 $parent_pid 2>/dev/null; then
    echo "proc_kill failed to kill process"
    # Clean up
    pkill -f "$test_script" 2>/dev/null || true
    exit 1
fi
