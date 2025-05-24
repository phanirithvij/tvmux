#!/bin/bash
# Test that configure fails when required tool is missing

# Mock command -v to control what tools are "found"
command() {
    if [[ "$1" == "-v" && "$2" == "this-command-does-not-exist" ]]; then
        return 1
    fi
    # Call real command for other cases
    \command "$@"
}

# Capture the CONFIGURE_MISSING variable
CONFIGURE_MISSING=""

# Test with a non-existent required tool
configure_check_tool "this-command-does-not-exist" "true" 2>/dev/null
exit_code=$?

# Should fail and add to CONFIGURE_MISSING
[[ $exit_code -eq 1 ]] && [[ "$CONFIGURE_MISSING" == *"this-command-does-not-exist"* ]]
