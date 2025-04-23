#!/bin/bash

echo "Using 1000 traces with 1 POI:"
./attack.py --log --no-plot --norm --dataset-path /home/drac/storage/dataset/240112_multi-leak-insub-1m-lna_avg --start-point 740 --end-point 1140 --num-traces 1000 attack --attack-algo pcc --profile /home/drac/storage/dataset/240112_multi-leak-insub-1m-lna_avg/profile_pois_1 --num-pois 1 --poi-spacing 2 --variable p_xor_k --align
echo "Using 2000 traces with 1 POI:"
./attack.py --log --no-plot --norm --dataset-path /home/drac/storage/dataset/240112_multi-leak-insub-1m-lna_avg --start-point 740 --end-point 1140 --num-traces 2000 attack --attack-algo pcc --profile /home/drac/storage/dataset/240112_multi-leak-insub-1m-lna_avg/profile_pois_1 --num-pois 1 --poi-spacing 2 --variable p_xor_k --align
echo "Using 3000 traces with 1 POI:"
./attack.py --log --no-plot --norm --dataset-path /home/drac/storage/dataset/240112_multi-leak-insub-1m-lna_avg --start-point 740 --end-point 1140 --num-traces 3000 attack --attack-algo pcc --profile /home/drac/storage/dataset/240112_multi-leak-insub-1m-lna_avg/profile_pois_1 --num-pois 1 --poi-spacing 2 --variable p_xor_k --align
echo "Using 6000 traces with 1 POI:"
./attack.py --log --no-plot --norm --dataset-path /home/drac/storage/dataset/240112_multi-leak-insub-1m-lna_avg --start-point 740 --end-point 1140 --num-traces 6000 attack --attack-algo pcc --profile /home/drac/storage/dataset/240112_multi-leak-insub-1m-lna_avg/profile_pois_1 --num-pois 1 --poi-spacing 2 --variable p_xor_k --align
echo "Using 10000 traces with 1 POI:"
./attack.py --log --no-plot --norm --dataset-path /home/drac/storage/dataset/240112_multi-leak-insub-1m-lna_avg --start-point 740 --end-point 1140 --num-traces 10000 attack --attack-algo pcc --profile /home/drac/storage/dataset/240112_multi-leak-insub-1m-lna_avg/profile_pois_1 --num-pois 1 --poi-spacing 2 --variable p_xor_k --align
echo "Using 15000 traces with 1 POI:"
./attack.py --log --no-plot --norm --dataset-path /home/drac/storage/dataset/240112_multi-leak-insub-1m-lna_avg --start-point 740 --end-point 1140 --num-traces 15000 attack --attack-algo pcc --profile /home/drac/storage/dataset/240112_multi-leak-insub-1m-lna_avg/profile_pois_1 --num-pois 1 --poi-spacing 2 --variable p_xor_k --align

# Better with more traces but not too much!

echo "Using 2 POIs:"
./attack.py --log --no-plot --norm --dataset-path /home/drac/storage/dataset/240112_multi-leak-insub-1m-lna_avg --start-point 740 --end-point 1140 --num-traces 6000 attack --attack-algo pcc --profile /home/drac/storage/dataset/240112_multi-leak-insub-1m-lna_avg/profile_pois_2 --num-pois 2 --poi-spacing 2 --variable p_xor_k --align
echo "Using 3 POIs:"
./attack.py --log --no-plot --norm --dataset-path /home/drac/storage/dataset/240112_multi-leak-insub-1m-lna_avg --start-point 740 --end-point 1140 --num-traces 6000 attack --attack-algo pcc --profile /home/drac/storage/dataset/240112_multi-leak-insub-1m-lna_avg/profile_pois_3 --num-pois 3 --poi-spacing 1 --variable p_xor_k --align

# Worse with more POIs!

echo "Using PDF:"
./attack.py --log --no-plot --norm --dataset-path /home/drac/storage/dataset/240112_multi-leak-insub-1m-lna_avg --start-point 740 --end-point 1140 --num-traces 6000 attack --attack-algo pdf --profile /home/drac/storage/dataset/240112_multi-leak-insub-1m-lna_avg/profile_pois_1 --num-pois 1 --poi-spacing 2 --variable p_xor_k --align

# Worse and longer with PDF!
