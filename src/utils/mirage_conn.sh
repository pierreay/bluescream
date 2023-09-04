#!/bin/bash

set -e

help() {
    cat << EOF
Usage: conn.sh BD_ADDR HCI_IFNAME
Connect with the BLE device at address BD_ADDR using the HCI dongle of interface HCI_IFNAME.
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

if [[ ! -f /tmp/mirage_output_ltk || ! -f /tmp/mirage_output_rand || ! -f /tmp/mirage_output_ediv ]]; then
    echo "Use mirage_pair.sh before to use conn.sh!"
    exit 1
fi

ltk=$(cat /tmp/mirage_output_ltk)
rand=$(cat /tmp/mirage_output_rand)
ediv=$(cat /tmp/mirage_output_ediv)

echo "Connect to confirm pairing success"
sudo -E mirage ble_master SCENARIO=ble_basic_master_encrypted INTERFACE=$hci_ifname TARGET=$bd_addr CONNECTION_TYPE=random LTK=$ltk RAND=$rand EDIV=$ediv
