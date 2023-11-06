# Miscellaneous functions used across bash scripts.

# Compile and flash the Nimble firmware from another git repository.
function firmware_compile_flash() {
    (cd ~/git/screaming_channels_nimble && make all)
}

# Evaluate a step depending on the chosen mode (incremental or equal).
# If $1 is set to "equal", return 1 (and echo 1) if $2 is equal $3.
# If $1 is set to "incr",  return 1 (and echo 1) if $2 is greater or equal $3.
# Otherwise, return 0 and echo nothing.
function eval_cond() {
    if [[ $1 == "equal" && $2 -eq $3 || $1 == "incr" && $2 -ge $3 ]]; then
        echo 1
        return 1
    fi
    return 0
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

# Usage: firmware_set_mode [train | attack] >/dev/null 2>&1
function firmware_set_mode() {
    script=/tmp/script.minicom
    cat << EOF > $script
send mode_$1
! killall -9 minicom
EOF
    minicom -D $(find_nrf_com) -S $script >/dev/null 2>&1 &
    sleep 3
}
