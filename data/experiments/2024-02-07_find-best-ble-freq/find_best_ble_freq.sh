#!/bin/bash

dir="$(dirname $(realpath $0))"

# * Wide-band analysis

function wb() {
    export SR=56e6; export FC=$1;
    echo SR=$SR; echo FC=$FC
    ./radio.py --dir "$ENVRC_RADIO_DIR" --loglevel DEBUG listen "$ENVRC_NF_FREQ" "$FC" "$SR" --nf-id $ENVRC_NF_ID --ff-id $ENVRC_FF_ID --duration=0.2 --gain=76 &
    sleep 6
    ./radio.py --loglevel DEBUG --dir "$ENVRC_RADIO_DIR" instrument "$ENVRC_DATASET_RAW_PATH" train "$ENVRC_ATTACKER_ADDR" "$ENVRC_VICTIM_ADDR" "$ENVRC_VICTIM_PORT" --idx 0 --config fast
    ./radio.py --dir "$ENVRC_RADIO_DIR" extract "$FC" "$SR" 0 --plot --no-overwrite --no-exit-on-error --config 1_aes_ff_antenna_8msps
    ./radio.py quit
}

# DONE:
# wb 2.510e9
# DONE:
# wb 2.530e9
# DONE:
# wb 2.550e9
# DONE:
# wb 2.570e9
# DONE:
# wb 2.590e9

echo Candidates:
echo 2.510
echo 2.530
echo 2.533
echo 2.566
echo 2.574
echo 2.595

# * Narrow-band capture

function nb() {
    export SR=8e6; export FC=$1; export G=76;
    echo SR=$SR; echo FC=$FC; echo G=$G
    ./radio.py --dir "$ENVRC_RADIO_DIR" --loglevel DEBUG listen "$ENVRC_NF_FREQ" "$FC" "$SR" --nf-id $ENVRC_NF_ID --ff-id $ENVRC_FF_ID --duration=0.3 --gain=$G &
    sleep 6
    ./radio.py --loglevel DEBUG --dir "$ENVRC_RADIO_DIR" instrument "$ENVRC_DATASET_RAW_PATH" train "$ENVRC_ATTACKER_ADDR" "$ENVRC_VICTIM_ADDR" "$ENVRC_VICTIM_PORT" --idx 0 --config fast
    if [[ $? != 0 ]]; then
        echo INSTRUMENTATION ERROR
        pkill radio.py
        exit 1
    fi
    ./radio.py --dir "$ENVRC_RADIO_DIR" extract "$FC" "$SR" 0 --no-plot --overwrite --exit-on-error --config 1_aes_ff_antenna_8msps
    if [[ $? != 0 ]]; then
        echo EXTRACTION ERROR
        pkill radio.py
        exit 1
    fi
    ./radio.py --dir "$ENVRC_RADIO_DIR" to-numpy $dir/fc_${FC}_sr_${SR}_g_${G}db.npy
    ./radio.py quit
}

# DONE:
# nb 2.510e9
# DONE:
# nb 2.530e9
# DONE:
# nb 2.533e9
# DONE:
# nb 2.566e9
# DONE:
# nb 2.574e9
# DONE:
# nb 2.595e9

# * AES precise extraction by plot analysis

function shrink() {
    export SR=8e6; export FC=$1; export G=76;
    echo SR=$SR; echo FC=$FC; echo G=$G
    ./radio.py plot-file $SR $dir/fc_${FC}_sr_${SR}_g_${G}db.npy --npy --cut --save $dir/fc_${FC}_sr_${SR}_g_${G}db_aes.npy
}

# DONE:
# shrink 2.510e9
# DONE:
# shrink 2.530e9
# DONE:
# shrink 2.533e9
# DONE:
# shrink 2.566e9
# DONE:
# shrink 2.574e9
# DONE:
# shrink 2.595e9

# * Final visualization

function plot_save() {
    export SR=8e6; export FC=$1; export G=76;
    echo SR=$SR; echo FC=$FC; echo G=$G
    ./radio.py plot-file $SR $dir/fc_${FC}_sr_${SR}_g_${G}db_aes.npy --npy --no-cut --save-plot $dir/fc_${FC}_sr_${SR}_g_${G}db_aes.svg
}

function plot_display() {
    export SR=8e6; export FC=$1; export G=76;
    echo SR=$SR; echo FC=$FC; echo G=$G
    ./radio.py plot-file $SR $dir/fc_${FC}_sr_${SR}_g_${G}db_aes.npy --npy --no-cut
}

# DONE:
# plot_save 2.510e9
# DONE:
# plot_save 2.530e9
# DONE:
# plot_save 2.533e9
# DONE:
# plot_save 2.566e9
# DONE:
# plot_save 2.574e9
# DONE:
# plot_save 2.595e9

plot_display 2.510e9 &
plot_display 2.530e9 &
plot_display 2.533e9 &
plot_display 2.566e9 &
plot_display 2.574e9 &
plot_display 2.595e9

echo "Best candidate:"
echo "2.533e9"
plot_display 2.533e9
