#!/bin/bash
# Test daemon socket creation

tmpdir=$(mktemp -d)
trap "rm -rf '$tmpdir'" EXIT

test_socket="$tmpdir/daemon.sock"

# Test socket creation
result=$(perl -e "$DAEMON_PERL_USE $DAEMON_PERL_CREATE_SOCKET" -e '
    my $socket = create_socket($ARGV[0]);
    if ($socket && -S $ARGV[0]) {
        print "PASS";
    } else {
        print "FAIL";
    }
' "$test_socket")

[[ "$result" == "PASS" ]]
