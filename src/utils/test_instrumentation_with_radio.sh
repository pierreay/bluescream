#!/bin/bash

export SR=8e6; export FC=2.533e9;
echo SR=$SR; echo FC=$FC

./radio.py --dir "$ENVRC_RADIO_DIR" --loglevel DEBUG listen "$ENVRC_NF_FREQ" "$FC" "$SR" --nf-id $ENVRC_NF_ID --ff-id $ENVRC_FF_ID --duration=0.1 --gain=76 &
sleep 6

./radio.py --loglevel DEBUG --dir "$ENVRC_RADIO_DIR" instrument "$ENVRC_DATASET_RAW_PATH" train "$ENVRC_ATTACKER_ADDR" "$ENVRC_VICTIM_ADDR" "$ENVRC_VICTIM_PORT" --idx 0 --config fast

./radio.py --dir "$ENVRC_RADIO_DIR" extract "$FC" "$SR" 0 --plot --no-overwrite --no-exit-on-error --config 1_aes_ff_antenna_8msps

./radio.py quit
