#!/bin/bash

set -e
source ./lib/misc.sh
source ./lib/discover.sh

help() {
    cat << EOF
Usage: conn.sh BD_ADDR [HCI_IFNAME]
Connect with the BLE device at address BD_ADDR.
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

if [[ ! -f /tmp/mirage_output_ltk || ! -f /tmp/mirage_output_rand || ! -f /tmp/mirage_output_ediv ]]; then
    echo "Use mirage_pair.sh before to use conn.sh!"
    exit 1
fi

ltk=$(cat /tmp/mirage_output_ltk)
rand=$(cat /tmp/mirage_output_rand)
ediv=$(cat /tmp/mirage_output_ediv)

echo "Connect to confirm pairing success"
sudo -E mirage ble_master SCENARIO=ble_basic_master_encrypted INTERFACE=$hci_ifname TARGET=$bd_addr CONNECTION_TYPE=random LTK=$ltk RAND=$rand EDIV=$ediv
