#!/bin/bash
# Profile with only 1 POI:
./attack.py --plot --norm --dataset-path $ENVRC_DATASET_PATH/240112_multi-leak-insub-1m-lna_avg --num-traces 0 --start-point 800 --end-point 1200 profile --pois-algo r --num-pois 1 --poi-spacing 2 --variable p_xor_k --align
mv ~/Figure_1.png profile/plot_corr.png
mv ~/Figure_2.png profile/plot_poi_1.png
mv profile profile_pois_1
# Profile with 2 POIs:
./attack.py --plot --norm --dataset-path $ENVRC_DATASET_PATH/240112_multi-leak-insub-1m-lna_avg --num-traces 0 --start-point 800 --end-point 1200 profile --pois-algo r --num-pois 2 --poi-spacing 2 --variable p_xor_k --align
mv ~/Figure_1.png profile/plot_corr.png
mv ~/Figure_2.png profile/plot_poi_1.png
mv ~/Figure_3.png profile/plot_poi_2.png
mv profile profile_pois_2
# Profile with 3 POIs:
./attack.py --plot --norm --dataset-path $ENVRC_DATASET_PATH/240112_multi-leak-insub-1m-lna_avg --num-traces 0 --start-point 800 --end-point 1200 profile --pois-algo r --num-pois 3 --poi-spacing 1 --variable p_xor_k --align
mv ~/Figure_1.png profile/plot_corr.png
mv ~/Figure_2.png profile/plot_poi_1.png
mv ~/Figure_3.png profile/plot_poi_2.png
mv ~/Figure_4.png profile/plot_poi_3.png
mv profile profile_pois_3
