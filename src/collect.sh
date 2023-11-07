#!/bin/bash

source ./lib/log.sh 
source ./lib/misc.sh
source ./lib/pywrap.sh

# * Arguments

# Reset getopts.
OPTIND=1

# Set Python logging level.
OPT_LOGLEVEL="INFO"
# If set to 1, instruct to reboot in case of repeated errors.
OPT_REBOOT=0
# If set to 1, instruct to switch YKush down and up in case of error.
OPT_YKUSH=0
# If set to 1, instruct to restart collection from 0.
OPT_RESTART=0

# Program's help.
function help() {
    cat << EOF
Usage: collect.sh [-l LOGLEVEL] [-r] [-y] [-f]

Run a full collection and record it inside \$ENVRC_DATASET_RAW_PATH. It will
record \$ENVRC_WANTED_TRACE_TRAIN and \$ENVRC_WANTED_TRACE_ATTACK number of
traces.

Concerning the radio, the sampling rate will be set at \$ENVRC_SAMP_RATE and
frequencies at \$ENVRC_NF_FREQ and \$ENVRC_FF_FREQ. The recording will be of
duration \$ENVRC_DURATION. You can enable the recordings for NF and FF traces
using \$ENVRC_NF_ID and \$ENVRC_FF_ID, or set it to -1 to disable this
recording. The \$ENVRC_RADIO_DIR will be used as a temporary storage for the
recordings.

Concerning the target, it will be connected using the \$ENVRC_VICTIM_ADDR
address and the inputs will be configured using the \$ENVRC_VICTIM_PORT dev
port.

Set -l to the desired Python LOGLEVEL [default = INFO].
Set -r to reboot on repeated errors [default = False]
Set -y to switch YKush on error [default = False]
Set -f to restart collection from trace #0 [default = False].
EOF
    exit 0
}

# Get the scripts arguments.
while getopts "h?l:ryf" opt; do
    case "$opt" in
        h|\?)
            help
            ;;
        l) OPT_LOGLEVEL=$OPTARG
           ;;
        r) OPT_REBOOT=1
           ;;
        y) OPT_YKUSH=1
           ;;
        f) OPT_RESTART=1
           ;;
    esac
done

# * Global variables

# Counter of events (e.g. failures) before rebooting.
REBOOT_CTR=0
# Limit of events before rebooting.
REBOOT_LIM=5

# * Subset

# ** Functions

function collect_train() {
    export COLLECT_NB="$ENVRC_WANTED_TRACE_TRAIN"
    export SUBSET_WD="$ENVRC_DATASET_RAW_PATH/train"
    export KEY_FIXED=0
    log_info
    log_info "=========== Training set ==========="
    log_info
    export COLLECT_MODE=train
    collect_one_set 2
}

function collect_attack() {
    export COLLECT_NB="$ENVRC_WANTED_TRACE_ATTACK"
    export SUBSET_WD="$ENVRC_DATASET_RAW_PATH/attack"
    export KEY_FIXED=1
    export COLLECT_MODE=attack
    log_info
    log_info "=========== Attack set ==========="
    log_info
    collect_one_set 2
}

