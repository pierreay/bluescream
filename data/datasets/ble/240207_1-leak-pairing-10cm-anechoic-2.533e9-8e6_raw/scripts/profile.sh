#!/bin/bash

dataset=$REPO_DATASET_PATH/ble/240207_1-leak-pairing-10cm-anechoic-2.533e9-8e6_raw
sp=1000
ep=1500

function profile_comp() {
    comp=$1
    nt=$2
    profile=profile_${comp}_${nt}
    echo "[?] Save plots using 's' to Figure_1.png and Figure_2.png"
    $SC_SRC/attack.py --plot --norm --dataset-path $dataset --num-traces $nt --start-point $sp --end-point $ep --comptype $comp profile --pois-algo r --num-pois 1 --poi-spacing 2 --variable p_xor_k --align
    mv $dataset/profile $dataset/$profile
    mv ~/Figure_1.png $dataset/$profile/plot_corr.png
    mv ~/Figure_2.png $dataset/$profile/plot_poi_1.png
}

# DONE: Profile using amplitude:
# profile_comp AMPLITUDE 5000

# DONE: Profile using amplitude:
# profile_comp AMPLITUDE 16384

# DONE: Profile using amplitude with more traces, while collection is still not complete, but used for the paper:
# profile_comp AMPLITUDE 27900

# DONE: Profile using amplitude at 32k traces:
# profile_comp AMPLITUDE 32768

# DONE: Profile using amplitude at 64k traces:
# profile_comp AMPLITUDE 65536

function profile_comp_resamp() {
    comp=$1
    nt=$2
    resamp_to=$3
    profile=profile_${comp}_${nt}_resamp_${resamp_to}
    echo "[?] Save plots using 's' to Figure_1.png and Figure_2.png"
    $SC_SRC/attack.py --plot --norm --dataset-path $dataset --num-traces $nt --start-point $sp --end-point $ep --comptype $comp \
                      profile --pois-algo r --num-pois 1 --poi-spacing 2 --variable p_xor_k --align --resamp-to ${resamp_to}
    mv $dataset/profile $dataset/$profile
    mv ~/Figure_1.png $dataset/$profile/plot_corr.png
    mv ~/Figure_2.png $dataset/$profile/plot_poi_1.png
}

# DONE:
# profile_comp_resamp AMPLITUDE 65536 16e6
