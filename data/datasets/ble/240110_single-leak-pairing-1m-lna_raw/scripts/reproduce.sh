# I also tried pdf as attack algo but that was no better.

# Attack 1:
./attack.py --no-log --no-plot --norm --dataset-path /home/drac/storage/dataset/240110_single-leak-pairing-1m-lna_raw --start-point 73837 --end-point 74237 --num-traces 3987 attack --attack-algo pcc --profile /home/drac/git/screaming_channels_ble/data/profiles/231222_single-cable-balanced_raw/ --num-pois 2 --poi-spacing 1 --variable p_xor_k --align

# Attack 2:
./attack.py --log --no-plot --norm --dataset-path /home/drac/storage/dataset/240110_single-leak-pairing-1m-lna_raw --start-point 74025 --end-point 74425 --num-traces 16000 attack --attack-algo pcc --profile /home/drac/storage/dataset/240112_multi-leak-insub-1m-lna_avg/profile_pois_2 --num-pois 2 --poi-spacing 1 --variable p_xor_k --align
