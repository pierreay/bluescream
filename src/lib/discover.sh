# * About

# Library used to discover the setup on the system.

# * Functions

# Print the found devices in our hardware setup. (Do not return test value for
# their presence).
function discover_setup() {
    # SDRs using SoapySDR.
    echo "=== SDR ==="
    echo "BladeRF: " && SoapySDRUtil --probe="driver=bladerf" >/dev/null 2>&1 | grep get_serial
    echo "USRP: "    && SoapySDRUtil --probe="driver=uhd"     2>/dev/null     | grep mboard_serial
    # J-Link OB from nRF52 DK.
    echo "=== nRF52 DK ==="
    nrfjprog --com | grep VCOM0
    # HCI dongle for Mirage.
    echo "=== HCI ==="
    whadup | grep hci
    # Butterfly on nRF52 dongle for WHAD.
    echo "=== Butterfly ==="
    whadup | grep uart
}

# If $1 is an HCI device IFNAME, then echo it, otherwise echo the first one
# found.
function select_hci() {
    if [[ -z ${1+x} ]]; then
        find_hci
    else
        echo $1
    fi
}

# Echo the IFNAME of the first HCI device found.
function find_hci() {
    hciconfig | head -n 1 | cut -f 1 -d ":"
}

# Echo the ADDRESS of the first HCI device found.
function find_hci_addr() {
    hciconfig | sed '2q;d' | awk '{print $(3)}'
}

function find_nrf_com() {
     nrfjprog --com | cut - -d " " -f 5
}
