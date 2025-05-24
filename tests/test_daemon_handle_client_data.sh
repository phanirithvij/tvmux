#!/bin/bash
# Test daemon handle_client_data with valid data

tmpdir=$(mktemp -d)
trap "rm -rf '$tmpdir'" EXIT

# Test that handle_client_data outputs fid:command
result=$(perl -e "$DAEMON_PERL_USE $DAEMON_PERL_HANDLE_CLIENT_DATA" -e '
    # Create a real filehandle from a string
    open(my $fh, "<", \"echo hello\n") or die $!;

    # Mock select and clients
    my $select = IO::Select->new();
    my %clients = ( 42 => $fh );

    handle_client_data($fh, $select, \%clients);
    close($fh);
')

[[ "$result" == "42:echo hello" ]]