function clean() {
    if [[ -d $SUBSET_WD ]]; then
        rm -rf $SUBSET_WD/*_trace_*.npy
        log_info "Clean traces in $SUBSET_WD"
    else
        log_error "$SUBSET_WD is not set!"
        exit 0
    fi
}

function resume() {
    # Choose which trace we should count.
    # NOTE: A better implementation would be to use the query subcommand of the
    # dataset.py file, and record last recording index directly in radio.py.
    if [[ $ENVRC_NF_ID != -1 ]]; then
        pattern="trace_nf"
    else
        pattern="trace_ff"
    fi
    # Get number of traces in current dataset.
    if [[ -d $SUBSET_WD ]]; then
        i_start=$(( $(ls $SUBSET_WD/ | grep $pattern | wc -l) - 1))
        log_info "Resume collection at i=$i_start in $SUBSET_WD"
    fi
    # If we detect -1 after resuming (hence the dataset is empty) or user ask
    # restart, set it to 0 to start from scratch.
    if [[ $i_start == -1 || $OPT_RESTART == 1 ]]; then
        i_start=0
    fi
}

# Initialize the script.
function init() {
    # Catch INT signal to properly quit the SDR.
    trap quit INT
    # NOTE: Prevent the "There is no debugger connected to the PC after reboot".
    log_warn "Reinitialize devices in default state..."
    ykush_reset
    # Print and find our hardware setup.
    discover_setup
    # Make sure the dataset is initialized.
    dataset_init $ENVRC_DATASET_RAW_PATH
    # Initialize the radio daemon.
    radio_init $OPT_LOGLEVEL
}

# Clean and quit the script.
function quit() {
    # Display time taken.
    display_time
    # Stop the radio server.
    radio_quit
    # Confirm quitting. NOTE: Useful to not loose log when launched using cron.
    read -p "press [ENTER] to quit"
    exit 0
}

function display_time() {
    duration=$SECONDS
    log_info "$(($duration / 60)) minutes ; $(($duration % 60)) seconds"
}

function ykush_reset() {
    if [[ $OPT_YKUSH == 1 ]]; then
        # Test that ykushcmd is available, otherwise, return immediately.
        if ! type ykushcmd &> /dev/null; then
            log_warn "Skip ykush reset because ykushcmd is not available!"
            return 1
        fi
        log_info
        log_info "=========== YKUSH RESET ==========="
        log_info
        log_info "power off ykush..."
        sudo ykushcmd -d a
        sleep 5 # Wait for shutdown.
        log_info "power on ykush..."
        sudo ykushcmd -u a
        sleep 10 # Wait for power-up and booting.
    else
        log_warn "Skip ykush reset because it is not enable!"
    fi
}

function reboot_if_needed() {
    if [[ $OPT_REBOOT == 1 ]]; then
        # Update counter
        REBOOT_CTR=$(( $REBOOT_CTR + 1 ))
        # Reboot if needed.
        if [[ $REBOOT_CTR -ge $REBOOT_LIM ]]; then
            sudo reboot
        fi
    fi
}

function radio_extract() {
    # NOTE: -1 here is set according to the --nf-id, --ff-id, and --id
    # specifications of the radio.py arguments.
    if [[ $ENVRC_NF_ID != -1 ]]; then
        ./radio.py --loglevel $OPT_LOGLEVEL --dir $ENVRC_RADIO_DIR extract $ENVRC_SAMP_RATE $ENVRC_NF_ID --window 0.13 --offset 0.035 --no-plot --overwrite --exit-on-error
    fi
    if [[ $ENVRC_FF_ID != -1 ]]; then
        ./radio.py --loglevel $OPT_LOGLEVEL --dir $ENVRC_RADIO_DIR extract $ENVRC_SAMP_RATE $ENVRC_FF_ID --window 0.13 --offset 0.035 --no-plot --overwrite --exit-on-error
    fi
}

function radio_save() {
    if [[ $ENVRC_NF_ID != -1 ]]; then
        cp $ENVRC_RADIO_DIR/raw_${ENVRC_NF_ID}_0.npy $SUBSET_WD/${i}_trace_nf.npy
        log_info "saved trace:"
        ls $SUBSET_WD/${i}_trace_nf.npy
    fi
    if [[ $ENVRC_FF_ID != -1 ]]; then
        cp $ENVRC_RADIO_DIR/raw_${ENVRC_FF_ID}_0.npy $SUBSET_WD/${i}_trace_ff.npy
        log_info "saved trace:"
        ls $SUBSET_WD/${i}_trace_ff.npy
    fi
}

# ** Script

function collect_one_set() {
    # * Options & Menu.
    
    i_start=0

    PS3='Please, enter your choice and press [ENTER]: '
    opts=("New collection" "Resume collection" "Quit")

    if [[ ! -z $1 ]]; then
        opt=$1
    else
        opt=
    fi

    if [[ -z "$opt" ]]; then
        select opt in "${opts[@]}"
        do
            case $opt in
                ${opts[0]})
                    clean
                    break
                    ;;
                ${opts[1]})
                    resume
                    break
                    ;;
                ${opts[2]})
                    exit
                    ;;
                *) log_error "Invalid option: $REPLY";;
            esac
        done
    else
        if [[ $opt == 1 ]]; then
            clean
        elif [[ $opt == 2 ]]; then
            resume
        else
            exit
        fi
    fi

    # * Profiling.

    SECONDS=0

    # * Collecting.

    # Make sure output directory is created (/attack or /train) or do nothing
    # if resuming.
    mkdir -p $SUBSET_WD

    for (( i = i_start; i < $COLLECT_NB; i++ ))
    do
        log_info
        log_info "=========== TRACE #$i -- KEY_FIXED=$KEY_FIXED -- SUBSET=$COLLECT_MODE ==========="
        log_info
        radio_instrument $OPT_LOGLEVEL $COLLECT_MODE $i
        if [[ $? == 1 ]]; then
            ykush_reset
            reboot_if_needed
            i=$(( $i - 1 ))
            continue
        fi
        radio_extract
        radio_save

        if [[ $(( ($i+1) % 200 )) == 0 ]]; then
            log_warn "restart devices every 200 traces to prevent errors..."
            ykush_reset
        fi
    done
}

# * Script

init
collect_train
collect_attack
quit
