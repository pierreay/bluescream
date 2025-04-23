#!/bin/bash

# * Variables

NRF_PATH="" # NOTE: Initialized by find_nrf().

# * Functions

function find_nrf() {
    NRF_PATH=$(nrfjprog --com | cut - -d " " -f 5)
    echo "INFO: Found nRF at: $NRF_PATH"
}

function compile_flash_firmware() {
    cd $SC_POC/firmware
    git checkout 276e0c4
    direnv exec . make -C pca10040/blank/armgcc flash
}

function start_tx() {
    script=/tmp/script.minicom
    cat << EOF > $script
send a
send 02
send o
! killall -9 minicom
EOF
    minicom -D ${NRF_PATH} -S $script >/dev/null 2>/dev/null &
    
}

function stop_tx() {
    script=/tmp/script.minicom
    cat << EOF > $script
send e
! killall -9 minicom
EOF
    minicom -D ${NRF_PATH} -S $script >/dev/null 2>/dev/null &
}

# * Steps

find_nrf
compile_flash_firmware
sleep 3 # NOTE: Wait firmware initialization.
start_tx

echo "INFO: Tune to 2.402 GHz and observe modulated carrier"
gqrx

stop_tx
