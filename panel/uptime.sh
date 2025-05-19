#!/usr/bin/env bash
(
    date +'%A %B %d   %H:%M' | figlet -c -f smblock
    echo

    echo $(uptime -p) | figlet -c -f smblock
    echo

    disk=$(echo $(df -h / | tail -n1) | cut -d' ' -f 4)
    echo "$disk" disk free | figlet -c -f smblock

) | lolcat -f -S 30
