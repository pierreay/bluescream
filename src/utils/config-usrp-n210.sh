#!/bin/bash

USRPN210_IFNAME="enp0s20f0u4"

# Unmanage the interface using NetworkManager.
nmcli device set $(USRPN210_IFNAME) managed no
# Configure host's network interface.
sudo ip addr add 10.0.3.39/24 dev $(USRPN210_IFNAME)
# Ping USRP network interface.
ping -c 4 10.0.3.40

