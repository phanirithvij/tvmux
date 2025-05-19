#!/bin/bash

# Set up base directory if not already set
BASE_DIR="${BASE_DIR:-$SCRIPT_DIR/.cache}"

source $SCRIPT_DIR/lib/cmd.sh
source $SCRIPT_DIR/lib/log.sh
source $SCRIPT_DIR/lib/proc.sh
source $SCRIPT_DIR/lib/tmux.sh
source $SCRIPT_DIR/lib/rec.sh
