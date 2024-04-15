#!/bin/bash

# * Global variables

# ** Script configuration

# *** Paths and addresses

# Path of current dataset.
DATASET_PATH="$REPO_DATASET_PATH/240414_1-leak-pairing-highdist-fix-2.533e9-8e6_raw"

# Bluetooth address of the Nimble board target.
NIMBLE_ADDR="C2:3E:54:84:5C:4C"

# *** Parameters

# Center frequency.
FC=2.533e9
# Sampling rate.
FS=8e6
# Gain [dB].
GAIN=66
# Bandpass filter for trigger signal. NOTE: Depends on sampling rate.
# TRG_BP_LOW="[1.0e6]"
# TRG_BP_HIGH="[1.9e6]"
# Minimum accepted SNR.
ACCEPT_SNR_MIN=11.0

# *** Actions

# Reflash the firmware at beginning.
REFLASH=1
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

function compile_firmware() {
    echo "INFO: Checkout f879eff -> $NIMBLE"
    cd $NIMBLE
    git checkout f879eff
    make all
}

function init_git() {
    echo "INFO: Checkout afc99e7 -> $SC_SRC"
    (cd $SC_SRC && git checkout afc99e7)
}

function init_tmp_dataset() {
    (cd $SC_SRC && ./dataset.py init /tmp ${FS} --input-gen-run --input-src-pairing --nb-trace-wanted-train 10 --nb-trace-wanted-attack 5 --force)
}

function init_radio_if_needed() {
    if [[ $KILL_RADIO == 1 ]]; then
        kill_radio
        sleep 1
    fi
    pgrep radio
    if [[ $? == 1 ]]; then
        (cd $SC_SRC && ./radio.py --dir /tmp --loglevel DEBUG listen 128e6 ${FC} ${FS} --nf-id -1 --ff-id 0 --duration=0.2 --gain $GAIN &)
        sleep 3
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
    (cd $SC_SRC && ./radio.py --dir /tmp --config $CONFIG_PATH instrument /tmp train ${HCI_ADDR} ${NIMBLE_ADDR} ${NRF_PATH} --idx 0 --config fast)
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
    (cd $SC_SRC && ./radio.py --dir /tmp --config $CONFIG_PATH extract ${FC} ${FS} 0 $plot_flag --no-overwrite --no-exit-on-error --config 1_aes_ff_antenna_8msps --save-plot="$DATASET_PATH/plots/calibrate_nimble" )
    echo "INFO: ret=$?"
}

function capture() {
    if [[ $REFLASH == 1 ]]; then
        compile_firmware
    fi

    init_tmp_dataset

    init_radio_if_needed

    init_config
    config "$CONFIG_PATH" "accept_snr_min" "${ACCEPT_SNR_MIN}"
    config "$CONFIG_PATH" "more_data_bit" "1"
    config "$CONFIG_PATH" "hop_interval" "15"
    config "$CONFIG_PATH" "procedure_interleaving" "false"
    config "$CONFIG_PATH" "ll_enc_req_conn_event" "4"
    # config "$CONFIG_PATH" "trg_bp_low" "${TRG_BP_LOW}"
    # config "$CONFIG_PATH" "trg_bp_high" "${TRG_BP_HIGH}"

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
    mkdir -p "$DATASET_PATH/logs"
    mkdir -p "$DATASET_PATH/plots"
}

function save_log() {
    tmux capture-pane -pS - > "$DATASET_PATH/logs/calibrate_nimble.log"
}

# * Steps

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
