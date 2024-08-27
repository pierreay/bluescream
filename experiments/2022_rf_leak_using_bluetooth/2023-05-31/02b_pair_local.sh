#!/bin/bash

set -e
source .envrc

# Pair.
sudo rm -rf /tmp/mirage_output
sudo -E mirage "ble_connect|ble_pair" ble_connect1.INTERFACE=$HCI_DONGLE_IFNAME ble_connect1.TARGET=$TARGET_ADDR ble_connect1.CONNECTION_TYPE=random | tee /tmp/mirage_output
tail -6 /tmp/mirage_output
ltk=$(tail -6 /tmp/mirage_output | grep "(LTK)" | awk '{print $8}')
rand=$(tail -6 /tmp/mirage_output | grep "rand=" | awk '{print $9}' | sed "s/rand=//g")
ediv=$(tail -6 /tmp/mirage_output | grep "rand=" | awk '{print $11}' | sed "s/ediv=//g")
addr=$(hciconfig | sed '2q;d' | awk '{print $(3)}')
echo $ltk > /tmp/mirage_output_ltk
echo $rand > /tmp/mirage_output_rand
echo $ediv > /tmp/mirage_output_ediv
echo $addr > /tmp/mirage_output_addr

# Connect to confirm pairing success.
sudo -E mirage ble_master SCENARIO=ble_basic_master_encrypted INTERFACE=$HCI_DONGLE_IFNAME TARGET=$TARGET_ADDR CONNECTION_TYPE=random LTK=$ltk RAND=$rand EDIV=$ediv
