#!/bin/bash
# Test daemon socket creation with directory creation

tmpdir=$(mktemp -d)
trap "rm -rf '$tmpdir'" EXIT

test_socket="$tmpdir/subdir/daemon.sock"

# Test that create_socket creates parent directory
result=$(perl -e "$DAEMON_PERL_USE $DAEMON_PERL_CREATE_SOCKET" -e '
    my $socket = create_socket($ARGV[0]);
    my $dir = $ARGV[0];
    $dir =~ s|/[^/]+$||;
    if (-d $dir && $socket && -S $ARGV[0]) {
        print "PASS";
    } else {
        print "FAIL";
    }
' "$test_socket")

[[ "$result" == "PASS" ]]
