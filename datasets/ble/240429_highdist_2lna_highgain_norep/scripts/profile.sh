#!/bin/bash -u

# * Environment

env="$(realpath $(dirname $0))/env.sh"
echo "INFO: Source file: $env"
source "$env"

# Safety-guard.
if [[ -z $ENV_FLAG ]]; then
    echo "ERROR: Environment can't been sourced!"
    exit 1
fi

# * Variables

# ** Configuration

readonly COMP_LIST=(AMPLITUDE PHASE_ROT)
readonly NUM_TRACES_LIST=(4000 8000 12000 16000)
readonly POIS_ALGO_LIST=(r snr)
readonly POIS_NB_LIST=(1 2)

readonly PROFILE_LENGTH=550
readonly SP=1100
readonly EP=$(( SP + PROFILE_LENGTH ))

# ** Internals

readonly DATASET="${DATASET_PATH}/raw"

# * Functions

function profile() {
    # Get parameters.
    local comp="${1}"
    local nt="${2}"
    local pois_algo="${3}"
    local pois_nb="${4}"
    # Set parameters.
    local profile="profiles/${comp}_${nt}_${pois_algo}_${pois_nb}"
    local plot="--no-plot"
    local save_images="--save-images"
    local custom_dtype="--no-custom-dtype"
    if [[ "${DATASET}" =~ .*/raw ]]; then
        custom_dtype="--custom-dtype"
    fi

    # Safety-guard.
    if [[ -d "${DATASET}/${profile}" ]]; then
        echo "SKIP: Profile creation: Existing directory: ${profile}"
        return 0
    elif [[ $(ls -alh "${DATASET}/train" | grep -E "*_trace_ff.npy" | wc -l) -lt "${nt}" ]]; then
        echo "SKIP: Profile creation: Not enough traces: < ${nt}"
        return 0
    fi

    # Create the profile and save it.
    "${SC_SRC}/attack.py" "${custom_dtype}" "${plot}" "${save_images}" --norm --dataset-path "${DATASET}" --num-traces "${nt}" --start-point "${SP}" --end-point "${EP}" --comptype "${comp}" \
                      profile --pois-algo "${pois_algo}" --num-pois "${pois_nb}" --poi-spacing 1 --variable p_xor_k --align

    echo "INFO: Save profile: $DATASET/${profile}"
    mv "${DATASET}/profile" "$DATASET/${profile}"
}

# * Script

mkdir -p "${DATASET}/profiles"

for comp in "${COMP_LIST[@]}"; do
    for num_traces in "${NUM_TRACES_LIST[@]}"; do
        for pois_algo in "${POIS_ALGO_LIST[@]}"; do
            for pois_nb in "${POIS_NB_LIST[@]}"; do
                profile "$comp" "$num_traces" "$pois_algo" "$pois_nb"
            done
        done
    done
done
