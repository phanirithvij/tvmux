#!/bin/bash
# Test daemon handle_new_client function

tmpdir=$(mktemp -d)
trap "rm -rf '$tmpdir'" EXIT

# Test that handle_new_client increments fid and adds to select
result=$(perl -e "$DAEMON_PERL_USE $DAEMON_PERL_HANDLE_NEW_CLIENT" -e '
    # Mock objects
    my $select = IO::Select->new();
    my %clients;
    my $next_fid = 1;
    my $initial_fid = $next_fid;

    # Mock server that returns a mock client
    my $mock_server = bless {}, "MockServer";
    sub MockServer::accept { return bless {}, "MockClient"; }

    # Track select->add calls
    my $added = 0;
    {
        no warnings "redefine";
        sub IO::Select::add { $added++; }
    }

    handle_new_client($mock_server, $select, \%clients, \$next_fid);

    if ($next_fid == $initial_fid + 1 &&
        scalar(keys %clients) == 1 &&
        $clients{$initial_fid} &&
        $added == 1) {
        print "PASS";
    } else {
        print "FAIL";
    }
')

[[ "$result" == "PASS" ]]
