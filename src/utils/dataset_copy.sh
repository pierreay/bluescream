#!/bin/bash

source ./lib/log.sh

# * Functions

# cp stub using rsync.
# $1 is [SRC...].
# $2 is [DST].
function copy() {
    log_info "Copy $1 to $2..."
    rsync -avz --progress $1 $2
}

# Copy a subset.
# $1 is source dataset directory.
# $2 is destination dataset directory.
# $3 is the subset name.
# $4 is the number of trace to copy.
function subset_copy() {
    if [[ -d $1/$3 ]]; then
        mkdir -p $2/$3
        copy $1/$3/k.npy $2/$3/k.npy
        copy $1/$3/p.npy $2/$3/p.npy
        for (( i = 0; i < $4; i++ ))
        do
            # NOTE: Hacky parallelization using launching 2 background copy
            # every 0.2 seconds.
            if [[ -f $1/$3/${i}_trace_nf.npy ]]; then
                copy $1/$3/${i}_trace_nf.npy $2/$3/${i}_trace_nf.npy &
            fi
            if [[ -f $1/$3/${i}_trace_ff.npy ]]; then
                copy $1/$3/${i}_trace_ff.npy $2/$3/${i}_trace_ff.npy &
            fi
            sleep 0.1
            # NOTE: No more than 10 rsync in parallel.
            while [[ $(pgrep rsync | wc -l) > 10 ]]; do
                log_warn "Sleep waiting rsync background processes to terminate..."
                sleep 10
            done
        done
    fi
}

# * Script

# Help.
if [[ $# -lt 3 ]]; then
    echo "Usage: dataset_copy.sh SRC DST NB_TRACE"
    echo "This script will (partially or completely) copy a dataset from SRC to DST using NB_TRACE number of traces."
    exit 0
fi

# Arguments.
SRC=$1
DST=$2
NB_TRACE=$3

# Copy.
copy $SRC/dataset.pyc $DST/dataset.pyc
subset_copy $SRC $DST train $NB_TRACE
subset_copy $SRC $DST attack $NB_TRACE
