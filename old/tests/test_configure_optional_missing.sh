#!/bin/bash
# Test that configure succeeds when optional tool is missing

# Mock command -v to control what tools are "found"
command() {
    if [[ "$1" == "-v" && "$2" == "optional-tool-not-exist" ]]; then
        return 1
    fi
    # Call real command for other cases
    \command "$@"
}

# Capture the variables
CONFIGURE_MISSING=""
CONFIGURE_OPTIONAL_MISSING=""

# Test with a non-existent optional tool
configure_check_tool "optional-tool-not-exist" "false" 2>/dev/null
exit_code=$?

# Should succeed but add to CONFIGURE_OPTIONAL_MISSING
[[ $exit_code -eq 1 ]] &&
[[ -z "$CONFIGURE_MISSING" ]] &&
[[ "$CONFIGURE_OPTIONAL_MISSING" == *"optional-tool-not-exist"* ]]
