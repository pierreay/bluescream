#!/bin/bash

# * About

# Perform multiple attacks and store the results in a CSV file.

# * Configuration

# Output CSV file for Python.
OUTFILE="attack_results.csv"
# Dataset path.
DATASET="/home/drac/storage/dataset/240112_multi-leak-insub-1m-lna_avg"
# Profile path.
PROFILE="$DATASET"/profile_pois_1

# * CSV building

# Write header.
echo "trace_nb;log2(key_rank);correct_bytes;pge_median" > "$OUTFILE"

function iterate() {
    i_start=$1
    i_step=$2
    i_end=$3
    # Iteration over number of traces.
    for num_traces in $(seq $i_start $i_step $i_end); do
        # Write number of traces.
        echo -n "$num_traces;" | tee -a "$OUTFILE"

        # Attack and extract:
        # 1) The key rank
        # 2) The correct number of bytes.
        # 3) The median of the PGE
        ./attack.py --no-log --no-plot --norm --dataset-path "$DATASET" \
                    --start-point 740 --end-point 1140 --num-traces $num_traces attack \
                    --attack-algo pcc --profile "$PROFILE" \
                    --num-pois 1 --poi-spacing 2 --variable p_xor_k --align 2>/dev/null \
            | grep -E 'actual rounded|CORRECT|MEDIAN' \
            | cut -f 2 -d ':' \
            | tr -d ' ' \
            | tr '[\n]' '[;]' \
            | sed 's/2^//' \
            | sed 's/;$//' \
            | tee -a "$OUTFILE"

        echo "" | tee -a "$OUTFILE"
    done
}

# Progressive steps.
iterate 10 10 100
iterate 100 100 1000
iterate 1000 200 2000
iterate 2000 500 15000
