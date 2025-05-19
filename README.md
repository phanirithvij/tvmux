# tmux monitor stuff

So I want to capture my dev work in tmux so I can train models on how to program
and actually use a computer. More data is good.

This is my tmux setup

## todo

- [x] fix the session recorder
- [ ] get the monitor panel working so i don't need to manually create it each
      reboot.
- [x] Fix asciinema server compatibility (recordings cause internal server error)

### Session recorder edge cases to handle:

- [ ] Terminal modes when switching panes:
  - [x] Cursor visibility state (hidden/visible)
  - [ ] Alternative screen buffer (e.g., vim, less, htop)
  - [ ] Application keypad mode
  - [ ] Mouse tracking mode
  - [ ] Bracketed paste mode
  - [ ] Line wrap mode

- [ ] Special terminal states:
  - [ ] Character encoding (UTF-8 vs others)
  - [ ] Color palette changes
  - [ ] Terminal title changes
  - [ ] Bell/notification states

- [ ] Input handling:
  - [ ] Raw vs cooked mode
  - [ ] Echo on/off

- [ ] Performance issues:
  - [ ] Optimize session directory lookup (mentioned in code TODO)
  - [ ] Handle very long-running sessions (file size limits)
  - [ ] Buffer overflow protection

