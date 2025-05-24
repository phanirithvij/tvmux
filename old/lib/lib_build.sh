#!/bin/bash
# Build functions for tvmux

# Build a self-contained script from source files
build_self() {
    local output_file="$1"

    if [[ -z "$output_file" ]]; then
        echo "Error: output file required" >&2
        return 1
    fi

    # Find the main script
    local main_script="${TVMUX_SCRIPT_DIR:-$(dirname "$0")}/tvmux.sh"

    if [[ ! -f "$main_script" ]]; then
        echo "Error: main script not found at $main_script" >&2
        return 1
    fi

    # Create output directory if needed
    mkdir -p "$(dirname "$output_file")" || return 1

    # Build the script
    echo "#!/bin/bash" > "$output_file"
    echo "" >> "$output_file"
    cat "${TVMUX_SCRIPT_DIR:-$(dirname "$0")}/lib"/*.sh "$main_script" | \
        grep -Ev '^#' | grep -Ev '^source ' >> "$output_file"

    # Make executable
    chmod +x "$output_file"

    echo "Built $output_file"
    return 0
}
