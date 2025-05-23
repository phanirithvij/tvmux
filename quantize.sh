#!/bin/bash

# Dynamic asciinema quantizer - quantizes only when data rate is high
# Key innovation: Keeps asciinema processes alive to avoid Python startup overhead

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_PATH="$SCRIPT_DIR/$(basename "$0")"

# Source libraries
source "$SCRIPT_DIR/lib/lib.sh"

# Arguments
CAST_FILE="${1:-current.cast}"
FPS="${2:-30}"
OUTPUT_FILE="${3:-quantized.cast}"

# Calculate frame interval
FRAME_INTERVAL=$(awk "BEGIN {print 1/$FPS}")

# Process PIDs for cleanup
PLAYBACK_TAIL_PID=""
PLAYBACK_CAT_PID=""
RECORD_TAIL_PID=""
RECORD_CAT_PID=""

# FIFOs for playback pipeline
PLAYBACK_INPUT="playback_input.fifo"
PLAYBACK_CHAIN="playback_chain.fifo"
PLAYBACK_OUTPUT="playback_output.fifo"

# FIFOs for recording pipeline
RECORD_INPUT="record_input.fifo"
RECORD_CHAIN="record_chain.fifo"
RECORD_OUTPUT="record_output.fifo"

# Global variables
HEADER=""
PANE_ID=""
BATCH_NUM=0

cleanup() {
    # Kill all background processes
    local pids=($PLAYBACK_TAIL_PID $PLAYBACK_CAT_PID $RECORD_TAIL_PID $RECORD_CAT_PID)
    for pid in "${pids[@]}"; do
        [[ -n "$pid" ]] && kill $pid 2>/dev/null || true
    done
    
    # Remove all FIFOs
    rm -f "$PLAYBACK_INPUT" "$PLAYBACK_CHAIN" "$PLAYBACK_OUTPUT"
    rm -f "$RECORD_INPUT" "$RECORD_CHAIN" "$RECORD_OUTPUT"
}

setup_fifos() {
    # Create all FIFOs
    rm -f "$PLAYBACK_INPUT" "$PLAYBACK_CHAIN" "$PLAYBACK_OUTPUT"
    rm -f "$RECORD_INPUT" "$RECORD_CHAIN" "$RECORD_OUTPUT"
    
    mkfifo "$PLAYBACK_INPUT" "$PLAYBACK_CHAIN" "$PLAYBACK_OUTPUT"
    mkfifo "$RECORD_INPUT" "$RECORD_CHAIN" "$RECORD_OUTPUT"
}

start_playback_pipeline() {
    # Start the playback pipeline (keeps asciinema cat alive)
    stdbuf -o0 tail -n +1 -f "$PLAYBACK_INPUT" > "$PLAYBACK_CHAIN" &
    PLAYBACK_TAIL_PID=$!
    
    stdbuf -o0 asciinema cat "$PLAYBACK_CHAIN" > "$PLAYBACK_OUTPUT" &
    PLAYBACK_CAT_PID=$!
}

start_recording_pipeline() {
    # Start the recording pipeline (keeps asciinema rec alive)
    stdbuf -o0 tail -n +1 -f "$RECORD_INPUT" > "$RECORD_CHAIN" &
    RECORD_TAIL_PID=$!
    
    # Use asciinema rec with stdin mode
    stdbuf -o0 asciinema rec --quiet --stdin "$RECORD_OUTPUT" < "$RECORD_CHAIN" &
    RECORD_CAT_PID=$!
}

send_batch_to_playback() {
    local batch_num=$1
    local batch_data="$2"
    local batch_end=$3
    
    # Send header + batch data + end marker
    {
        echo "$HEADER"
        echo -e "$batch_data"
        echo "[${batch_end},\"o\",\"\\033[0m###PLAYBACK_BATCH_${batch_num}_END###\\n\"]"
    } >> "$PLAYBACK_INPUT"
}

capture_playback_output() {
    local batch_num=$1
    local output=""
    
    # Read until we see our batch marker
    while IFS= read -r line; do
        if [[ "$line" == *"###PLAYBACK_BATCH_${batch_num}_END###"* ]]; then
            break
        fi
        output="${output}${line}"$'\n'
    done < "$PLAYBACK_OUTPUT"
    
    echo -n "$output"
}

send_tmux_to_recorder() {
    local batch_num=$1
    
    # Capture and send tmux state
    {
        tmux_get_pane "$PANE_ID"
        echo -e "\\033[0m###RECORD_BATCH_${batch_num}_END###"
    } >> "$RECORD_INPUT"
}

