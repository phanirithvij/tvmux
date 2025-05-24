#!/bin/bash
# Test that configure succeeds when required tool exists

# Mock command -v to control what tools are "found"
command() {
    if [[ "$1" == "-v" && "$2" == "sh" ]]; then
        echo "/bin/sh"
        return 0
    fi
    # Call real command for other cases
    \command "$@"
}

# Test with a tool that definitely exists (sh)
configure_check_tool "sh" "true"
exit_code=$?

[[ $exit_code -eq 0 ]]
