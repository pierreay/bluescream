#!/bin/bash

dataset=~/storage/dataset/240126_300-leak-insub-10cm-lna_avg
profile=~/storage/dataset/240126_300-leak-insub-10cm-lna_avg/profile
profile_length=400
start_point=760
end_point=$((start_point + profile_length))
plot=--no-plot

echo "Using 2000 traces with 1 POI:"
./attack.py --log $plot --norm --dataset-path $dataset --start-point $start_point --end-point $end_point --num-traces 2000 --bruteforce attack --attack-algo pcc --profile ${profile}_pois_1 --num-pois 1 --poi-spacing 2 --variable p_xor_k --align
