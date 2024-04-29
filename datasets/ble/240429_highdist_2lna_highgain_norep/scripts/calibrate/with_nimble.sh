#!/bin/bash

# * Environment

env="$(realpath $(dirname $0))/../env.sh"
echo "INFO: Source file: $env"
source "$env"

# Safety-guard.
if [[ -z $ENV_FLAG ]]; then
    echo "ERROR: Environment can't been sourced!"
    exit 1
fi

# * Global variables

# ** Script configuration

# *** Paths and addresses

# Bluetooth address of the Nimble board target.
NIMBLE_ADDR="C2:3E:54:84:5C:4C"

# *** Parameters

# Should we enable AES repetitions?
AES_REPETITIONS=1

# *** Actions

# Reset YKush switch at beginning.
RESET_YKUSH=1
# Extract instead of plotting whole capture.
EXTRACT=1
# Plot extraction result.
EXTRACT_PLOT=1
# Kill radio already running and at the end.
KILL_RADIO=1

# ** Internals

CONTINUE_FLAG=1

CONFIG_PATH="/tmp/config.toml"

NRF_PATH="" # NOTE: Initialized by find_nrf().
HCI_ADDR="" # NOTE: Initialized by find_hci().

LOG_PATH="$DATASET_PATH/logs/calibrate_nimble.log"

# * Functions

function find_hci() {
    HCI_ADDR=$(hciconfig | sed '2q;d' | awk '{print $(3)}')
    echo "INFO: Found HCI at: $HCI_ADDR"
}

function find_nrf() {
    NRF_PATH=$(nrfjprog --com | cut - -d " " -f 5)
    echo "INFO: Found nRF at: $NRF_PATH"
}

function reset_ykush() {
    echo "INFO: Shutdown YKush switch..."
    sudo ykushcmd -d a
    sleep 1
    sudo ykushcmd -u a
    sleep 3
    echo "DONE!"
}

function flash_firmware_once() {
    firmware_src="/tmp/mynewt-firmware.hex"
    firmware_dst="${DATASET_PATH}/bin/nimble.hex"
    if [[ -f "${firmware_dst}" ]]; then
        echo "SKIP: Flash firmware: File exists: ${firmware_dst}"
        return 0
    fi

    if [[ ${AES_REPETITIONS} -eq 0 ]]; then
        checkout_root="light"
        checkout_sub="light"
    else
        checkout_root="main"
        checkout_sub="master"
    fi
    echo "INFO: Checkout ${checkout_root} -> $NIMBLE"
    cd $NIMBLE/repos/apache-mynewt-core && git checkout ${checkout_sub}
    cd $NIMBLE/repos/apache-mynewt-nimble && git checkout ${checkout_sub}
    cd $NIMBLE && git checkout ${checkout_root}

    echo "INFO: Compile and flash Nimble firmware..."
    cd $NIMBLE && make all

    echo "INFO: Save firmware: ${firmware_src} -> ${firmware_dst}"
    mkdir -p "$(dirname "$firmware_dst")" && cp "${firmware_src}" "${firmware_dst}"
    echo "DONE!"    
}

function init_git() {
    echo "INFO: Checkout main -> $SC_SRC"
    (cd $SC_SRC && git checkout main)
}

function init_tmp_dataset() {
    if [[ ${AES_REPETITIONS} -eq 0 ]]; then
        (cd $SC_SRC && ./dataset.py init /tmp ${FS} --input-gen-run --input-src-pairing --nb-trace-wanted-train 10 --nb-trace-wanted-attack 5 --force)
    else
        (cd $SC_SRC && ./dataset.py init /tmp ${FS} --input-gen-run --input-src-serial --nb-trace-wanted-train 10 --nb-trace-wanted-attack 5 --force)
    fi
}

function init_radio_if_needed() {
    if [[ $KILL_RADIO == 1 ]]; then
        kill_radio
        sleep 1
    fi
    pgrep radio
    if [[ $? == 1 ]]; then
        (cd $SC_SRC && ./radio.py --dir /tmp --loglevel DEBUG listen 128e6 ${FC} ${FS} --nf-id -1 --ff-id 0 --duration=2 --gain $GAIN &)
        sleep 4
    fi
}

function kill_radio() {
    pkill radio.py
    echo "INFO: Radio killed!"
}

function init_config() {
    rm -f $CONFIG_PATH
    cp $SC_SRC/config.toml $CONFIG_PATH
}

# Example:
# config "$CONFIG_PATH" "trg_bp_low" "[0.5e6]"
function config() {
    config_file="$1"
    param_name="$2"
    param_value="$3"
    echo "${config_file}: ${param_name}=${param_value}"
    sed -i "s/${param_name} = .*/${param_name} = ${param_value}/g" "${config_file}"
}

function instrument() {
    if [[ ${AES_REPETITIONS} -eq 0 ]]; then
        config="fast"
    else
        config="slow"
    fi
    (cd $SC_SRC && ./radio.py --dir /tmp --config $CONFIG_PATH instrument /tmp train ${HCI_ADDR} ${NIMBLE_ADDR} ${NRF_PATH} --idx 0 --config ${config})
    ret=$?
    echo "INFO: ret=$ret?"
    if [[ "$ret" != 0 ]]; then
        CONTINUE_FLAG=0
    fi
}

function plot() {
    (cd $SC_SRC && ./radio.py --dir /tmp plot-file ${FS} /tmp/raw_0_0.npy --freq ${FC})
}

function extract() {
    plot_flag="--plot"
    if [[ $EXTRACT_PLOT == 0 ]]; then
        plot_flag="--no-plot"
    fi
    if [[ ${AES_REPETITIONS} -eq 0 ]]; then
        config="1_aes_ff_antenna_8msps"
    else
        config="300_aes"
    fi
    (cd $SC_SRC && ./radio.py --dir /tmp --config $CONFIG_PATH extract ${FC} ${FS} 0 $plot_flag --no-overwrite --no-exit-on-error --config ${config} --save-plot="$DATASET_PATH/plots/calibrate_nimble" )
    echo "INFO: ret=$?"
}

function capture() {
    flash_firmware_once

    init_tmp_dataset

    init_radio_if_needed

    init_config

    config "$CONFIG_PATH" "accept_snr_min" "5.0"
    config "$CONFIG_PATH" "more_data_bit" "1"
    config "$CONFIG_PATH" "hop_interval" "15"
    config "$CONFIG_PATH" "procedure_interleaving" "false"
    config "$CONFIG_PATH" "ll_enc_req_conn_event" "4"
    config "$CONFIG_PATH" "trg_bp_low" "[1.0e6]"
    config "$CONFIG_PATH" "trg_bp_high" "[1.9e6]"

    instrument
}

function analyze() {
    if [[ $EXTRACT == 1 ]]; then
        extract
    else
        plot
    fi
}

function init_log() {
    clear
    mkdir -p "$(dirname ${LOG_PATH})"
    mkdir -p "$DATASET_PATH/plots"
}

function save_log() {
    tmux capture-pane -pS - > "${LOG_PATH}"
}

# * Steps

# Safety-guard.
if [[ -f "${LOG_PATH}" ]]; then
    echo "SKIP: Log file exist: ${LOG_PATH}"
    exit 0
fi

init_log

init_git

find_nrf
find_hci

if [[ $RESET_YKUSH == 1 ]]; then
    reset_ykush
fi

capture

if [[ $CONTINUE_FLAG == 1 ]]; then
    analyze
fi

if [[ $KILL_RADIO == 1 ]]; then
    kill_radio
fi

save_log
