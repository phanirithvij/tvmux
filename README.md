# 🤖 monitor

So I want to capture my dev work in tmux so I can train models on how to program
and actually use a computer. More data is good.

This is my current tmux setup, including my `tmux.conf`.

## `0.3.0`

This shell script records a session following the active pane. After some turd
polish and more testing, I plan to expand it to work with one window per
project and separate recordings for each. I'll likely split it up into a library
of bash scripts that are concatenated on deployment, like I have in
[🔗 rip](https://github.com/bitplane/rip).

From 0.3 onwards, with each stable period I'll tag it as a "release" even though
it's not really a release.

## To-do

### General

- [ ] get the monitor panel working so i don't need to manually create it each
      reboot.
- [ ] Write a `./configure` script that checks all the things we need.
- [ ] `make build` and `make install` to `$PREFIX`, defaulting to `~/.local/`
- 


### `0.4`

- [ ] Drop the fifo and actually record all the 

### `0.5`

- [ ] Command line args / flags / config
  - [ ] Consider a generic settings approach that works with config file, args
        and env vars as first class citizens.
  - [ ] Consider different entrypoints.
- [ ] Review breaking down into functions like in `rip`
