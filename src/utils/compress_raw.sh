#!/bin/bash

# Compress the RAW dataset in order to upload it.
cd $ENVRC_DATASET_PATH && tar cvf $HOME/dataset_raw_$(date "+%Y-%m-%d_%H-%M-%S").tar.bz2 -I pbzip2 raw/train raw/attack
