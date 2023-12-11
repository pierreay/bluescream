#!/bin/bash -e

source ./lib/log.sh
source ./lib/pywrap.sh

function help() {
    cat << EOF
Usage: attack_sweep.sh

Run a profiled correlation attack sweeping over the attack trace to find the correct alignment.
EOF
}

# Check for number of args.
if [[ $# -gt 0 ]]; then
    help
    exit 1
fi

# Default variable and configuration summary.
indir=$ENVRC_DATASET_AVG_PATH
template_length=200
log_info "indir=$indir"

poi_num=2
poi_spacing=2
variable=p_xor_k

log_info "attack sweep using the attack set"
# XXX: Attack trace sweep could be parallelized inside attack.py using same code template as dataset.py/average.
start=1000
for (( i = 1; i <= 2000; i++ ))
do
    end=$(( $start + $template_length ))
    echo -n "start=$start;"
    echo -n "end=$end;"
    start=$(( $start + 1 ))
    # Discard stderr because of tqdm progress bar.
    ./attack.py --no-log --norm --dataset-path $indir --start-point $start --end-point $end --num-traces $NBTRACE attack  --attack-algo pcc --variable p_xor_k 2>/dev/null | grep CORRECT
done
