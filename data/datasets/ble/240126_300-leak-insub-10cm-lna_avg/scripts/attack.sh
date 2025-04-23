#!/bin/bash

dataset=~/storage/dataset/240126_300-leak-insub-10cm-lna_avg
profile=~/storage/dataset/240126_300-leak-insub-10cm-lna_avg/profile
profile_length=400
start_point=760
end_point=$((start_point + profile_length))
plot=--no-plot

echo "Using 1000 traces with 1 POI:"
./attack.py --log $plot --norm --dataset-path $dataset --start-point $start_point --end-point $end_point --num-traces 1000 attack --attack-algo pcc --profile ${profile}_pois_1 --num-pois 1 --poi-spacing 2 --variable p_xor_k --align
echo "Using 2000 traces with 1 POI:"
./attack.py --log $plot --norm --dataset-path $dataset --start-point $start_point --end-point $end_point --num-traces 2000 attack --attack-algo pcc --profile ${profile}_pois_1 --num-pois 1 --poi-spacing 2 --variable p_xor_k --align
echo "Using 3000 traces with 1 POI:"
./attack.py --log $plot --norm --dataset-path $dataset --start-point $start_point --end-point $end_point --num-traces 3000 attack --attack-algo pcc --profile ${profile}_pois_1 --num-pois 1 --poi-spacing 2 --variable p_xor_k --align
echo "Using 6000 traces with 1 POI:"
./attack.py --log $plot --norm --dataset-path $dataset --start-point $start_point --end-point $end_point --num-traces 6000 attack --attack-algo pcc --profile ${profile}_pois_1 --num-pois 1 --poi-spacing 2 --variable p_xor_k --align

# Best with 2000 traces!
best_nb_traces=2000

echo "Using 2 POIs:"
./attack.py --log $plot --norm --dataset-path $dataset --start-point $start_point --end-point $end_point --num-traces $best_nb_traces attack --attack-algo pcc --profile ${profile}_pois_2 --num-pois 2 --poi-spacing 2 --variable p_xor_k --align
echo "Using 3 POIs:"
./attack.py --log $plot --norm --dataset-path $dataset --start-point $start_point --end-point $end_point --num-traces $best_nb_traces attack --attack-algo pcc --profile ${profile}_pois_3 --num-pois 3 --poi-spacing 1 --variable p_xor_k --align

# Worse with more POIs!
