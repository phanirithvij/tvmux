#!/usr/bin/env bash
# Dependency checker for tvmux

# Colors
CONFIGURE_RED='\033[0;31m'
CONFIGURE_GREEN='\033[0;32m'
CONFIGURE_YELLOW='\033[1;33m'
CONFIGURE_BOLD='\033[1m'
CONFIGURE_NC='\033[0m'

# Track missing dependencies
CONFIGURE_MISSING=""
CONFIGURE_OPTIONAL_MISSING=""

# Check if a tool is available
configure_check_tool() {
    local tool="$1"
    local required="${2:-true}"
    local install_hint="${3:-}"

    printf "  %-20s" "$tool" >&2

    if command -v "$tool" >/dev/null 2>&1; then
        echo -e "${CONFIGURE_GREEN}✓${CONFIGURE_NC} Found" >&2
        return 0
    else
        if [[ "$required" == "true" ]]; then
            echo -e "${CONFIGURE_RED}✗${CONFIGURE_NC} Missing (required)" >&2
            CONFIGURE_MISSING="$CONFIGURE_MISSING $tool"
        else
            echo -e "${CONFIGURE_YELLOW}○${CONFIGURE_NC} Missing (optional)" >&2
            CONFIGURE_OPTIONAL_MISSING="$CONFIGURE_OPTIONAL_MISSING $tool"
        fi

        if [[ -n "$install_hint" ]]; then
            echo "    → $install_hint" >&2
        fi
        return 1
    fi
}

# Check bash version
configure_check_bash_version() {
    printf "  %-20s" "bash version" >&2

    if ((BASH_VERSINFO[0] >= 4)); then
        echo -e "${CONFIGURE_GREEN}✓${CONFIGURE_NC} ${BASH_VERSION}" >&2
        return 0
    else
        echo -e "${CONFIGURE_RED}✗${CONFIGURE_NC} ${BASH_VERSION} (requires 4.0+)" >&2
        CONFIGURE_MISSING="$CONFIGURE_MISSING bash4+"
        return 1
    fi
}

# Main configure function
cmd_configure() {
    echo -e "${CONFIGURE_BOLD}Checking tvmux dependencies...${CONFIGURE_NC}" >&2
    echo >&2

    # Core requirements
    echo -e "${CONFIGURE_BOLD}Core Requirements:${CONFIGURE_NC}" >&2
    configure_check_bash_version
    configure_check_tool "tmux" "true" "Install: apt install tmux"
    configure_check_tool "asciinema" "true" "Install: apt install asciinema"
    echo >&2

    # Optional tools for enhanced functionality
    echo -e "${CONFIGURE_BOLD}Optional Tools:${CONFIGURE_NC}" >&2
    configure_check_tool "ffmpeg" "false" "Install: apt install ffmpeg"
    configure_check_tool "jq" "false" "Install: apt install jq"
    configure_check_tool "shellcheck" "false" "Install: apt install shellcheck"
    configure_check_tool "pre-commit" "false" "Install: pip install pre-commit"
    echo >&2

    # Summary
    echo -e "${CONFIGURE_BOLD}Summary:${CONFIGURE_NC}" >&2

    if [[ -z "$CONFIGURE_MISSING" ]]; then
        echo -e "${CONFIGURE_GREEN}✓ All required dependencies are installed${CONFIGURE_NC}" >&2

        if [[ -n "$CONFIGURE_OPTIONAL_MISSING" ]]; then
            echo -e "${CONFIGURE_YELLOW}○ Optional tools missing:${CONFIGURE_OPTIONAL_MISSING}${CONFIGURE_NC}" >&2
        else
            echo -e "${CONFIGURE_GREEN}✓ All optional dependencies are installed${CONFIGURE_NC}" >&2
        fi

        return 0
    else
        echo -e "${CONFIGURE_RED}✗ Missing required dependencies:${CONFIGURE_MISSING}${CONFIGURE_NC}" >&2
        echo >&2
        echo "Please install the missing dependencies and try again." >&2
        return 1
    fi
}
