#!/bin/bash

# TODO: Improve script usage and reliability:
# - Implement reboot after successive ykush reset.
# - Use an argument to choose between reboot or not on failure.
# - Automatically resume if previous recording is detected.
# - Allow option to force restart (e.g. --restart).

source ./lib/log.sh 
source ./lib/misc.sh

# * Subset

# ** Functions

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
    # NOTE: A better implementation would be to use the query subcommand of the
    # dataset.py file, and record last recording index directly in radio.py.
    if [[ -d $SUBSET_WD ]]; then
        i_start=$(( $(ls $SUBSET_WD/ | grep trace_ff | wc -l) - 1))
        log_info "Resume collection at i=$i_start in $SUBSET_WD"
    fi
}

# Initialize the script.
function init() {
    # Initialize the radio server.
    radio_init INFO
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
    log_info
    log_info "=========== YKUSH RESET ==========="
    log_info
    log_info "power off ykush..."
    sudo ykushcmd -d a
    sleep 5 # Wait for shutdown.
    log_info "power on ykush..."
    sudo ykushcmd -u a
    sleep 10 # Wait for power-up and booting.
}

# Arguments:
# $1 should be the trace recording index.
function radio_record() {
    # NOTE: Send a SIGINT signal such that Python goes through the __exit__()
    # of Device class, such that WHAD/Butterfly do not finish in a bad state.
    timeout --signal=SIGINT 30 python3 ./radio.py --loglevel INFO --dir $ENVRC_RADIO_DIR instrument $ENVRC_DATASET_RAW_PATH $COLLECT_MODE $ENVRC_VICTIM_ADDR $ENVRC_VICTIM_PORT --idx $1
    if [[ $? -ge 1 ]]; then
        return 1
    fi
}

function radio_quit() {
    ./radio.py quit
}

function radio_extract() {
    if [[ $COLLECT_MODE == "train" ]]; then
        ./radio.py --loglevel INFO --dir $ENVRC_RADIO_DIR extract $ENVRC_SAMP_RATE $ENVRC_FF_ID --window 0.13 --offset 0.035 --no-plot --overwrite --exit-on-error
    elif [[ $COLLECT_MODE == "attack" ]]; then
        ./radio.py --loglevel INFO --dir $ENVRC_RADIO_DIR extract $ENVRC_SAMP_RATE $ENVRC_FF_ID --window 0.13 --offset 0.035 --no-plot --overwrite --exit-on-error
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
    trap quit INT

    # * Collecting.

    # Make sure output directory is created (/attack or /train) or do nothing
    # if resuming.
    mkdir -p $SUBSET_WD

    for (( i = i_start; i < $COLLECT_NB; i++ ))
    do
        log_info
        log_info "=========== TRACE #$i -- KEY_FIXED=$KEY_FIXED -- SUBSET=$COLLECT_MODE ==========="
        log_info
        radio_record $i
        if [[ $? == 1 ]]; then
            ykush_reset
            i=$(( $i - 1 ))
            continue
        fi
        radio_extract
        cp $ENVRC_RADIO_DIR/raw_${ENVRC_FF_ID}_0.npy $SUBSET_WD/${i}_trace_ff.npy
        log_info "saved trace:"
        ls $SUBSET_WD/${i}_trace_ff.npy

        if [[ $(( ($i+1) % 200 )) == 0 ]]; then
            log_warn "restart devices every 200 traces to prevent errors..."
            ykush_reset
        fi
    done
}

# * Dataset

init

# ** Training subset

export COLLECT_NB="$ENVRC_WANTED_TRACE_TRAIN"
export SUBSET_WD="$ENVRC_DATASET_RAW_PATH/train"
export KEY_FIXED=0
log_info
log_info "=========== Training set ==========="
log_info
export COLLECT_MODE=train
collect_one_set 2

# ** Attack subset

export COLLECT_NB="$ENVRC_WANTED_TRACE_ATTACK"
export SUBSET_WD="$ENVRC_DATASET_RAW_PATH/attack"
export KEY_FIXED=1
export COLLECT_MODE=attack
log_info
log_info "=========== Attack set ==========="
log_info
collect_one_set 2

quit
