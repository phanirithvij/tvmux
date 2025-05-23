#!/bin/bash
set -e

# Default input file
INPUT_FILE="${1:-current.cast}"
OUTPUT_DIR="./.cache/split-test"
FPS="${2:-1}"  # Default 1 frame per second
WINDOW_SIZE=$(bc -l <<< "scale=6; 1/$FPS")

# Check if input file exists
if [[ ! -f "$INPUT_FILE" ]]; then
    echo "Error: Input file '$INPUT_FILE' not found"
    exit 1
fi

# Create output directory
mkdir -p "$OUTPUT_DIR"
rm -f "$OUTPUT_DIR"/*.cast  # Clean up any existing files

echo "Splitting $INPUT_FILE into $FPS fps chunks..."
echo "Window size: $WINDOW_SIZE seconds"

# Read the header
HEADER=$(head -n1 "$INPUT_FILE")

# Use awk for faster processing
tail -n +2 "$INPUT_FILE" | awk -v header="$HEADER" -v outdir="$OUTPUT_DIR" -v window="$WINDOW_SIZE" '
BEGIN {
    chunk_num = 1
    current_file = sprintf("%s/%06d.cast", outdir, chunk_num)
    print header > current_file
    current_window_end = window
    lines_in_chunk = 0
}
{
    # Extract timestamp (first field between brackets)
    match($0, /^\[([0-9.]+)/, arr)
    timestamp = arr[1]
    
    # Check if we need a new chunk
    if (timestamp >= current_window_end) {
        # Close current file
        close(current_file)
        if (lines_in_chunk > 0) {
            printf "Created %s (%d events)\n", current_file, lines_in_chunk
        }
        
        # Calculate new chunk number based on timestamp
        chunk_num = int(timestamp / window) + 1
        current_window_end = chunk_num * window
        
        # Start new file
        current_file = sprintf("%s/%06d.cast", outdir, chunk_num)
        print header > current_file
        lines_in_chunk = 0
    }
    
    # Write line to current chunk
    print $0 > current_file
    lines_in_chunk++
}
END {
    if (lines_in_chunk > 0) {
        printf "Created %s (%d events)\n", current_file, lines_in_chunk
    }
}'

# Summary
total_chunks=$(ls "$OUTPUT_DIR"/*.cast 2>/dev/null | wc -l)
echo -e "\nSplit complete: $total_chunks chunks created in $OUTPUT_DIR"

# Show first few chunks info
echo -e "\nFirst few chunks:"
for f in $(ls "$OUTPUT_DIR"/*.cast 2>/dev/null | head -5); do
    lines=$(($(wc -l < "$f") - 1))  # Subtract header line
    echo "  $(basename "$f"): $lines events"
done