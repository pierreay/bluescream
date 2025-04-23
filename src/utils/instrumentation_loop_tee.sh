#!/bin/bash

# firmware_compile_flash
# rm -rf /home/drac/storage/dataset/tmp_raw/*
# dataset_init
# ./radio.py --dir $ENVRC_RADIO_DIR --loglevel DEBUG listen $ENVRC_NF_FREQ $ENVRC_FF_FREQ $ENVRC_SAMP_RATE --nf-id $ENVRC_NF_ID --ff-id $ENVRC_FF_ID --duration=$ENVRC_DURATION --gain 76 &

while test 1; do
    echo "======="
    ./radio.py --dir "$ENVRC_RADIO_DIR" instrument "$ENVRC_DATASET_RAW_PATH" train "$ENVRC_ATTACKER_ADDR" "$ENVRC_VICTIM_ADDR" "$ENVRC_VICTIM_PORT" --idx 0 --config example
    ./radio.py --dir "$ENVRC_RADIO_DIR" extract "$ENVRC_SAMP_RATE" "$ENVRC_FF_ID" --no-plot --no-overwrite --no-exit-on-error --config 1_aes_weak --corr \
               ~/git/bluescream/data/signals/2.548GHz_30Msps_AES_BLE_clean_leak_single.npy 2>&1 \
        | tee -a /tmp/radio_extract_output
done
