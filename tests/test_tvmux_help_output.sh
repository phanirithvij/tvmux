#!/bin/bash
# Test that tvmux help command works

output=$(bash tvmux.sh --help 2>&1)
[[ "$output" =~ "Commands:" ]]
