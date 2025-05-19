# Terminal Recording Test Cases

## Basic Tests
- [x] Echo some text with colors: `echo -e "\033[31mRed\033[32mGreen\033[0m"`
- [x] Clear screen: `clear`
- [x] Move cursor around: `tput cup 5 10; echo "Here"`

## Pane Switching Tests
- [x] Create multiple panes (`Ctrl+B %` and `Ctrl+B "`)
- [x] Switch between panes (`Ctrl+B arrow keys`)
- [x] Run different commands in each pane
- [x] Resize panes (`Ctrl+B Alt+arrow keys`)

## Terminal Modes Tests
- [ ] Test vim (alternative screen): `vim test.txt`
   - Insert mode, normal mode
   - Exit with `:q`
- [ ] Test sl (scroll region): `sl` and switch panes while it's running
- [ ] Test less: `less /etc/passwd`
- [ ] Test htop: `htop`
- [ ] Test man pages: `man ls`

## Special Characters
- [x] Unicode: `echo "Hello 世界 🌍"`
- [ ] Box drawing: `echo "┌─┐│ │└─┘"`
- [x] Tab characters: `echo -e "Column1\tColumn2"`

## Terminal States
- [x] Hide cursor: `tput civis`
- [x] Show cursor: `tput cnorm`
- [ ] Bold text: `echo -e "\033[1mBold\033[0m"`
- [ ] Terminal bell: `echo -e "\a"`

## Long Output
- [ ] Generate lots of output: `seq 1 1000`
- [ ] Colored output: `ls -la --color=always`
- [ ] Progress bars: `for i in {1..100}; do echo -ne "\r$i%"; sleep 0.01; done`

## Edge Cases
- [ ] Very wide lines: `echo $(printf '=%.0s' {1..200})`
- [ ] Rapid updates: `watch -n 0.1 date`
- [ ] Binary output: `cat /bin/ls | head -c 100`

## Recording Checks
- [x] Verify current.cast symlink exists
- [x] Check asciinema JSON is valid: `jq . current_session.cast`
- [x] Test local playback: `asciinema play current_session.cast`
