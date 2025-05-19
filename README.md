# tmux monitor stuff

So I want to capture my dev work in tmux so I can train models on how to program
and actually use a computer. More data is good.

This is my tmux setup

## todo

- [ ] get the monitor panel working so i don't need to manually create it each
      reboot.

### Session recorder edge cases to handle:

- [ ] Terminal modes when switching panes:
  - [ ] Alternative screen buffer (e.g., vim, less, htop)
    - bugs here seem impossible to fix without a pipe interceptor and screen
      refresh. might be worth writing a tty state buffer tool
  - [ ] Application keypad mode
  - [ ] Mouse tracking mode
  - [ ] Bracketed paste mode
  - [ ] Line wrap mode

- [ ] Special terminal states:
  - [ ] Color palette changes

- [ ] Input handling:
  - [ ] Raw vs cooked mode
  - [ ] Echo on/off
