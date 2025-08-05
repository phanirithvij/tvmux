# 📺 `tvmux`

Per-project/window `tmux` recorder using `asciinema`; records the current pane
and follows the user around the current window.

## 🎥 Usage

Install `tvmux` from pip or uv, or run standalone from `uvx`, like so:

```bash
$ uvx tvmux --help
```

Or, if installed, run from inside a tmux pane:

```bash
# Start recording
tvmux rec
# list ongoing recordings
tvmux rec ls
# stop them all, like you would a Docker container
tvmux rec stop $(tvmux ls -q)
```

By default, it'll save to `~/Videos/tmux/YYYY-MM/`, you can change this
with a `.tvmux.conf` in your homedir:

```toml
# Example tvmux configuration file
# Copy to ~/.tvmux.conf or specify with --config-file

[output]
# Base directory for recordings (supports ~ expansion)
directory = "~/Videos/tmux"

# Date format for subdirectories (Python strftime format)
date_format = "%Y-%m"

[server]
# Server port (can also be set with TVMUX_SERVER_PORT)
port = 21590

# Auto-start server when needed
auto_start = true

# Auto-shutdown server when no recordings active
auto_shutdown = true

[recording]
# Repair cast files on stop (fixes JSON corruption from abrupt terminations)
repair_on_stop = true

# Follow active pane switches within windows
follow_active_pane = true

[annotations]
# Include cursor position and visibility in recordings
include_cursor_state = true
```

## 🔗 links

* [🏠 home](https://bitplane.net/dev/python/tvmux)
* [📚 pydoc](https://bitplane.net/dev/python/tvmux/pydoc)
* [🐱 github](https://github.com/bitplane/tvmux)
* [🐍 pypi](https://pypi.org/project/tvmux)

### 🌍 See also

|                                                     |                                    |
|-----------------------------------------------------|------------------------------------|
| [📺 asciinema](https://asciinema.org/)              | The terminal recorder              |
| [🪟 textual](https://textualize.io/)                | TUI library for Python             |
| [🗔  bittty](https://bitplane.net/dev/python/bittty) | My terminal                        |
| [🎬 sh2mp4](https://bitplane.net/dev/sh/sh2mp4)     | Convert this to MP4 files          |

## TODO

### Prep for next steps

- [ ] Need asciinema scrubber using bittty ([wip](https://github.com/ttygroup/textual-asciinema))
- [ ] Start a basic TUI in Textual
