#!/bin/bash

source ./lib/log.sh 
source ./lib/misc.sh

# * Subset

# ** Functions

function clean() {
    if [[ -d $OUTPUT_WD ]]; then
        rm -rf $OUTPUT_WD/*
        log_info "Clean $OUTPUT_WD"
    else
        log_error "$OUTPUT_WD is not set!"
        exit 0
    fi
}

function resume() {
    if [[ -d $OUTPUT_WD ]]; then
        i_start=$(( $(ls $OUTPUT_WD/ | grep trace_nf | wc -l) - 1))
        log_info "Resume collection at i=$i_start in $OUTPUT_WD"
    fi
}

function quit() {
    exit
}

function display_time_quit() {
    display_time
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
    if [[ $FW_MODE == "train" ]]; then
        log_info "power off ykush..."
        sudo ykushcmd -d a
        sleep 10 # Wait for shutdown.
        log_info "power on ykush..."
        sudo ykushcmd -u a
    else
        log_info "disabled for attack mode, otherwise pairing is lost..."
    fi
    sleep 20 # Wait for power-up and booting.
    }

function pair() {
    timeout 30 ./utils/mirage_pair.sh "$ENVRC_VICTIM_ADDR" | tee /tmp/mirage_pair_output
    if [[ $? -ge 1 ]]; then
        return 1
    fi
    grep FAIL /tmp/mirage_pair_output >/dev/null 2>&1
    return $(( 1 - $? ))
}

function record() {
    timeout 30 python3 ./radio.py --dir "$ENVRC_RADIO_DIR" record "$ENVRC_VICTIM_ADDR" "$ENVRC_NF_FREQ" "$ENVRC_FF_FREQ" "$ENVRC_SAMP_RATE" --duration="$ENVRC_DURATION"
    if [[ $? -ge 1 ]]; then
        return 1
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
                    quit
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
            quit
        fi
    fi

    # * Profiling.

    SECONDS=0
    trap display_time_quit INT

    # * Collecting.

    # Make sure output directory is created (/attack or /train) or do nothing
    # if resuming.
    mkdir -p $OUTPUT_WD

    if [[ $KEY_FIXED == 1 ]]; then
        if [[ $i_start == 0 ]]; then
            pair
            cp /tmp/mirage_output_ltk $OUTPUT_WD/k.txt
            # Fix record.py trying to load values from /tmp after rebooting.
            cp /tmp/mirage_output_addr $OUTPUT_WD/.addr.txt
            cp /tmp/mirage_output_rand $OUTPUT_WD/.rand.txt
            cp /tmp/mirage_output_ediv $OUTPUT_WD/.ediv.txt
        else
            cp $OUTPUT_WD/.addr.txt /tmp/mirage_output_addr
            cp $OUTPUT_WD/.rand.txt /tmp/mirage_output_rand
            cp $OUTPUT_WD/.ediv.txt /tmp/mirage_output_ediv
        fi
    fi

    log_info "freq_nf=$ENVRC_NF_FREQ"      >  $OUTPUT_WD/params.txt
    log_info "freq_ff=$ENVRC_FF_FREQ"      >> $OUTPUT_WD/params.txt
    log_info "samp_rate=$ENVRC_SAMP_RATE"  >> $OUTPUT_WD/params.txt

    for (( i = i_start; i <= $COLLECT_NB; i++ ))
    do
        log_info
        log_info "=========== TRACE #$i -- KEY_FIXED=$KEY_FIXED ==========="
        log_info
        if [[ $KEY_FIXED == 0 ]]; then
            pair
            if [[ $? == 1 ]]; then
                ykush_reset
                i=$(( $i - 1 ))
                continue
            fi
            cp /tmp/mirage_output_ltk $OUTPUT_WD/${i}_k.txt
            log_info "saved ks:"
            ls $OUTPUT_WD/${i}_k.txt
        fi
        record
        if [[ $? == 1 ]]; then
            ykush_reset
            i=$(( $i - 1 ))
            continue
        fi
        if [[ $FW_MODE == "train" ]]; then
            ./radio.py --dir $ENVRC_RADIO_DIR extract $ENVRC_SAMP_RATE --window 0.2 --offset 0.00 --no-plot --overwrite
        elif [[ $FW_MODE == "attack" ]]; then
            ./radio.py --dir $ENVRC_RADIO_DIR extract $ENVRC_SAMP_RATE --window 0.01 --offset 0.00 --no-plot --overwrite
        fi
        cp /tmp/raw_0_0.npy $OUTPUT_WD/${i}_trace_nf.npy
        cp /tmp/raw_1_0.npy $OUTPUT_WD/${i}_trace_ff.npy
        cp /tmp/bt_skd_0 $OUTPUT_WD/${i}_p.txt
        log_info "saved traces:"
        ls $OUTPUT_WD/${i}_trace_nf.npy $OUTPUT_WD/${i}_trace_ff.npy
        log_info "saved pt:"
        ls $OUTPUT_WD/${i}_p.txt

        if [[ $KEY_FIXED == 0 && $(( ($i+1) % 100 )) == 0 ]]; then
            log_warn "restart devices to prevent errors..."
            ykush_reset
        fi
    done

    display_time
}

# * Dataset

sleep 5         # Be sure fstab mount our partitions.
if [[ -z ${OUTPUT_WD_ROOT+x} ]]; then
    export OUTPUT_WD_ROOT=$HOME/storage/screaming_channels_dataset/raw
fi
if [[ -z ${COLLECT_TRAINING_NB+x} ]]; then
    export COLLECT_TRAINING_NB=65536
fi
if [[ -z ${COLLECT_ATTACK_NB+x} ]]; then
    export COLLECT_ATTACK_NB=2048
fi

# ** Training subset

export COLLECT_NB="$COLLECT_TRAINING_NB"
export OUTPUT_WD="$OUTPUT_WD_ROOT/train"
export KEY_FIXED=0
log_info
log_info "=========== Training set ==========="
log_info
export FW_MODE=train
firmware_set_mode $FW_MODE >/dev/null 2>&1
collect_one_set 2

# ** Attack subset

export COLLECT_NB="$COLLECT_ATTACK_NB"
export OUTPUT_WD="$OUTPUT_WD_ROOT/attack"
export KEY_FIXED=1
export FW_MODE=attack
log_info
log_info "=========== Attack set ==========="
log_info
firmware_set_mode $FW_MODE >/dev/null 2>&1
collect_one_set 2
