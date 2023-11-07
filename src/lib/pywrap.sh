# * About

# Bash library wrapping my Python commands.

# * radio.py

# Initialize the radio thread in the background.
# $1 is loglevel [default = DEBUG].
function radio_init() {
    ./radio.py --dir $ENVRC_RADIO_DIR --loglevel ${1-DEBUG} listen $ENVRC_NF_FREQ $ENVRC_FF_FREQ $ENVRC_SAMP_RATE --nf-id $ENVRC_NF_ID --ff-id $ENVRC_FF_ID --duration=$ENVRC_DURATION &
    sleep 20 # Wait for SDR's driver initialization.
}

# Arguments:
# $1 is loglevel [default = DEBUG].
# $2 should be the subset [train | attack] [default = train].
# $3 should be the trace recording index [default = 0].
# $4 should be any supplementary switch [EMPTY | --no-radio] [default = EMPTY]
function radio_instrument() {
    # NOTE: Send a SIGINT signal such that Python goes through the __exit__()
    # of Device class, such that WHAD/Butterfly do not finish in a bad state.
    timeout --signal=SIGINT 30 python3 ./radio.py --loglevel ${1-DEBUG} --dir $ENVRC_RADIO_DIR instrument $ENVRC_DATASET_RAW_PATH ${2-train} $ENVRC_ATTACKER_ADDR $ENVRC_VICTIM_ADDR $ENVRC_VICTIM_PORT --idx ${3-0} $4
    if [[ $? -ge 1 ]]; then
        return 1
    fi
}

function radio_quit() {
    ./radio.py quit
}

# * dataset.py

# Initialize a dataset in $1 using sample rate $2. Silently do nothing if
# dataset already exists.
function dataset_init() {
    # NOTE: Dataset name is taken from lib/dataset.py/Dataset.FILENAME variable.
    if [[ ! -f $1/dataset.pyc ]]; then
        log_info "Initialize a dataset in $1"
        ./dataset.py init $1 $2 --input-gen-init --nb-trace-wanted-train 65536 --nb-trace-wanted-attack 16384
    fi
}
