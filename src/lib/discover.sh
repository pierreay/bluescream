# * About

# Library used to discover the setup on the system.

# * Functions

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
