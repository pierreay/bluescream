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
Set -r to reboot computer on repeated errors. Ignored if key is fixed in target device [default = False]
Set -y to reset YKush switch on repeated errors. Ignored if key is fixed in target device [default = False]
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
REBOOT_LIM=9

# Counter of events (e.g. failures) before YKush reset.
YKUSH_CTR=0
# Limit of events before YKush reset.
YKUSH_LIM=3

# * Subset

# ** Functions

function collect_train() {
    export COLLECT_NB="$ENVRC_WANTED_TRACE_TRAIN"
    export SUBSET_WD="$ENVRC_DATASET_RAW_PATH/train"
    export KEY_FIXED=0
    export COLLECT_MODE=train
    log_info
    log_info "=========== Training set ==========="
    log_info
    collect_one_set
}

function collect_attack() {
    export COLLECT_NB="$ENVRC_WANTED_TRACE_ATTACK"
    export SUBSET_WD="$ENVRC_DATASET_RAW_PATH/attack"
    export KEY_FIXED=1
    export COLLECT_MODE=attack
    log_warn "Unconditionally disable YKush resetting and rebooting for fixed key!"
    export OPT_REBOOT=0
    export OPT_YKUSH=0
    log_info
    log_info "=========== Attack set ==========="
    log_info
    collect_one_set
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
    ykush_reset $OPT_YKUSH
    # Print and find our hardware setup.
    discover_setup
    # Make sure the dataset is initialized.
    dataset_init $ENVRC_DATASET_RAW_PATH $ENVRC_SAMP_RATE
    # Initialize the radio daemon.
    radio_init 40 $OPT_LOGLEVEL
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

# If an error has occurred during last function, switch YKush and/or reboot if
# needed. Otherwise, reset the error counters.
function check_errors() {
    # Check the return code of the last function.
    ret=$?
    if [[ $ret != 0 ]]; then
        ykush_reset_if_needed
        reboot_if_needed
    else
        reset_error_counters
    fi
    return $ret
}

# Reset the counters used for rebooting and resetting. Meant to be called after
# a successful recording.
function reset_error_counters() {
    REBOOT_CTR=0
    YKUSH_CTR=0
}

function ykush_reset_if_needed() {
    if [[ $OPT_YKUSH == 1 ]]; then
        # Reset if needed.
        if [[ $YKUSH_CTR -ge $YKUSH_LIM ]]; then
            ykush_reset $OPT_YKUSH
        fi
        # Update counter
        YKUSH_CTR=$(( $YKUSH_CTR + 1 ))
    fi
}

function reboot_if_needed() {
    if [[ $OPT_REBOOT == 1 ]]; then
        # Reboot if needed.
        if [[ $REBOOT_CTR -ge $REBOOT_LIM ]]; then
            sudo reboot
        fi
        # Update counter
        REBOOT_CTR=$(( $REBOOT_CTR + 1 ))
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
    # Make sure output directory is created (/attack or /train) or do nothing
    # when resuming.
    mkdir -p $SUBSET_WD
    # Clean subset directory if asked to restart, or set the start index based
    # on previous recordings.
    i_start=0
    if [[ $OPT_RESTART == 1 ]]; then
        clean
    else
        resume
    fi
    SECONDS=0

    for (( i = i_start; i < $COLLECT_NB; i++ ))
    do
        log_info
        log_info "=========== TRACE #$i -- KEY_FIXED=$KEY_FIXED -- SUBSET=$COLLECT_MODE ==========="
        log_info

        # Instrument and record.
        radio_instrument $OPT_LOGLEVEL $COLLECT_MODE $i
        check_errors
        if [[ $? != 0 ]]; then
            log_warn "Restart the current recording!"
            i=$(( $i - 1 ))
            continue
        fi

        # Extract the signal from the recording.
        radio_extract $OPT_LOGLEVEL --no-plot --overwrite --exit-on-error
        check_errors
        if [[ $? != 0 ]]; then
            log_warn "Restart the current recording!"
            i=$(( $i - 1 ))
            continue
        fi

        # If success, save the extraction.
        radio_save

        # Safety-restart.
        if [[ $(( ($i+1) % 200 )) == 0 ]]; then
            log_warn "Restart devices every 200 traces to prevent errors..."
            ykush_reset $OPT_YKUSH
        fi
    done
}

# * Script

init
collect_train
collect_attack
quit
