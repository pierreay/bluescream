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
indir=~/storage/dataset/240110_single-leak-pairing-1m-lna_raw
log_info "indir=$indir"

poi_num=2
poi_spacing=2
variable=p_xor_k

log_info "attack sweep using the attack set"
# XXX: Attack trace sweep could be parallelized inside attack.py using same code template as dataset.py/average.
start=72000
stop=75000
template_length=400
step=10
for (( i = $start; i <= $stop; i += $step ))
do
    end=$(( $i + $template_length ))
    echo "=============="
    echo -n "start=$i;"
    echo "end=$end"
    # NOTE: Discard stderr because of tqdm progress bar.
    ./attack.py --no-log --no-plot --norm --dataset-path $indir --start-point $i --end-point $end --num-traces 300 attack --attack-algo pcc --profile ~/git/screaming_channels_ble/data/profiles/231222_single-cable-balanced_raw/ --variable p_xor_k --align 2>/dev/null | grep "CORRECT\|PGE\|rounded"
done
