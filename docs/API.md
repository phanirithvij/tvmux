# API CLI Design - Single Source of Truth

## The Problem
We want to maintain API and CLI definitions in sync so that:
1. The Textual TUI can consume the HTTP API
2. We can test API endpoints without the TUI
3. Remote tmux servers can be supported
4. Web UI can be port-forwarded and proxied

## Current Solution
Auto-generated CLI from FastAPI routes using introspection:

```python
# Automatically generates commands like:
tvmux api sessions list
tvmux api sessions create --name my-session
tvmux api recordings start --session-id 0 --window-id @1
tvmux api panes send-keys %1 --keys "ls -la"
```

## Benefits
- **Zero maintenance**: CLI updates automatically when routes change
- **Type safety**: Pydantic models ensure correct data types
- **Testing**: Can test every API endpoint from CLI
- **Documentation**: FastAPI's docstrings become CLI help text
- **Remote support**: Same CLI works for local or remote servers

## Future Enhancements

### 1. Better Output Formatting
```python
# Add format options
tvmux api sessions list --format=table
tvmux api sessions list --format=json
tvmux api sessions list --format=yaml
```

### 2. Decorator-Based Approach
```python
@api_route("POST", "/recordings/")
@cli_command("rec", "start")  # Also generates 'tvmux rec start'
async def create_recording(request: RecordingCreate):
    """Start a new recording."""
    ...
```

### 3. Remote Server Support
```bash
# Connect to remote tvmux server
tvmux --server=remote.host:21590 api sessions list
tvmux --server=container.local:21590 rec start
```

### 4. WebSocket Support for Live Updates
```python
# Watch for changes
tvmux api recordings watch  # Streams updates via WebSocket
```

### 5. Batch Operations
```python
# Execute multiple commands from file
tvmux api batch commands.yaml
```

## Use Cases

### Development & Testing
```bash
# Test recording flow without UI
tvmux api recordings create --session-id 0 --window-id @1
tvmux api panes select %2  # Trigger pane switch
tvmux api recordings delete 0:@1
```

### CI/CD & Automation
```bash
# Script complex workflows
#!/bin/bash
SESSION=$(tvmux api sessions create --name test | jq -r '.id')
WINDOW=$(tvmux api windows create --session $SESSION | jq -r '.id')
tvmux api recordings create --session-id $SESSION --window-id $WINDOW
```

### Remote Management
```bash
# Manage recordings on remote servers
tvmux --server=prod.example.com:21590 api recordings list
tvmux --server=prod.example.com:21590 api recordings stop all
```

## Implementation Notes

The current implementation:
1. Introspects FastAPI routes at module load time
2. Extracts path parameters, query parameters, and body models
3. Converts Pydantic models to Click options
4. Groups commands by resource (sessions, windows, panes, etc.)
5. Preserves all API functionality through the CLI

This approach ensures the CLI is always in sync with the API, making it perfect for:
- Testing Textual UI features without the UI
- Scripting and automation
- Remote server management
- API exploration and debugging
