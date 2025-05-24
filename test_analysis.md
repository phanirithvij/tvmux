# Test Analysis - Issues and Bad Practices

## 1. **Variable Name Mismatch Bug** (test_proc_trap_order.sh)
- **Issue**: The test itself documents a bug - `proc_trap` uses `_PROC_EXIT_$$` but `__proc_exit` uses `_SHELL_EXIT_$$`
- **Impact**: Trap handlers never execute
- **Fix**: The variable names need to be consistent in the implementation

## 2. **Hardcoded Paths/Assumptions**

### test_configure_optional_missing.sh & test_configure_required_*.sh
- Mocks `command` by creating a function that shadows `/usr/bin/command`
- **Issue**: Assumes `command` binary is at `/usr/bin/command` (line 10)
- **Better**: Use `$(which command)` or `builtin command`

### test_proc_kill_tree.sh
- Uses `mktemp` without checking if it fails
- No error handling if the test script creation fails

## 3. **Missing Cleanup**

### test_proc_kill_tree.sh
- Has cleanup (`trap "rm -f $test_script" EXIT`) but if the test fails catastrophically, orphan processes might remain
- Uses `pkill -f "$test_script"` only on failure, not in trap handler
- Should kill all test processes in EXIT trap

### test_proc_trap_order.sh
- Similar issue - creates temp file but doesn't clean up potential subshell processes

## 4. **Race Conditions**

### test_proc_kill_tree.sh
- Uses `sleep 0.2` to wait for processes to start
- Uses `sleep 0.5` to wait for kill to complete
- **Issue**: These are arbitrary delays that could fail on slow systems
- **Better**: Use a loop with timeout to check process state

## 5. **Tests That Don't Test Much**

### test_tvmux_sources.sh
- Only checks if sourcing produces stderr output
- Doesn't verify any functionality actually works
- Could pass even if the script is completely broken but happens to not print errors

### test_tvmux_help_output.sh
- Only checks if output contains "Available commands:"
- Doesn't verify help is actually helpful or complete

### test_configure_success.sh
- Accepts both exit code 0 and 1 as success (line 10)
- Comment says "Just check that it runs without crashing" - not a meaningful test

## 6. **Duplicate/Redundant Tests**

### test_args.sh vs test_args_generic.sh vs test_lib_args.sh
- All three test the same library with significant overlap
- test_lib_args.sh is the most comprehensive and well-structured
- The other two could be removed or merged

### test_args_*.sh individual files vs test_lib_args.sh
- Many individual test files (test_args_bool_flag.sh, test_args_int_valid.sh, etc.) duplicate tests already in test_lib_args.sh
- Having both creates maintenance burden

### test_tvmux_help.sh vs test_tvmux_help_output.sh
- Both test help functionality
- test_tvmux_help_output.sh is too minimal to be useful

## 7. **Poor Test Isolation**

### test_args_env_precedence.sh
- Sets environment variables that could affect other tests if run in the same shell
- Doesn't unset variables after test

### test_init.sh
- Sources lib_init.sh which could pollute the test environment
- Better to run in a subshell

## 8. **Inconsistent Test Patterns**

### Exit codes
- Some tests use explicit `exit 0/1`
- Others rely on last command status
- Some use `[[ condition ]] && exit 0 || exit 1`

### Output
- Some tests are verbose with echo statements
- Others are completely silent
- No consistent format for pass/fail reporting

## 9. **Tests Don't Match Filenames**

### test_proc.sh
- Filename suggests it tests process functions
- Actually tests very basic functionality and shell traps
- Doesn't test most proc_* functions

### test_simple_args.sh
- Name suggests a simple test
- Actually duplicates comprehensive testing done elsewhere

## 10. **Missing Error Scenarios**

### Most tests only test happy paths
- Don't test edge cases like:
  - Very long command lines
  - Special characters in arguments
  - Concurrent execution
  - Signal handling
  - Resource exhaustion

## 11. **No Test Documentation**
- Most test files lack comments explaining:
  - What they're testing
  - Why it matters
  - Expected behavior
  - Known limitations

## Recommendations:
1. Fix the variable name bug in proc_trap implementation
2. Consolidate redundant tests (keep test_lib_args.sh, remove others)
3. Add proper cleanup handlers to all tests that create processes/files
4. Replace sleep with proper wait loops
5. Make test_configure_success.sh actually test something
6. Add consistent test output format
7. Run all tests in subshells for isolation
8. Add test documentation headers
9. Remove or improve minimal tests
10. Use consistent patterns for exit codes and error handling
