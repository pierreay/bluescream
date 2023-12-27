# * About

# Miscellaneous functions used across bash scripts.

# * Load

source ./lib/discover.sh

# * Bash helper

# Evaluate a step depending on the chosen mode (incremental or equal).
# If $1 is set to "equal", return 1 (and echo 1) if $2 is equal $3.
# If $1 is set to "incr",  return 1 (and echo 1) if $2 is greater or equal $3.
# Otherwise, return 0 and echo nothing.
function eval_cond() {
    if [[ $1 == "equal" && $2 -eq $3 || $1 == "incr" && $2 -ge $3 ]]; then
        echo 1
        return 1
    fi
    return 0
}

# $1 is the question message.
# Return 1 if YES, 0 if NO.
function yes-no() {
    echo "$1"
    select yn in "Yes" "No"; do
        case $yn in
            Yes ) return 1; break;;
            No )  return 0; break;;
        esac
    done
}

# * Firmware

# Compile and flash the Nimble firmware from another git repository.
function firmware_compile_flash() {
    (cd "$ENVRC_NIMBLE_PATH" && make all)
}

# Usage: firmware_set_mode [train | attack] >/dev/null 2>&1
function firmware_set_mode() {
    script=/tmp/script.minicom
    cat << EOF > $script
send mode_$1
! killall -9 minicom
EOF
    minicom -D $(find_nrf_com) -S $script >/dev/null 2>&1 &
    sleep 3
}

# * Environment / Setup

# Reset devices connected to YepKit YKush USB hub.$
# $1 set to 1 perform the reset, otherwise, ignore and log warn [default = 1]
function ykush_reset() {
    if [[ ${1-1} == 1 ]]; then
        # Test that ykushcmd is available, otherwise, return immediately.
        if ! type ykushcmd &> /dev/null; then
            log_warn "Skip ykush reset because ykushcmd is not available!"
            return 1
        fi
        log_info
        log_info "=========== YKUSH RESET ==========="
        log_info
        log_info "Power off YKush..."
        sudo ykushcmd -d a
        sleep 5 # Wait for shutdown.
        log_info "Power on YKush..."
        sudo ykushcmd -u a
        sleep 10 # Wait for power-up and booting.
        log_info "YKush reset done!"
    else
        log_warn "Skip ykush reset because it is not enabled!"
    fi
}

# * Dataset

# Display a tree of a dataset.
# $1 is the path of the dataset [default = $ENVRC_DATASET_RAW_PATH]
function dataset_tree() {
    tree -L 2 -alh -I "??_trace_ff.npy" -I "???_trace_ff.npy" -I "????_trace_ff.npy" -I "?????_trace_ff.npy" \
                   -I "??_trace_nf.npy" -I "???_trace_nf.npy" -I "????_trace_nf.npy" -I "?????_trace_nf.npy" \
                   ${1-$ENVRC_DATASET_RAW_PATH}
    if [[ -d "${1-$ENVRC_DATASET_RAW_PATH}/train" ]]; then
        echo "Number of npy files in train  : $(ls ${1-$ENVRC_DATASET_RAW_PATH}/train | grep '.*.npy' | wc -l)"
    fi
    if [[ -d "${1-$ENVRC_DATASET_RAW_PATH}/attack" ]]; then
        echo "Number of npy files in attack : $(ls ${1-$ENVRC_DATASET_RAW_PATH}/attack | grep '.*.npy' | wc -l)"
    fi
}

# Archive the traces from the train and attack subsets.
# $1 is the path of the dataset [default = $ENVRC_DATASET_RAW_PATH]
function dataset_archive() {
    call_dir=$(pwd)
    cd ${1-$ENVRC_DATASET_RAW_PATH}
    tar cvf train.tar train
    tar cvf attack.tar attack
    cd "$call_dir"
}

# Erase all file inside a dataset.
# $1 is the dataset path [default = $ENVRC_DATASET_RAW_PATH].
function dataset_erase() {
    target=${1-$ENVRC_DATASET_RAW_PATH}
    if [[ -z "$target" ]]; then
        log_error "No valid dataset has been provided for erasing!"
        return 1
    fi
    yes-no "Erase the entire dataset at '$target'?"
    if [[ $? == 1 ]]; then
        echo rm -r "$target"/*
        rm -r "$target"/*
    fi
}

# Archive the Nimble firmware in the dataset.
# It will copy the binary ".hex" from "/tmp" and create the associated submodule.
# $1 is the dataset path [default = $ENVRC_DATASET_RAW_PATH].
function dataset_archive_nimble() {
    call_dir=$(pwd)
    # Save ENVRC variables before moving.
    dataset_path="${1-$ENVRC_DATASET_RAW_PATH}"
    dataset_name=$(basename $(realpath "$dataset_path"))
    nimble_path="$ENVRC_NIMBLE_PATH"
    if [[ -z "$dataset_path" ]]; then
        log_error "No dataset path!"
        return 1
    fi
    # * Archive the firwmare.
    cd "$dataset_path"
    log_info "Export the Nimble firmware..."
    FIRMWARE_DIR=firmware
    mkdir -p $FIRMWARE_DIR && (cd $FIRMWARE_DIR && make -f "$nimble_path"/Makefile export)
    # * Create the tag associated with the dataset inside the current repo.
    log_info "Create the dataset tag inside the Nimble repository..."
    cd "$nimble_path"
    # If tag has already be created locally, delete it.
    git tag | grep "$dataset_name"
    if [[ $? == 0 ]]; then
        git tag -d "$dataset_name"
    fi
    # If tag has already be created globally, delete it.
    git fetch --tags
    git tag | grep "$dataset_name"
    if [[ $? == 0 ]]; then
        git tag -d "$dataset_name"
    fi
    git push --tags --force
    # Replace the tag with the new one.
    git tag $dataset_name
    git push --tags
    # * Archive the submodule and checkout the tag.
    cd "$dataset_path"
    log_info "Create the Nimble submodule..."
    SUBMODULE_DIR=submodules
    mkdir -p $SUBMODULE_DIR && cd $SUBMODULE_DIR && git submodule add --force git@github.com:pierreay/screaming_channels_nimble.git
    # Fetch tags and checkout the tag used for the dataset.
    cd screaming_channels_nimble && git fetch --tags --force
    git checkout $dataset_name
    # Return.
    cd "$call_dir"
}
