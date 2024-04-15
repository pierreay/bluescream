#!/bin/bash

# * About

# Perform multiple attacks and store the results in a CSV file.

# * Global configuration

# Dataset path.
DATASET=$REPO_DATASET_PATH/ble/240412_1-leak-pairing-highdist-fix-2.534e9-16e6_raw

# Length of the profile in samples.
PROFILE_LENGTH=1000
# Start index for attack traces.
START_POINT=2000
# Stop index for attack traces.
END_POINT=$((START_POINT + PROFILE_LENGTH))

# Path of script directory.
SCRIPT_WD="$(dirname $(realpath $0))"

# * Functions for CSV building

function iterate() {
    i_start=$1
    i_step=$2
    i_end=$(($3 - 1 ))
    # Iteration over number of traces.
    for num_traces in $(seq $i_start $i_step $i_end); do
        # Write number of traces.
        echo -n "$num_traces;" | tee -a "$OUTFILE_CSV"

        # Attack and extract:
        # 1) The key rank
        # 2) The correct number of bytes.
        # 3) The median of the PGE
        $SC_SRC/attack.py --no-log --no-plot --norm --dataset-path "$DATASET"                                          \
                          --start-point $START_POINT --end-point $END_POINT --num-traces $num_traces attack-recombined \
                          --comptype $COMPTYPE --attack-algo pcc --profile "$PROFILE"                                  \
                          --num-pois $POIS_NB --poi-spacing 1 --variable p_xor_k --align 2>/dev/null                   \
            | grep -E 'actual rounded|CORRECT|MEDIAN'                                                                  \
            | cut -f 2 -d ':'                                                                                          \
            | tr -d ' '                                                                                                \
            | tr '[\n]' '[;]'                                                                                          \
            | sed 's/2^//'                                                                                             \
            | sed 's/;$//'                                                                                             \
            | tee -a "$OUTFILE_CSV"

        echo "" | tee -a "$OUTFILE_CSV"
    done
}

function csv_build() {
    # Configuration of iterate().
    # Profile path.
    export PROFILE=$DATASET/profile_$1_${POIS_ALGO}_${POIS_NB}
    # Attacked component.
    export COMPTYPE=$2

    # Write CSV header.
    echo "trace_nb;log2(key_rank);correct_bytes;pge_median" > "$OUTFILE_CSV"
    # Get data into CSV [START STEP END].
    iterate 10 100 1500
    # iterate 10 125 1000
    # iterate 1000 250 10000
    # iterate 10000 500 $((20000 + 1))
}

# * Script

nb_traces_list=(5000)
comp_list=(AMPLITUDE RECOMBIN)
pois_algo_list=(r snr)
pois_nb_list=(1)

for nb_traces in "${nb_traces_list[@]}"; do
    for comp in "${comp_list[@]}"; do
        for pois_algo in "${pois_algo_list[@]}"; do
            for pois_nb in "${pois_nb_list[@]}"; do
                # POIs algorithm.
                export POIS_ALGO=$pois_algo
                # POIs number.
                export POIS_NB=$pois_nb
                
                # Output CSV file for Python.
                export OUTFILE_CSV=$DATASET/logs/attack_results_${comp}_${nb_traces}_${POIS_ALGO}_${POIS_NB}.csv
                # Output PDF file for Python.
                export OUTFILE_PDF=$DATASET/plots/attack_results_${comp}_${nb_traces}_${POIS_ALGO}_${POIS_NB}.pdf
                
                # Safety-guard.
                if [[ ! -f ${OUTFILE_CSV} ]]; then
                    # NOTE: Add/remove "&" for parallel/serial execution.
                    csv_build '{}'_${nb_traces} ${comp} # &
                else
                    echo "SKIP: File exists: ${OUTFILE_CSV}"
                fi

                # Safety-guard.
                if [[ ! -f ${OUTFILE_PDF} ]]; then
                    # Plot.
                    basename=$(basename $0)
                    python3 "${SCRIPT_WD}/${basename/.sh/.py}" $OUTFILE_CSV $OUTFILE_PDF
                else
                    echo "SKIP: File exists: ${OUTFILE_PDF}"
                fi
            done
        done
    done
done
