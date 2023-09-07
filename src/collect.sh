#!/bin/bash

# Source the project environment for following variables:
# - DE_VICTIM_ADDR
# - DE_ATTACK_HCI
# - DE_REC_FREQ_NF
# - DE_REC_FREQ_FF
# - DE_REC_SAMP_RATE
source ../.envrc

# * collect_one_set.sh

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

function timeoutnreboot() {
    timeout 30 $*
    ret=$?
    if [[ $ret == 124 || $ret == 1 ]]; then
        echo "ret=$ret for $*"
        echo
        echo "=========== REBOOT ==========="
        echo
        # sleep 30 && sudo reboot
        echo "=========== REBOOT DISABLED ==========="
        echo
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
            ./utils/mirage_pair.sh "$DE_VICTIM_ADDR" "$DE_ATTACK_HCI"
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
            timeoutnreboot ./utils/mirage_pair.sh "$DE_VICTIM_ADDR" "$DE_ATTACK_HCI"
            cp /tmp/mirage_output_ltk $OUTPUT_WD/${i}_k.txt
        fi
        timeoutnreboot python3 ./collect.py record "$DE_VICTIM_ADDR" "$DE_REC_FREQ_NF" "$DE_REC_FREQ_FF" "$DE_REC_SAMP_RATE"
        python3 ./collect.py extract "$DE_REC_SAMP_RATE" --no-plot --overwrite --window 0.15 --offset 0.04
        cp /tmp/raw_0_0.npy $OUTPUT_WD/${i}_trace_nf.npy
        cp /tmp/raw_1_0.npy $OUTPUT_WD/${i}_trace_ff.npy
        cp /tmp/bt_skd_0 $OUTPUT_WD/${i}_p.txt
    done

    display_time
}

# * collect.sh

sleep 5         # Be sure fstab mount our partitions.
if [[ -z ${OUTPUT_WD_ROOT+x} ]]; then
    export OUTPUT_WD_ROOT=$HOME/storage/screaming_channels_annex/tmp
fi
if [[ -z ${COLLECT_TRAINING_NB+x} ]]; then
    export COLLECT_TRAINING_NB=65536
fi
if [[ -z ${COLLECT_ATTACK_NB+x} ]]; then
    export COLLECT_ATTACK_NB=2048
fi

# ** Training set collection

export COLLECT_NB="$COLLECT_TRAINING_NB"
export OUTPUT_WD="$OUTPUT_WD_ROOT/train"
export KEY_FIXED=0
echo
echo "=========== Training set ==========="
echo
collect_one_set # 2

# ** Attack set collection

export COLLECT_NB="$COLLECT_ATTACK_NB"
export OUTPUT_WD="$OUTPUT_WD_ROOT/attack"
export KEY_FIXED=1
echo
echo "=========== Attack set ==========="
echo
collect_one_set # 2
