# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

**Build and setup:**
- `make dev` - Set up development environment with venv and pre-commit hooks
- `make install` - Install production dependencies only
- `make clean` - Remove caches and virtual environment

**Testing:**
- `make test` - Run all tests using pytest
- `make coverage` - Generate HTML coverage report

**Code quality:**
- Pre-commit hooks automatically run ruff for linting and formatting
- `ruff check .` - Manual linting
- `ruff format .` - Manual code formatting

**Distribution:**
- `make dist` - Build distributable packages
- `make release` - Publish to PyPI

## Architecture Overview

tvmux is a terminal session recorder that creates asciinema cast files from tmux sessions. The project is undergoing a rewrite from Bash (master branch) to Python with a client-server architecture.

### Core Components

**CLI Interface (`src/tvmux/cli/`):**
- `main.py` - Main CLI entry point with server and record commands
- `server.py` - Server management commands (start/stop/status)
- `record.py` - Recording control commands

**FastAPI Server (`src/tvmux/server/`):**
- `main.py` - FastAPI application with lifespan management and tmux hook setup
- `state.py` - Global state management for recorders and server configuration
- `routers/` - REST API endpoints:
  - `/sessions` - Session management
  - `/windows` - Window management
  - `/panes` - Pane operations (separate from windows)
  - `/recordings` - Recording control (RESTful with IDs)
  - `/callbacks` - tmux hook callbacks

**Recording Engine (`src/tvmux/`):**
- `recorder.py` - Core recording functionality using asciinema and FIFOs
- `background.py` - Process management for background tasks
- `repair.py` - Cast file repair utilities for handling abrupt terminations

**Data Models (`src/tvmux/models/`):**
- Pydantic models for sessions, windows, panes, and positions
- Type-safe data structures for the REST API

### Key Architecture Decisions

**Client-Server Pattern:**
- REST API at 127.0.0.1:21590 for tmux integration
- Server manages global state and multiple window recordings
- CLI tools communicate via HTTP to the server

**Active Pane Following:**
- Records only the currently active pane rather than entire sessions
- Dramatically reduces file sizes while capturing relevant workflow
- Automatically switches recording focus when user changes panes

**FIFO-based Streaming:**
- Uses named pipes to stream terminal output to asciinema
- Enables real-time recording with proper terminal state preservation
- Handles pane switching by dumping state and redirecting streams

## Recording Flow

1. Server starts and sets up tmux hooks for pane change callbacks
2. When recording starts, creates FIFO and launches asciinema process
3. Dumps initial pane state (content + cursor position) to FIFO
4. Starts `tmux pipe-pane` to stream live output to FIFO
5. On pane switches, stops old stream, dumps new state, starts new stream
6. On stop, sends terminal reset sequences and repairs cast file

## Output Organization

Recordings are organized by date: `output_dir/YYYY-MM/timestamp_hostname_session_window.cast`

## Development Notes

- Python 3.10+ with type hints and Pydantic models
- Async/await for server operations
- Uses `scripts/test.sh` (pytest) for testing
- Ruff for linting and formatting (120 char line length)
- Pre-commit hooks enforce code quality
- Background process management prevents orphaned processes
