# Terminal Recording Test Cases

## Special Characters
- [ ] Box drawing: `echo "┌─┐│ │└─┘"`

## Long Output
- [ ] Generate lots of output: `seq 1 1000`
- [ ] Colored output: `ls -la --color=always`
- [ ] Progress bars: `for i in {1..100}; do echo -ne "\r$i%"; sleep 0.01; done`

## Edge Cases
- [ ] Very wide lines: `echo $(printf '=%.0s' {1..200})`
- [ ] Rapid updates: `watch -n 0.1 date`
- [ ] Binary output: `cat /bin/ls | head -c 100`
