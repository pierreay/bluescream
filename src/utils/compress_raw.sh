#!/bin/bash

# $1 is the set name [e.g. raw].
# $2 is the subset name [train | attack].
function compress_subset() {
    tar cvf dataset_$1_$2_$(date "+%Y-%m-%d_%H-%M-%S").tar.bz2  -I pbzip2 $1/$2
}

# Compress the RAW dataset in order to upload it.
cd $ENVRC_DATASET_PATH && compress_subset raw train
cd $ENVRC_DATASET_PATH && compress_subset raw attack
