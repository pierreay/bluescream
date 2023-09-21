#!/bin/bash

source ./lib/misc.sh

# Source the project environment for following variables:
# - DE_VICTIM_ADDR
# - DE_ATTACK_HCI
# - DE_REC_FREQ_NF
# - DE_REC_FREQ_FF
# - DE_REC_SAMP_RATE
# Disable sourcing of the environment because it should not allows to modify
# environment variable from the terminal.
# source ../.envrc

# * Subset

# ** Functions

function cleanncreate() {
    rm -rf $OUTPUT_WD
    mkdir -p $OUTPUT_WD
    echo "Clean and create $OUTPUT_WD"
}

function resume() {
    i_start=$(( $(ls $OUTPUT_WD/ | grep trace_nf | wc -l) - 1))
    echo "Resume collection at i=$i_start in $OUTPUT_WD"
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
    echo "$(($duration / 60)) minutes ; $(($duration % 60)) seconds"
}

function ykush_reset() {
    echo
    echo "=========== YKUSH RESET ==========="
    echo
    echo "power off ykush..."
    sudo ykushcmd -d a
    sleep 10 # Wait for shutdown.
    echo "power on ykush..."
    sudo ykushcmd -u a
    sleep 20 # Wait for power-up and booting.
}

function pair() {
    timeout 30 ./utils/mirage_pair.sh "$DE_VICTIM_ADDR" | tee /tmp/mirage_pair_output
    if [[ $? -ge 1 ]]; then
        return 1
    fi
    grep FAIL /tmp/mirage_pair_output >/dev/null 2>&1
    return $(( 1 - $? ))
}

function record() {
    timeout 30 python3 ./radio.py record "$DE_VICTIM_ADDR" "$DE_REC_FREQ_NF" "$DE_REC_FREQ_FF" "$DE_REC_SAMP_RATE"
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
                    cleanncreate
                    break
                    ;;
                ${opts[1]})
                    resume
                    break
                    ;;
                ${opts[2]})
                    quit
                    ;;
                *) echo "Invalid option: $REPLY";;
            esac
        done
    else
        if [[ $opt == 1 ]]; then
            cleanncreate
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

    echo "freq_nf=$DE_REC_FREQ_NF"      >  $OUTPUT_WD/params.txt
    echo "freq_ff=$DE_REC_FREQ_FF"      >> $OUTPUT_WD/params.txt
    echo "samp_rate=$DE_REC_SAMP_RATE"  >> $OUTPUT_WD/params.txt

    for (( i = i_start; i <= $COLLECT_NB; i++ ))
    do
        echo
        echo "=========== TRACE #$i -- KEY_FIXED=$KEY_FIXED ==========="
        echo
        if [[ $KEY_FIXED == 0 ]]; then
            pair
            if [[ $? == 1 ]]; then
                ykush_reset
                i=$(( $i - 1 ))
                continue
            fi
            cp /tmp/mirage_output_ltk $OUTPUT_WD/${i}_k.txt
        fi
        record
        if [[ $? == 1 ]]; then
            ykush_reset
            i=$(( $i - 1 ))
            continue
        fi
        python3 ./radio.py extract "$DE_REC_SAMP_RATE" --no-plot --overwrite --window 0.15 --offset 0.04
        cp /tmp/raw_0_0.npy $OUTPUT_WD/${i}_trace_nf.npy
        cp /tmp/raw_1_0.npy $OUTPUT_WD/${i}_trace_ff.npy
        cp /tmp/bt_skd_0 $OUTPUT_WD/${i}_p.txt
        echo "saved traces:"
        ls $OUTPUT_WD/${i}_trace_nf.npy $OUTPUT_WD/${i}_trace_ff.npy
        echo "saved metadata:"
        ls $OUTPUT_WD/${i}_k.txt $OUTPUT_WD/${i}_p.txt

        if [[ $KEY_FIXED == 0 && $(( ($i+1) % 100 )) == 0 ]]; then
            echo "restart devices to prevent errors..."
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
echo
echo "=========== Training set ==========="
echo
firmware_set_mode train
collect_one_set # 1

# ** Attack subset

export COLLECT_NB="$COLLECT_ATTACK_NB"
export OUTPUT_WD="$OUTPUT_WD_ROOT/attack"
export KEY_FIXED=1
echo
echo "=========== Attack set ==========="
echo
firmware_set_mode attack
collect_one_set # 1
