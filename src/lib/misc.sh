# * About

# Miscellaneous functions used across bash scripts.

# * Load

source ./lib/discover.sh

# * Functions

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
