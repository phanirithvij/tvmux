#!/bin/bash
# TTY extension protocol for tvmux using APC (Application Program Command)
# Format: ESC_tvmux:set:key:value ESC\

# Send a tvmux APC command and set the variable
protocol_set() {
    local key="$1"
    local value="$2"

    # Convert key to uppercase and create variable name
    local var_name="TVMUX_MODE_${key^^}"

    # Set the variable
    declare -g "$var_name=$value"

    # Send the APC sequence
    printf '\033_tvmux:set:%s:%s\033\\' "$key" "$value"
}
