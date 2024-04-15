#!/bin/bash

./dataset.py --loglevel INFO average --nb-aes 300 $ENVRC_DATASET_PATH/240126_300-leak-insub-10cm-lna_raw $ENVRC_DATASET_PATH/240126_300-leak-insub-10cm-lna_avg train --template 1 --no-plot --stop -1 --no-force --jobs=-1
./dataset.py --loglevel INFO average --nb-aes 300 $ENVRC_DATASET_PATH/240126_300-leak-insub-10cm-lna_raw $ENVRC_DATASET_PATH/240126_300-leak-insub-10cm-lna_avg attack --template 1 --no-plot --stop -1 --no-force --jobs=-1
