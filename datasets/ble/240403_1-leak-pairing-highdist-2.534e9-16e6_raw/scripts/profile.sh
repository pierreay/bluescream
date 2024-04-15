#!/bin/bash

DATASET=$REPO_DATASET_PATH/ble/240403_1-leak-pairing-highdist-2.534e9-16e6_raw
SP=2000
EP=3000

function profile_comp() {
    comp=$1
    nt=$2
    pois_algo=$3
    pois_nb=$4
    profile=profile_${comp}_${nt}_${pois_algo}_${pois_nb}
    if [[ -d "${DATASET}/${profile}" ]]; then
        echo "[!] Profile already created: ${profile}"
        return 0
    fi
    
    plot=--no-plot
    save_images=--save-images
    $SC_SRC/attack.py ${plot} ${save_images} --norm --dataset-path ${DATASET} --num-traces ${nt} --start-point ${SP} --end-point ${EP} --comptype ${comp} profile --pois-algo ${pois_algo} --num-pois ${pois_nb} --poi-spacing 1 --variable p_xor_k --align
    mv $DATASET/profile $DATASET/$profile
}

for comp in AMPLITUDE PHASE_ROT; do
    for num_traces in 5000 10000 19000 30000; do
        for pois_algo in r snr corr; do
            for pois_nb in 1 2 3; do
                profile_comp $comp $num_traces $pois_algo $pois_nb
            done
        done
    done
done
