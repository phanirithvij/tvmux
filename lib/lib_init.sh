#!/bin/bash
# tvmux library initialization

((BASH_VERSINFO[0] < 4)) && { echo "tvmux requires bash 4+" >&2; exit 1; }

# Setup
TVMUX_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source "$TVMUX_LIB_DIR/lib_args.sh"
source "$TVMUX_LIB_DIR/lib_cmd.sh"
source "$TVMUX_LIB_DIR/lib_configure.sh"
source "$TVMUX_LIB_DIR/lib_proc.sh"
source "$TVMUX_LIB_DIR/lib_build.sh"
