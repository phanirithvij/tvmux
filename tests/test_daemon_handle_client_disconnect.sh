#!/bin/bash
# Test daemon handle_client_data disconnection

tmpdir=$(mktemp -d)
trap "rm -rf '$tmpdir'" EXIT

# Test that handle_client_data removes disconnected clients
result=$(perl -e "$DAEMON_PERL_USE $DAEMON_PERL_HANDLE_CLIENT_DATA" -e '
    # Create a filehandle that will return EOF
    open(my $fh, "<", \"") or die $!;

    # Mock select with tracking
    my $select = IO::Select->new();
    my $removed = 0;
    {
        no warnings "redefine";
        sub IO::Select::remove { $removed++; shift; }
    }

    # Setup clients
    my %clients = ( 99 => $fh );

    handle_client_data($fh, $select, \%clients);

    if (scalar(keys %clients) == 0 && $removed == 1) {
        print "PASS";
    } else {
        print "FAIL";
    }
')

[[ "$result" == "PASS" ]]
