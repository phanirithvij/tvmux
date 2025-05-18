#!/bin/bash

SESSION_RAW=$(tmux display -p '#{session_created}')
SESSION_ID=$(tmux display -p '#{session_id}')
PANE_PID=$$

# Format session start as human-readable and hierarchical
SESSION_DIR=$(date -d "@$SESSION_RAW" +%Y%m/%Y%m%d_%H%M%S)
DIR="$HOME/Videos/asciinema/tmux/$SESSION_DIR"
META="$DIR/meta"
mkdir -p "$META"

FIFO="$DIR/$PANE_PID.cast.fifo"
OUT="$DIR/$PANE_PID.cast.zst"

record_metadata() {
  echo "$SESSION_ID" > "$META/session_id"
  echo "$PANE_PID" > "$META/pane.$PANE_PID"
}

record_metadata
mkfifo "$FIFO"
zstd --fast -T0 < "$FIFO" > "$OUT" &

# Spawn session monitor in background subshell
(
  pid_file="$META/geometry.pid"
  log_file="$META/geometry.log"

  # exit early if already running
  if [[ -f "$pid_file" ]] && kill -0 $(cat "$pid_file" 2>/dev/null) 2>/dev/null; then
    exit 0
  fi

  echo $$ > "$pid_file"

  clean_fifo() {
    [[ -p "$1" ]] && ! lsof "$1" &>/dev/null && rm -f "$1"
  }

  cleanup_geometry_monitor() {
    rm -f "$pid_file"
    for fifo in "$DIR"/*.cast.fifo; do
      clean_fifo "$fifo"
    done
  }

  trap cleanup_geometry_monitor EXIT

  current=""
  while tmux has-session -t "$SESSION_ID" 2>/dev/null; do
    next=$(tmux list-panes -a -F '#{pane_id} #{session_name}:#{window_index}.#{pane_index} #{pane_width}x#{pane_height}@#{pane_left},#{pane_top}' | xargs echo || true)
    if [[ -n "$next" && "$current" != "$next" ]]; then
      echo "$(date +%s) $next" >> "$log_file"
      current="$next"
    fi
    sleep 2
  done
) &
disown

exec asciinema rec -q -y "$FIFO"
