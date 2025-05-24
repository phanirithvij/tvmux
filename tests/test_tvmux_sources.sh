#!/bin/bash
# Test that tvmux.sh sources without errors

error_output=$(bash -c 'source ./tvmux.sh' 2>&1)
[[ -z "$error_output" ]]
