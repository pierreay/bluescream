#!/bin/bash

set -e

help() {
    cat << EOF
Usage: mirage_pair.sh BD_ADDR HCI_IFNAME
Pair with the BLE device at address BD_ADDR using the HCI dongle of interface HCI_IFNAME.
EOF
}

if [[ $# -lt 2 ]]; then
    help
    exit 1
fi

bd_addr=$1
echo "bd_addr=$1"
hci_ifname=$2
echo "hci_ifname=$2"

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
