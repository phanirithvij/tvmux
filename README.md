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

By default, it'll save to `~/Videos/tmux/YYYY-MM/`. See all configuration options:

```bash
# Show default config (TOML format)
tvmux config defaults

# Show available environment variables
tvmux config defaults --format=env

# Show your current config
tvmux config show
```

To customize, create `~/.tvmux.conf` or use environment variables like `TVMUX_OUTPUT_DIRECTORY`.

## 🔗 links

* [🏠 home](https://bitplane.net/dev/python/tvmux)
* [📚 pydoc](https://bitplane.net/dev/python/tvmux/pydoc)
* [📚 api](https://bitplane.net/dev/python/tvmux/api)
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