capture_recorded_output() {
    local batch_num=$1
    local output=""
    local line_count=0
    local in_recording=0
    
    # Read recorded output
    while IFS= read -r line; do
        # Skip the header on first batch
        if [[ $batch_num -eq 1 ]] && [[ $in_recording -eq 0 ]]; then
            in_recording=1
            continue
        fi
        
        if [[ "$line" == *"###RECORD_BATCH_${batch_num}_END###"* ]]; then
            break
        fi
        
        output="${output}${line}"$'\n'
        ((line_count++))
    done < "$RECORD_OUTPUT"
    
    echo -n "$output"
}

create_quantized_frame() {
    local batch_start=$1
    local tmux_output=$2
    
    # Create a single asciinema frame with the tmux capture
    if [[ -n "$tmux_output" ]]; then
        echo "[${batch_start},\"o\",$(printf '%s' "$tmux_output" | jq -Rs .)]"
    fi
}

process_batch() {
    local batch_data="$1"
    local batch_start=$2
    local batch_end=$3
    
    [[ -z "$batch_data" ]] && return
    
    ((BATCH_NUM++))
    echo "Processing batch $BATCH_NUM (${batch_start}s - ${batch_end}s)" >&2
    
    # Step 1: Send to playback pipeline
    send_batch_to_playback "$BATCH_NUM" "$batch_data" "$batch_end"
    
    # Step 2: Capture and display output
    local playback_output
    playback_output=$(capture_playback_output "$BATCH_NUM")
    echo -n "$playback_output"
    
    # Step 3: Send tmux state to recorder
    send_tmux_to_recorder "$BATCH_NUM"
    
    # Step 4: Capture recorded output
    local recorded_output
    recorded_output=$(capture_recorded_output "$BATCH_NUM")
    
    # Step 5: Create quantized version
    local quantized_data
    quantized_data=$(create_quantized_frame "$batch_start" "$recorded_output")
    
    # Step 6: Compare and output
    local original_size=${#batch_data}
    local quantized_size=${#quantized_data}
    
    if [[ -n "$quantized_data" ]] && [[ $quantized_size -lt $original_size ]]; then
        echo "  → Using quantized (${quantized_size} < ${original_size} bytes)" >&2
        echo "$quantized_data" >> "$OUTPUT_FILE"
    else
        echo "  → Using original (${original_size} ≤ ${quantized_size} bytes)" >&2
        echo -e "$batch_data" >> "$OUTPUT_FILE"
    fi
}

process_cast_file() {
    local batch_data=""
    local batch_start=""
    local batch_end=""
    local current_time=0
    local next_batch_time=$FRAME_INTERVAL
    
    while IFS= read -r line; do
        # Parse timestamp
        local timestamp
        timestamp=$(echo "$line" | jq -r '.[0]' 2>/dev/null || echo "0")
        
        # Check if we need a new batch
        if [[ $(awk "BEGIN {print ($timestamp >= $next_batch_time) ? 1 : 0}") == "1" ]] || [[ -z "$batch_start" ]]; then
            # Process previous batch
            process_batch "$batch_data" "$batch_start" "$current_time"
            
            # Start new batch
            batch_data="$line"
            batch_start="$timestamp"
            
            # Update next batch time
            while [[ $(awk "BEGIN {print ($timestamp >= $next_batch_time) ? 1 : 0}") == "1" ]]; do
                next_batch_time=$(awk "BEGIN {print $next_batch_time + $FRAME_INTERVAL}")
            done
        else
            # Add to current batch
            [[ -n "$batch_data" ]] && batch_data="${batch_data}"$'\n'"$line" || batch_data="$line"
        fi
        
        current_time="$timestamp"
    done
    
    # Process final batch
    process_batch "$batch_data" "$batch_start" "$current_time"
}

main() {
    # Validate input
    if [[ ! -f "$CAST_FILE" ]]; then
        echo "Error: Cast file '$CAST_FILE' not found" >&2
        exit 1
    fi
    
    # Set up cleanup
    shell_trap cleanup
    
    # Initialize
    setup_fifos
    start_playback_pipeline
    start_recording_pipeline
    
    # Get pane ID and clear terminal
    PANE_ID=$(tmux display-message -p '#{pane_id}')
    clear
    
    # Read header
    read -r HEADER < "$CAST_FILE"
    echo "$HEADER" > "$OUTPUT_FILE"
    
    # Parse dimensions
    local width height
    width=$(echo "$HEADER" | jq -r '.width')
    height=$(echo "$HEADER" | jq -r '.height')
    
    echo "Quantizing at $FPS fps (${FRAME_INTERVAL}s intervals)" >&2
    echo "Terminal: ${width}×${height}" >&2
    echo "" >&2
    
    # Give pipelines time to stabilize
    sleep 0.5
    
    # Process the cast file
    tail -n +2 "$CAST_FILE" | process_cast_file
    
    echo "" >&2
    echo "Quantization complete: $OUTPUT_FILE" >&2
    
    # Let pipelines finish
    sleep 0.5
}

main "$@"