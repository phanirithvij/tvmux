# 📺 `tvmux`

asciinema tmux recorder

## ⁉️ why!?

So I can record tmux sessions and archive my workflow, then later use them for
AI training.


# LETS REWRITE IN PYTHON

## 🏗️ v0.4 Refactoring Plan

### Phase 1: Core Architecture & Library Reorganization
- [ ] **Library structure refactoring**
  - [ ] Create `fd.sh` (file descriptor management)
  - [x] Create `lib_daemon.sh` (daemon lifecycle management)

### Phase 2: Daemon Architecture
- [ ] **Socket-based daemon**
  - [x] `daemon_start()` - Launch daemon process
  - [ ] `daemon_status()` - Verify daemon is alive
  - [x] Store socket path in `tmux @TVMUX_DAEMON_SOCKET`
  - [x] Store daemon PID in `tmux @TVMUX_DAEMON_PID`
- [ ] **APC protocol dispatcher**
  - [ ] Inline AWK parser for escape sequences
  - [ ] `tvmux_apc_parser()` - Extract commands from stream
  - [ ] Security: Command whitelisting in AWK
  - [ ] Security: Argument sanitization
  - [ ] Output: `prefix_function "context" "arg1" "arg2"`
- [ ] **Multiplexed dispatcher reading**
  - [ ] Round-robin reading from multiple AWK parsers
  - [ ] Non-blocking reads with timeout
  - [ ] Dynamic dispatcher spawn/teardown

### Phase 3: Hook & State Management
- [ ] **Tmux hook stacking**
  - [ ] `tmux_hook_add()` - Add handler without overwriting
  - [ ] `tmux_hook_remove()` - Remove specific handler
  - [ ] `tmux_hook_wrap()` - Wrap existing hooks
  - [ ] Daemon maintains hook handler registry
  - [ ] Self-healing hooks (check on each trigger)
- [ ] **FD-based pipeline management**
  - [ ] Replace FIFOs with file descriptors
  - [ ] `tvmux_fd_open_pipe()` - Create pipe with FDs
  - [ ] `tvmux_fd_connect()` - Connect to socket
  - [ ] `tvmux_fd_route()` - Route data between FDs
  - [ ] Store FDs in associative arrays
- [ ] **Configuration system**
  - [ ] `tvmux_args_define()` - Define command arguments
  - [ ] `tvmux_args_parse()` - Parse with precedence
  - [ ] Precedence: defaults < env < config < CLI
  - [ ] Environment vars: `TVMUX_COMMAND_ARGNAME`
  - [ ] No `.env` files (use tmux environment)

### Phase 4: Remote Deployment & Multi-Instance
- [ ] **Self-deployment to tmux server**
  - [ ] `tvmux_deploy_check()` - Check deployment version
  - [ ] `tvmux_deploy_transfer()` - Transfer script via tmux
  - [ ] `tvmux_deploy_execute()` - Run on tmux server host
  - [ ] Hash comparison for version management
  - [ ] Refuse to run if versions conflict
- [ ] **Per-tmux-server instances**
  - [ ] Socket naming: `/tmp/tvmux.$USER/daemon.$TMUX_PID.sock`
  - [ ] One daemon per tmux server
  - [ ] Clean shutdown on tmux server exit

### Phase 5: Per-Window Recording (Building on new architecture)
- [ ] Recording per window/project
  - [x] Window recording status indicator
    - [ ] Change to pause indicator when recording but not active
  - [ ] **Window-based pipelines**
    - [ ] One asciinema process per window
    - [ ] Window ID → pipeline FD mapping
    - [ ] Dynamic pipeline creation/destruction
  - [ ] **File naming & organization**
    - [ ] Base: `~/Videos/tmux/YYYY-MM/`
    - [ ] Files: `YYYY-MM-DD_HHMM_sessionid_windowid.cast`
    - [ ] Symlinks: `YYYY-MM-DD_HHMM_sessionname_windowname.cast`
    - [ ] Update symlinks on window rename
  - [ ] **Window lifecycle integration**
    - [ ] Hook: `window-renamed` → update symlinks
    - [ ] Hook: `window-unlinked` → stop recording
    - [ ] Hook: `pane-died` → check if window empty

### Phase 6: Advanced Pipeline Features
- [ ] **Pipeline architecture**
  - [ ] Stage management in daemon
  - [ ] Pluggable pipeline stages
  - [ ] Built-in stages: quantizer, compressor
- [ ] **State tracking for all panes**
  - [ ] Lightweight monitoring mode
  - [ ] Track cursor, screen mode, colors
  - [ ] Materialize full state on demand
  - [ ] Switch monitoring → recording seamlessly

### Phase 7: Future Enhancements
- [ ] **Advanced state tracking**
  - [ ] Scrollback buffer position
  - [ ] Selection/highlights
  - [ ] Alternative buffer snapshots
  - [ ] Pane geometry tracking
- [ ] **File size optimization**
  - [ ] Quantizer integration
  - [ ] Remove redundant escape sequences
  - [ ] Compress during recording
- [ ] **Export formats**
  - [ ] MP4 generation
  - [ ] GIF export
  - [ ] Timeline scrubbing
- [ ] **Quality of life**
  - [ ] Graceful recording resume
  - [ ] Better error messages
  - [ ] Man page generation
  - [ ] Web UI for playback

### Future

- [ ] Running by piping into a session. `tvmux remote` ought to work if we cat
      the script (build) into a buffer, add an entrypoint, then dump and execute
      with bash.


## 🔗 links

* [🏠 home](https://bitplane.net/dev/sh/tvmux)
* [🐱 github](https://github.com/bitplane/tvmux)

### 🌍 awesome projects

* [📺 asciinema](https://asciinema.org/)
* [🪟 textual](https://textualize.io/)
