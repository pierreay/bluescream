# * About

# Miscellaneous functions used across bash scripts.

# * Load

source ./lib/discover.sh

# * Bash helper

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

# * Firmware

# Compile and flash the Nimble firmware from another git repository.
function firmware_compile_flash() {
    (cd ~/git/screaming_channels_nimble && make all)
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

# * Environment / Setup

# Reset devices connected to YepKit YKush USB hub.$
# $1 set to 1 perform the reset, otherwise, ignore and log warn [default = 1]
function ykush_reset() {
    if [[ ${1-1} == 1 ]]; then
        # Test that ykushcmd is available, otherwise, return immediately.
        if ! type ykushcmd &> /dev/null; then
            log_warn "Skip ykush reset because ykushcmd is not available!"
            return 1
        fi
        log_info
        log_info "=========== YKUSH RESET ==========="
        log_info
        log_info "Power off YKush..."
        sudo ykushcmd -d a
        sleep 5 # Wait for shutdown.
        log_info "Power on YKush..."
        sudo ykushcmd -u a
        sleep 10 # Wait for power-up and booting.
        log_info "YKush reset done!"
    else
        log_warn "Skip ykush reset because it is not enabled!"
    fi
}

# * Dataset

# Display a tree of a dataset.
# $1 is the path of the dataset [default = $ENVRC_DATASET_RAW_PATH]
function dataset_tree() {
    tree -alh -I "??_trace_ff.npy" -I "???_trace_ff.npy" -I "????_trace_ff.npy" -I "?????_trace_ff.npy" \
              -I "??_trace_nf.npy" -I "???_trace_nf.npy" -I "????_trace_nf.npy" -I "?????_trace_nf.npy" \
              ${1-$ENVRC_DATASET_RAW_PATH}
    echo "Number of npy files in train  : $(ls ${1-$ENVRC_DATASET_RAW_PATH}/train | grep '.*.npy' | wc -l)"
    echo "Number of npy files in attack : $(ls ${1-$ENVRC_DATASET_RAW_PATH}/attack | grep '.*.npy' | wc -l)"
}
