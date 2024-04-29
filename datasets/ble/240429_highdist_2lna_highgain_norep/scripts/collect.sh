#!/bin/bash

# * Environment

env="$(realpath $(dirname $0))/env.sh"
echo "INFO: Source file: $env"
source "$env"

# Safety-guard.
if [[ -z $ENV_FLAG ]]; then
    echo "ERROR: Environment can't been sourced!"
    exit 1
fi

# * Variables

# Should we enable AES repetitions?
AES_REPETITIONS=1

# ** Screaming Channels .envrc

export ENVRC_VICTIM_PORT="$(nrfjprog --com | cut - -d " " -f 5)"
export ENVRC_SAMP_RATE=${FS}
export ENVRC_DURATION=0.2
export ENVRC_GAIN=${GAIN}
export ENVRC_WANTED_TRACE_TRAIN=16000
export ENVRC_WANTED_TRACE_ATTACK=16000
export ENVRC_NF_FREQ=128000000 # 128e6
export ENVRC_FF_FREQ=${FC}
export ENVRC_RADIO_DIR="$HOME/storage/tmp"
export ENVRC_DATASET_RAW_PATH="${DATASET_PATH}/raw"
export ENVRC_DATASET_AVG_PATH="${DATASET_PATH}/avg"
export ENVRC_DATASET_EXT_PATH="${DATASET_PATH}/ext"
export ENVRC_NIMBLE_PATH="$HOME/git/screaming_channels_nimble"
export ENVRC_CONFIG_FILE="${DATASET_PATH}/config.toml"
export ENVRC_VICTIM_ADDR="C2:3E:54:84:5C:4C"
export ENVRC_ATTACKER_ADDR="00:19:0E:19:79:D8"
export ENVRC_NF_ID=-1
export ENVRC_FF_ID=0
if [[ ${AES_REPETITIONS} -eq 0 ]]; then
    export ENVRC_EXTRACT_CONFIG="1_aes_ff_antenna_8msps"
    export ENVRC_DEVICE_CONFIG="fast"
    export ENVRC_DATASET_INPUT="PAIRING"
else
    export ENVRC_EXTRACT_CONFIG="300_aes"
    export ENVRC_DEVICE_CONFIG="slow"
    export ENVRC_DATASET_INPUT="SERIAL"
fi

# * Functions

function init_config() {
    rm -f $ENVRC_CONFIG_FILE
    cp $SC_SRC/config.toml $ENVRC_CONFIG_FILE
}

# Example:
# config "$ENVRC_CONFIG_FILE" "trg_bp_low" "[0.5e6]"
function config() {
    config_file="$1"
    param_name="$2"
    param_value="$3"
    echo "${config_file}: ${param_name}=${param_value}"
    sed -i "s/${param_name} = .*/${param_name} = ${param_value}/g" "${config_file}"
}

# * Script

# ** Collection

echo "INFO: Checkout main -> $SC_SRC"
(cd $SC_SRC && git checkout main)

init_config

config "$ENVRC_CONFIG_FILE" "accept_snr_min" "2.0"
config "$ENVRC_CONFIG_FILE" "more_data_bit" "1"
config "$ENVRC_CONFIG_FILE" "hop_interval" "15"
config "$ENVRC_CONFIG_FILE" "procedure_interleaving" "false"
config "$ENVRC_CONFIG_FILE" "ll_enc_req_conn_event" "4"
config "$ENVRC_CONFIG_FILE" "trg_bp_low" "[1.0e6]"
config "$ENVRC_CONFIG_FILE" "trg_bp_high" "[1.9e6]"

mkdir -p ${ENVRC_DATASET_RAW_PATH}
if [[ -f ${ENVRC_DATASET_RAW_PATH}/.collect_done ]]; then
    echo "SKIP: Collection: File exists: ${ENVRC_DATASET_RAW_PATH}/.collect_done"
else
    (cd $SC_SRC && ./collect.sh -l INFO -y)
    touch ${ENVRC_DATASET_RAW_PATH}/.collect_done
fi

# ** Post-processing

# *** Averaging

function average_subset() {
    subset="$1"
    force="--force"
    flag_path="${ENVRC_DATASET_AVG_PATH}/.average_${subset}_done"
    if [[ -f "$flag_path" ]]; then
        echo "SKIP: Averaging: File exists: $flag_path"
    else
        (cd $SC_SRC && ./dataset.py --loglevel INFO average --nb-aes 300 ${ENVRC_DATASET_RAW_PATH} ${ENVRC_DATASET_AVG_PATH} ${subset} --template 1 --no-plot --stop -1 ${force} --jobs=-1)
        touch "${flag_path}"
    fi    
}

if [[ ${AES_REPETITIONS} -eq 1 ]]; then
    mkdir -p ${ENVRC_DATASET_AVG_PATH}
    average_subset train
    average_subset attack
fi

# *** Extracting

function extract_subset() {
    subset="$1"
    force="--force"
    flag_path="${ENVRC_DATASET_EXT_PATH}/.extract_${subset}_done"
    if [[ -f "$flag_path" ]]; then
        echo "SKIP: Averaging: File exists: $flag_path"
    else
        (cd $SC_SRC && ./dataset.py --loglevel INFO extract --nb-aes 300 ${ENVRC_DATASET_RAW_PATH} ${ENVRC_DATASET_EXT_PATH} ${subset} --template 1 --idx 1 --no-plot --stop -1 ${force} --jobs -1 --window 0)
        touch "${flag_path}"
    fi    
}

if [[ ${AES_REPETITIONS} -eq 1 ]]; then
    mkdir -p ${ENVRC_DATASET_EXT_PATH}
    extract_subset attack
fi
