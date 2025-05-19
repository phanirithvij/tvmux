#!/bin/bash

#
# Logging functions
#

LOG_LEVEL=${LOG_LEVEL:-30}  # Default to WARNING

log_msg() {
    local level="$1"; shift
    if (( level >= LOG_LEVEL )); then
        echo "[$(date '+%H:%M:%S')] $*" >&2
    fi
}

log_debug() { log_msg 10 "[DEBUG] $*"; }
log_info()  { log_msg 20 "[INFO]  $*"; }
log_warn()  { log_msg 30 "[WARN]  $*"; }
log_error() { log_msg 40 "[ERROR] $*"; }
