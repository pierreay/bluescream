#!/bin/bash

# * About

# Deprecated script using Mirage to pair a device and export important
# information.

# * External interface

function pair() {
    timeout 30 ./utils/mirage_pair.sh "$ENVRC_VICTIM_ADDR" | tee /tmp/mirage_pair_output
    if [[ $? -ge 1 ]]; then
        return 1
    fi
    grep FAIL /tmp/mirage_pair_output >/dev/null 2>&1
    return $(( 1 - $? ))
}

# * Script

set -e
source ./lib/misc.sh

help() {
    cat << EOF
Usage: mirage_pair.sh BD_ADDR [HCI_IFNAME]
Pair with the BLE device at address BD_ADDR.
If specified, it uses the HCI dongle of interface HCI_IFNAME, otherwise, the first one found.
EOF
}

if [[ $# -lt 1 ]]; then
    help
    exit 1
fi

bd_addr=$1
hci_ifname=$(select_hci $2)
echo "bd_addr=$bd_addr"
echo "hci_ifname=$hci_ifname"

# Pair.
sudo -E mirage "ble_connect|ble_pair" ble_connect1.INTERFACE=$hci_ifname ble_connect1.TARGET=$bd_addr ble_connect1.CONNECTION_TYPE=random | tee /tmp/mirage_output
tail -6 /tmp/mirage_output
ltk=$(tail -6 /tmp/mirage_output | grep "(LTK)" | awk '{print $8}')
rand=$(tail -6 /tmp/mirage_output | grep "rand=" | awk '{print $9}' | sed "s/rand=//g")
ediv=$(tail -6 /tmp/mirage_output | grep "rand=" | awk '{print $11}' | sed "s/ediv=//g")
addr=$(hciconfig | sed '2q;d' | awk '{print $(3)}')
echo $ltk > /tmp/mirage_output_ltk
echo $rand > /tmp/mirage_output_rand
echo $ediv > /tmp/mirage_output_ediv
echo $addr > /tmp/mirage_output_addr
