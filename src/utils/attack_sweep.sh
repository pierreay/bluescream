#!/bin/bash -e

# XXX: Attack trace sweep could be parallelized inside attack.py using same
# code template as dataset.py/average() function, if really needed.

source ./lib/log.sh

dataset_dir=~/storage/dataset/240110_single-leak-pairing-1m-lna_raw
profile_dir=~/git/bluescream/data/profiles/231222_single-cable-balanced_raw/ 
poi_num=2
poi_spacing=1
variable=p_xor_k

# * Sweep over points

start=73830
stop=73845
template_length=400
step=2
num_traces=1500
function sweep_over_points() {
    for (( i = $start; i <= $stop; i += $step ))
    do
        end=$(( $i + $template_length ))
        log_info "=============="
        log_info "start=$i"
        log_info "end=$end"
        # NOTE: Discard stderr because of tqdm progress bar.
        ./attack.py --no-log --no-plot --norm --dataset-path $dataset_dir --start-point $i --end-point $end --num-traces $num_traces attack --attack-algo pcc --profile $profile_dir --num-pois $poi_num --poi-spacing $poi_spacing --variable $variable --align 2>/dev/null | grep "CORRECT\|PGE\|rounded"
    done
}

sweep_over_points

# * Sweep over number of traces

# Once the previous part has found the best points, use it and start sweeping
# the number of traces.

start=73837
end=$(( $start + $template_length ))
function sweep_over_number_of_traces() {
    for (( i = 100; i <= 16000; i += $((i / 10)) ))
    do
        log_info "=============="
        log_info "num-traces=$i"
        # NOTE: Discard stderr because of tqdm progress bar.
        ./attack.py --no-log --no-plot --norm --dataset-path $dataset_dir --start-point $start --end-point $end --num-traces $i attack --attack-algo pcc --profile $profile_dir --num-pois $poi_num --poi-spacing $poi_spacing --variable $variable --align 2>/dev/null | grep "CORRECT\|PGE\|rounded"
    done
}

sweep_over_number_of_traces

# * Final attack

function final_attack() {
    start=73837
    num_traces=3987
    ./attack.py --no-log --no-plot --norm --dataset-path $dataset_dir --start-point $start --end-point $end --num-traces $num_traces attack --attack-algo pcc --profile $profile_dir --num-pois $poi_num --poi-spacing $poi_spacing --variable $variable --align 2>/dev/null | grep "CORRECT\|PGE\|rounded"
}

final_attack
