#!/bin/bash

dataset=$REPO_DATASET_PATH/240126_300-leak-insub-10cm-lna_avg

# Profile with only 1 POI:
$SC_SRC/attack.py --plot --norm --dataset-path $dataset --num-traces 0 --start-point 800 --end-point 1200 profile --pois-algo r --num-pois 1 --poi-spacing 2 --variable p_xor_k --align
mv ~/Figure_1.png $dataset/profile/plot_corr.png
mv ~/Figure_2.png $dataset/profile/plot_poi_1.png
mv $dataset/profile $dataset/profile_pois_1

# Profile with 2 POIs:
$SC_SRC/attack.py --plot --norm --dataset-path $dataset --num-traces 0 --start-point 800 --end-point 1200 profile --pois-algo r --num-pois 2 --poi-spacing 2 --variable p_xor_k --align
mv ~/Figure_1.png $dataset/profile/plot_corr.png
mv ~/Figure_2.png $dataset/profile/plot_poi_1.png
mv ~/Figure_3.png $dataset/profile/plot_poi_2.png
mv $dataset/profile $dataset/profile_pois_2

# Profile with 3 POIs:
$SC_SRC/attack.py --plot --norm --dataset-path $dataset --num-traces 0 --start-point 800 --end-point 1200 profile --pois-algo r --num-pois 3 --poi-spacing 1 --variable p_xor_k --align
mv ~/Figure_1.png $dataset/profile/plot_corr.png
mv ~/Figure_2.png $dataset/profile/plot_poi_1.png
mv ~/Figure_3.png $dataset/profile/plot_poi_2.png
mv ~/Figure_4.png $dataset/profile/plot_poi_3.png
mv $dataset/profile $dataset/profile_pois_3

# Profile with only 1 POI resampled to 8 MHz:
$SC_SRC/attack.py --plot --norm --dataset-path $dataset --num-traces 0 --start-point 500 --end-point 1500 profile --pois-algo r --num-pois 1 --poi-spacing 2 --variable p_xor_k --align
mv ~/Figure_1.png $dataset/profile/plot_corr.png
mv ~/Figure_2.png $dataset/profile/plot_poi_1.png
mv $dataset/profile $dataset/profile_pois_1_resamp_sr_8e6_pt_266
