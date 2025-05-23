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

# Read the header (first line)
HEADER=$(head -n1 "$INPUT_FILE")

# Initialize variables
chunk_num=1
current_window_start=0
current_window_end=$WINDOW_SIZE
chunk_file=""

# Process the file line by line
while IFS= read -r line; do
    # Skip the header line
    if [[ "$line" == "$HEADER" ]]; then
        continue
    fi
    
    # Extract timestamp from the line
    # Format: [timestamp, "o", "data"]
    timestamp=$(echo "$line" | cut -d',' -f1 | tr -d '[]' | xargs)
    
    # If timestamp is greater than current window end, start new chunk
    if (( $(echo "$timestamp >= $current_window_end" | bc -l) )); then
        # Finalize current chunk if it exists
        if [[ -n "$chunk_file" ]] && [[ -f "$chunk_file.tmp" ]]; then
            mv "$chunk_file.tmp" "$chunk_file"
            echo "Created $chunk_file ($(wc -l < "$chunk_file") lines)"
        fi
        
        # Calculate which window this timestamp belongs to
        window_num=$(echo "scale=0; $timestamp / $WINDOW_SIZE" | bc -l)
        chunk_num=$((window_num + 1))
        current_window_start=$(echo "$window_num * $WINDOW_SIZE" | bc -l)
        current_window_end=$(echo "($window_num + 1) * $WINDOW_SIZE" | bc -l)
        
        # Start new chunk
        chunk_file=$(printf "%s/%06d.cast" "$OUTPUT_DIR" "$chunk_num")
        echo "$HEADER" > "$chunk_file.tmp"
    fi
    
    # Write line to current chunk
    if [[ -n "$chunk_file" ]]; then
        echo "$line" >> "$chunk_file.tmp"
    fi
    
done < "$INPUT_FILE"

# Finalize last chunk
if [[ -n "$chunk_file" ]] && [[ -f "$chunk_file.tmp" ]]; then
    mv "$chunk_file.tmp" "$chunk_file"
    echo "Created $chunk_file ($(wc -l < "$chunk_file") lines)"
fi

# Summary
total_chunks=$(ls "$OUTPUT_DIR"/*.cast 2>/dev/null | wc -l)
echo -e "\nSplit complete: $total_chunks chunks created in $OUTPUT_DIR"

# Show first few chunks info
echo -e "\nFirst few chunks:"
for f in $(ls "$OUTPUT_DIR"/*.cast 2>/dev/null | head -5); do
    lines=$(($(wc -l < "$f") - 1))  # Subtract header line
    echo "  $(basename "$f"): $lines events"
done