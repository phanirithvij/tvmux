#!/bin/bash
# Test bash version check

# Since BASH_VERSINFO is readonly, we can only test with current version
# which should pass if we're running bash 4+

CONFIGURE_MISSING=""
output=$(configure_check_bash_version 2>&1)
exit_code=$?

# Should pass on bash 4+
if ((BASH_VERSINFO[0] >= 4)); then
    [[ $exit_code -eq 0 ]] || { echo "Bash version check failed"; exit 1; }
else
    # If somehow running on bash 3, it should fail
    [[ $exit_code -eq 1 ]] && [[ "$CONFIGURE_MISSING" == *"bash4+"* ]] || { echo "Bash 3 check didn't fail properly"; exit 1; }
fi
