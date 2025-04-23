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

# ** Profile configuration

# List of parameters for the used profiles.
readonly COMP_LIST=(AMPLITUDE) # AMPLITUDE
readonly NUM_TRACES_LIST=(8000 12000 65000)
readonly POIS_ALGO_LIST=(r)
readonly POIS_NB_LIST=(1 2)

readonly PROFILE_LENGTH=550

# ** Attack configuration

# Options.
readonly PLOT="--no-plot"

# Number of traces for the attack.
readonly NUM_TRACES_ATTACK_LIST=(250 2000 8000 40000)

# Paths.
readonly METASET_LIST=(raw) # raw avg ext

# Delimiters.
readonly START_POINT=1020
readonly END_POINT=$((START_POINT + PROFILE_LENGTH))

# ** Sweep-mode configuration

# Toggle the sweep mode.
readonly SWEEP_MODE_EN=0
# Start/End/Step point for the sweep mode.
readonly SWEEP_MODE_START=1040
readonly SWEEP_MODE_STEP=1
readonly SWEEP_MODE_END=1050

# ** Internals

readonly LOG_PATH_BASE="${DATASET_PATH}/logs"
# For an internal profile:
readonly PROFILE_PATH_BASE="${DATASET_PATH}/raw/profiles"
# For an external profile:
# readonly PROFILE_PATH_BASE="${REPO_DATASET_PATH}/ble/240423_highdist_2lna_highgain/avg/profiles"

TMUX_PANE_CAPTURE=""

# * Functions

function attack() {
    # Get parameters.
    local metaset="${1}"
    local num_traces="${2}"
    local comp="${3}"
    local pois_algo="${4}"
    local pois_nb="${5}"
    local num_traces_attack="${6}"
    # Set parameters.
    local plot="${PLOT}"
    local metaset_path="${DATASET_PATH}/${metaset}"
    local profile_path="${PROFILE_PATH_BASE}/${comp}_${num_traces}_${pois_algo}_${pois_nb}"
    if [[ "${comp}" == "RECOMBIN" ]]; then
        profile_path="${PROFILE_PATH_BASE}/"'{}'"_${num_traces}_${pois_algo}_${pois_nb}"
    fi
    local log_path="${LOG_PATH_BASE}/attack_${metaset}_${comp}_${num_traces}_${pois_algo}_${pois_nb}_${num_traces_attack}.log"
    local bruteforce="--no-bruteforce"
    local custom_dtype="--no-custom-dtype"
    if [[ "${metaset}" == "raw" ]]; then
        custom_dtype="--custom-dtype"
    fi
    local start_point="${START_POINT}"
    local end_point="${END_POINT}"
    local align_attack="--align-attack"
    local align_profile="--align-profile"
    local align_profile_avg="--no-align-profile-avg"

    # Safety-guard.
    if [[ -f "${log_path}" ]]; then
        echo "SKIP: Attack: File exists: ${log_path}"
        return 0
    elif [[ $(ls -alh "${metaset_path}/attack" | grep -E "*_trace_ff.npy" | wc -l) -lt "${num_traces_attack}" ]]; then
        echo "SKIP: Attack: Not enough traces: < ${num_traces_attack}"
        return 0
    fi

    # Base command for the attack.sh
    local attack_cmd='"${SC_SRC}"/attack.py "${custom_dtype}" --log "${plot}" --norm --dataset-path "${metaset_path}" --start-point "${start_point}" --end-point "${end_point}" --num-traces "${num_traces_attack}" "${bruteforce}" \
              attack-recombined --comptype "${comp}" --attack-algo pcc --profile "${profile_path}" --num-pois "${pois_nb}" --poi-spacing 1 --variable p_xor_k "${align_attack}" "${align_profile}" "${align_profile_avg}"'

    # For logging multiple attacks:
    if [[ "${SWEEP_MODE_EN}" -eq 0 ]]; then
        # Initialize log.
        mkdir -p "$LOG_PATH_BASE"
        # Perform the attack.
        eval "${attack_cmd}"
        # Finalize log.
        tmux capture-pane -t "${TMUX_PANE_CAPTURE}" -pS - > "${log_path}"
        clear
    # For running sweep mode attacks:
    else
        plot="--no-plot"
        align_profile="--no-align-profile"
        for start_point in $(seq "${SWEEP_MODE_START}" "${SWEEP_MODE_STEP}" "${SWEEP_MODE_END}"); do
            local kr="$(eval "${attack_cmd}" 2>/dev/null | grep actual)"
            printf "${start_point};${kr/actual rounded: /}\n"
        done
    fi
}

function git_checkout() {
    local branch="${1}"
    local path="${2}"
    printf "INFO: Checkout ${branch} -> ${path}\n"
    (cd "${path}" && git checkout "${branch}")
}

function tmux-get-pane() {
    printf "$(tmux list-sessions | grep "attached" | cut -d ":" -f 1):$(tmux list-windows | grep "active" | cut -d ":" -f 1).$(tmux list-panes | grep "active" | cut -d ":" -f 1)"
}

# * Script

clear
TMUX_PANE_CAPTURE="$(tmux-get-pane)"
git_checkout main "${SC}"

for metaset in "${METASET_LIST[@]}"; do
    for comp in "${COMP_LIST[@]}"; do
        for num_traces in "${NUM_TRACES_LIST[@]}"; do
            for pois_algo in "${POIS_ALGO_LIST[@]}"; do
                for pois_nb in "${POIS_NB_LIST[@]}"; do
                    for num_traces_attack in "${NUM_TRACES_ATTACK_LIST[@]}"; do
                        attack "${metaset}" "${num_traces}" "${comp}" "${pois_algo}" "${pois_nb}" "${num_traces_attack}"
                    done
                done
            done
        done
    done
done
