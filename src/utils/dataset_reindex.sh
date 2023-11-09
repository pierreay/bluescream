#!/bin/bash

# * Arguments

if [[ $# != 3 ]]; then
    echo -e "Usage: reindex.sh PATH INDEX NB_FILES_RECORD\nThis script will re-index the traces in the repository PATH using the given INDEX."
    exit 0
fi
if [[ ! -d "$1" ]]; then
    echo "PATH doesn't exist!"
    exit 1
fi
if [[ $2 -le 0 ]]; then
    echo "INDEX should be positive!"
    exit 1
fi
if [[ $3 -le 0 ]]; then
    echo "NB_FILES_RECORD should be positive!"
    exit 1
fi

# * Script

current_base_index=0
current_index=0
target_base_index=$2
i=0
files_per_record=$3

cd "$1"
for file in $(ls -t -r); do
    if [ -f "$file" ]; then
        target_current_index=$(( $target_base_index + $current_index))
        mv "$file" "${file/$current_index/$target_current_index}"
        i=$(( i + 1 ))
        if [[ $i == 4 ]]; then
            current_index=$(( current_index + 1 ))
            i=0
        fi
    fi 
done
