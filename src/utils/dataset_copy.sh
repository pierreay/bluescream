#!/bin/bash

source ./lib/log.sh

# * Functions

# cp stub using rsync.
# $1 is [SRC...].
# $2 is [DST].
# If env $PARALLEL != 0, use background copy.
function copy() {
    log_info "Copy $1 to $2..."
    # NOTE: Hacky parallelization launching 2 background copy.
    if [[ $PARALLEL != 0 ]]; then
        rsync -avz --progress $1 $2 &
    else
        rsync -avz --progress $1 $2
    fi
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
            if [[ -f $1/$3/${i}_trace_nf.npy ]]; then
                copy $1/$3/${i}_trace_nf.npy $2/$3/${i}_trace_nf.npy
            fi
            if [[ -f $1/$3/${i}_trace_ff.npy ]]; then
                copy $1/$3/${i}_trace_ff.npy $2/$3/${i}_trace_ff.npy
            fi
            # NOTE: No more than 50 rsync in parallel.
            if [[ $PARALLEL != 0 ]]; then
                while test $(pgrep rsync | wc -l) -ge 50; do
                    log_warn "Sleep waiting rsync background processes to terminate..."
                    sleep 1
                done
            fi
        done
    fi
}

# * Script

# Help.
if [[ $# -lt 3 ]]; then
    echo "Usage: dataset_copy.sh SRC DST NB_TRACE [-p]"
    echo "This script will (partially or completely) copy (using rsync) a dataset from SRC to DST using NB_TRACE number of traces."
    echo "DST (not SRC) can be specified using an SSH remote, e.g. myserver:/home/storage"
    echo "If -p is passed, use parallel copy."
    exit 0
fi

# Arguments.
SRC=$1
DST=$2
NB_TRACE=$3
PARALLEL=${4-0}

# Copy.
copy $SRC/dataset.pyc $DST/dataset.pyc
subset_copy $SRC $DST train $NB_TRACE
subset_copy $SRC $DST attack $NB_TRACE
