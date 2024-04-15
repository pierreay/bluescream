#!/bin/bash

DATASET=$REPO_DATASET_PATH/ble/240413_1-leak-pairing-highdist-fix-2.534e9-8e6_raw
SP=1000 # NOTE: Depends on current sampling rate at 8e6.
EP=1500 # NOTE: Depends on current sampling rate at 8e6.

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

comp_list=(AMPLITUDE PHASE_ROT)
num_traces_list=(5000)
pois_algo_list=(r snr)
pois_nb_list=(1 2)

for comp in "${comp_list[@]}"; do
    for num_traces in "${num_traces_list[@]}"; do
        for pois_algo in "${pois_algo_list[@]}"; do
            for pois_nb in "${pois_nb_list[@]}"; do
                profile_comp $comp $num_traces $pois_algo $pois_nb
            done
        done
    done
done
