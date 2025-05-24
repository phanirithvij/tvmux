# 📺 `tvmux`

asciinema tmux pane recorder

## ⁉️ why!?

I wanted to record my terminal development workflow, so I can later summarise it
and tune models on me programming and using TUI apps. So I did a proof of
concept of collection by recording `asciinema rec -c "tmux att"`, which ended up
being enormous and largely irrelevant.

Recording the top level is about 450MB for a day's worth of hacking in my one day
test. This compressed to ~8MB with xz, but I don't have any idea of where the
window splits are, and don't trust LLM inference to infer them. As an example for
comparison, a test window looks like this:

[https://asciinema.org/a/720036](https://asciinema.org/a/720036)

For my next iteration, I tried recording individual panes. Which, with lots of
long-running jobs and monitors showing log files, ended up being ... uh... a
pane? Not just saving window geometry and stitching it back together again, but
some background panes had excessively large outputs. They're in the background,
so I don't care about them.

So for mk3, I made this recording tool that follows the active pane by detecting
the pane change, dumping the contents, injecting control codes and stovepiping
everything after it into `asciinema` via tail.

The session above looks like this as I navigate, which shows exactly what I'm up
to, far better IMO:

[https://asciinema.org/a/720034](https://asciinema.org/a/720034)

# ▶️ usage

Currently there's a release, and you can just drop that into `~/.local/bin` but
it's really a test of the release process so is a bit flaky. For best results,
run this from inside your tmux session:

```bash
$ git clone https://github.com/bitplane/tvmux.git
$ cd tvmux
$ make start
# ... some time later ...
$ make stop
```

You'll see a symlink linking to the `.cast` file which will be under `./.cache`.
There's `make` steps for build and install but without testing, who knows where
the outputs will go (lol)

# ⏩ What's next?

- [ ] Recording per window/project
  - [x] Window recording status indicator
    - [ ] Change to pause indicator when recording but not active
  - [ ] 
- [ ] Tracking / dumping state
  - [x] Cursor position
  - [ ] Scrollback buffer
   - [ ] Scroll position
   - [ ] Highlight/selection
  - [ ] Alternative buffer tracking
  - [ ] Geometry
    - [x] Terminal size
    - [ ] Pane position + details
- [ ] Application specific escape codes
  - [x] set for variables
  - [ ] Terminal geometry
  - [ ] Timestamping
  - [ ] Investigate 
- [ ] Reduce file size
  - [ ] Phase 1: Measure and fix FPS
  - [ ] Remove alt buffer + scrollback when not used 
- [ ] Config files, env vars and args via a bash library.
- [ ] Exporting to various formats
  - [ ] MP4
    - [ ] Integrate sh2mp4 (combine?)
  - [ ] GIF - use `agg`
- [ ] Keep using it and adding turd polish!
  - [ ] Fix recording paths
  - [ ] Docs
     - [ ] Make docs publish to bitplane.net
     - [ ] Manpage install
  - [ ] Allow sourcing lib.sh from other dirs
  - [ ] Allow graceful continuation of recording
  - [ ] First bytes bug again :/
  - [ ] Nesting hooks?

## 🔗 links

* [🏠 home](https://bitplane.net/dev/sh/tvmux)
* [🐱 github](https://github.com/bitplane/tvmux)

### 🌍 awesome projects

* [📺 asciinema](https://asciinema.org/)
* [🪟 textual](https://textualize.io/)

