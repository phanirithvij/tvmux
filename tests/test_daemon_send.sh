#!/bin/bash
# Test daemon_send client function

tmpdir=$(mktemp -d)
trap "rm -rf '$tmpdir'" EXIT

# Create a simple echo server using perl
socket_path="$tmpdir/test.sock"
perl -e "$DAEMON_PERL_USE" -e '
    my $server = IO::Socket::UNIX->new(
        Type => SOCK_STREAM,
        Local => $ARGV[0],
        Listen => 5
    ) or die "$!\n";

    my $client = $server->accept();
    my $data = <$client>;
    chomp $data;
    print $client "RECEIVED: $data\n";
    close($client);
    close($server);
' "$socket_path" &
server_pid=$!

# Wait for socket
while [[ ! -S "$socket_path" ]]; do
    sleep 0.1
done

# Test sending command directly with perl
result=$(perl -e "$DAEMON_PERL_USE $DAEMON_PERL_CLIENT" "$socket_path" "test command")

# Cleanup
kill $server_pid 2>/dev/null || true
wait $server_pid 2>/dev/null || true

[[ "$result" == "RECEIVED: test command" ]]
