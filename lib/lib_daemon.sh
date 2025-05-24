#!/bin/bash
# Daemon management functions

# shellcheck disable=SC2016 # Perl code stored as literal strings - no shell expansion needed
DAEMON_PERL_USE='use IO::Socket::UNIX; use IO::Select;'

DAEMON_PERL_CREATE_SOCKET='
sub create_socket {
    my ($path) = @_;
    unlink $path;
    my $dir = $path;
    $dir =~ s|/[^/]+$||;
    mkdir $dir unless -d $dir;
    return IO::Socket::UNIX->new(
        Type => SOCK_STREAM,
        Local => $path,
        Listen => 5
    ) or die "Cannot create socket at $path: $!\n";
}'

DAEMON_PERL_HANDLE_NEW_CLIENT='
sub handle_new_client {
    my ($server, $select, $clients, $next_fid_ref) = @_;
    my $client = $server->accept();
    return unless $client;
    $clients->{$$next_fid_ref} = $client;
    $select->add($client);
    $$next_fid_ref++;
}'

DAEMON_PERL_HANDLE_CLIENT_DATA='
sub handle_client_data {
    my ($fh, $select, $clients) = @_;
    my $fid = (grep { $clients->{$_} == $fh } keys %$clients)[0];
    return unless defined $fid;
    my $data = <$fh>;
    if (!defined $data) {
        $select->remove($fh);
        delete $clients->{$fid};
        close $fh;
        return;
    }
    chomp $data;
    print "$fid:$data\n";
}'

DAEMON_PERL_MAIN_LOOP='
my $server = create_socket($ARGV[0]);
my $select = IO::Select->new($server);
my %clients;
my $next_fid = 1;

while (1) {
    for my $fh ($select->can_read(0.1)) {
        if ($fh == $server) {
            handle_new_client($server, $select, \%clients, \$next_fid);
        } else {
            handle_client_data($fh, $select, \%clients);
        }
    }
}'

daemon_loop() {
    local socket_path="$1"
    perl -e "$DAEMON_PERL_USE
             $DAEMON_PERL_CREATE_SOCKET
             $DAEMON_PERL_HANDLE_NEW_CLIENT
             $DAEMON_PERL_HANDLE_CLIENT_DATA
             $DAEMON_PERL_MAIN_LOOP" "$socket_path"
}

daemon_start() {
    local loop_cmd="${1:-daemon_loop}"
    local socket_path="/tmp/tvmux.$USER/daemon.$$.sock"

    # Run loop command (real or test)
    $loop_cmd "$socket_path" | while IFS=: read -r fid cmd args; do
        if declare -f "daemon_on_$cmd" >/dev/null; then
            "daemon_on_$cmd" $args >&"$fid"
        else
            log_error "Unknown daemon command: $cmd"
        fi
    done &

    local daemon_pid=$!
    tmux set-environment TVMUX_DAEMON_PID "$daemon_pid"
    tmux set-environment TVMUX_DAEMON_SOCKET "$socket_path"

    proc_trap "proc_kill $daemon_pid; rm -f $socket_path"
}

daemon_get_socket() {
    local pid
    local socket

    pid=$(tmux show-environment TVMUX_DAEMON_PID 2>/dev/null | cut -d= -f2)
    socket=$(tmux show-environment TVMUX_DAEMON_SOCKET 2>/dev/null | cut -d= -f2)

    # Check if daemon is healthy
    if [[ -n "$pid" ]] && [[ -n "$socket" ]]; then
        if kill -0 "$pid" 2>/dev/null && [[ -S "$socket" ]]; then
            echo "$socket"
            return 0
        fi
    fi

    # Cleanup stale state
    if [[ -n "$pid" ]] && ! kill -0 "$pid" 2>/dev/null; then
        # PID exists but process is dead
        proc_kill "$pid" 2>/dev/null || true
    fi

    if [[ -n "$socket" ]] && [[ -e "$socket" ]] && { [[ -z "$pid" ]] || ! kill -0 "$pid" 2>/dev/null; }; then
        # Socket exists but no valid PID
        rm -f "$socket"
    fi

    # Clear tmux variables
    tmux set-environment -u TVMUX_DAEMON_PID 2>/dev/null || true
    tmux set-environment -u TVMUX_DAEMON_SOCKET 2>/dev/null || true

    echo ""
    return 1
}

# Example daemon command handlers
daemon_on_status() {
    echo "running"
}

daemon_on_echo() {
    echo "$*"
}
