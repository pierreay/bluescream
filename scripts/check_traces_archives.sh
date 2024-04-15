#!/bin/bash

VERBOSE=0

function check_datasets_under() {
    for dataset in $(realpath $(find "$1" -maxdepth 1 -type d -regex ".*23.*\|.*24.*")); do
        if [[ $VERBOSE == 1 ]]; then
            echo "INFO: Check: ${dataset}"
        fi
        # NOTE: List from .gitignore.
        for directory in train train2 attack attack2; do
            if [[ -d "${dataset}/${directory}" ]]; then
                size_run=$(stat -c "%s" "${dataset}/${directory}")
                size_stage=$(stat -c '%s' "${dataset}/${directory}.tar")
                if [[ $VERBOSE == 1 ]]; then
                    echo size_run="$size_run"
                    echo size_stage="$size_stage"
                fi
                if [[ "$size_run" -gt "$size_stage" ]]; then
                    echo "WARN: Re-compress ${directory} into ${directory}.tar: ${dataset}"
                fi
            fi
        done
        if [[ $VERBOSE == 1 ]]; then
            echo "DONE!"
        fi
    done    
}

check_datasets_under "$REPO_DATASET_PATH/poc"
check_datasets_under "$REPO_DATASET_PATH/ble"
