# Miscellaneous functions used across bash scripts.

# NOTE: DEPRECATED
function pair() {
    timeout 30 ./utils/mirage_pair.sh "$ENVRC_VICTIM_ADDR" | tee /tmp/mirage_pair_output
    if [[ $? -ge 1 ]]; then
        return 1
    fi
    grep FAIL /tmp/mirage_pair_output >/dev/null 2>&1
    return $(( 1 - $? ))
}

# Initialize a dataset in $1 using sample rate $2. Silently do nothing if
# dataset already exists.
function dataset_init() {
    if [[ ! -f $1/dataset.pyc ]]; then
        log_info "Initialize a dataset in $ENVRC_DATASET_RAW_PATH"
        ./dataset.py init $1 $2 --input-gen-init --nb-trace-wanted-train 65536 --nb-trace-wanted-attack 16384
    fi
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
