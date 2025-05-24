#!/bin/bash
# Command implementations for tvmux

cmd_start() {
    echo "Starting recording..."
    echo "  Window: ${TVMUX_CMD_START_WINDOW}"
    echo "  Output: ${TVMUX_CMD_START_OUTPUT}"
    # TODO: Implement actual recording
}

cmd_stop() {
    echo "Stopping recording..."
    echo "  Window: ${TVMUX_CMD_STOP_WINDOW}"
    # TODO: Implement actual stop
}

cmd_status() {
    echo "No active recordings"
    # TODO: Show actual status
}

cmd_build() {
    build_self "$TVMUX_CMD_BUILD_OUTPUT"
}
