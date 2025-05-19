# Refactor plan

* to `make build`, we alias out `source` with `cat $1; . $1` then
  `source tmux-record.sh > ./build/tmux-record` (lol, or `sed` if that's too dirty)
* add `make install` step with default `PREFIX` of `$HOME/.local`

