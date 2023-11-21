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
# $1 is the dataset directory [default = $ENVRC_DATASET_RAW_PATH]
# $2 is the sample rate [default = $ENVRC_SAMP_RATE]
function dataset_init() {
    # NOTE: Dataset name is taken from lib/dataset.py/Dataset.FILENAME variable.
    if [[ ! -f $1/dataset.pyc ]]; then
        log_info "Initialize a dataset in $1..."
        ./dataset.py init ${1-$ENVRC_DATASET_RAW_PATH} ${2-$ENVRC_SAMP_RATE} --input-gen-init --nb-trace-wanted-train 65536 --nb-trace-wanted-attack 16384
    else
        log_info "Dataset already initialized in $1!"
    fi
}

# Average the AES of single traces from one subset.
# $1 is the LOGLEVEL [default = DEBUG]
# $2 is the input dataset [default = $ENVRC_DATASET_RAW_PATH]
# $3 is the output dataset [default = $ENVRC_DATASET_AVG_PATH]
# $4 is the subset [default = train]
# $5 is the template index [default = -1 [ask]]
# $6 is the plot switch [default = --plot]
# $7 is the stop option [default = 1 [stop after first trace]]
# $8 is the force option [default = --no-force]
function dataset_average() {
    ./dataset.py --loglevel ${1-DEBUG} average --nb-aes 300 ${2-$ENVRC_DATASET_RAW_PATH} ${3-$ENVRC_DATASET_AVG_PATH} ${4-train} --template ${5--1} ${6---plot} --stop ${7-1} ${8---no-force} --jobs=-1
}

# * attack.py

# Create a profile from a train subset.
# $1 can be --plot or --no-plot [default = --plot].
# $2 is the --dataset-path [default = $ENVRC_DATASET_AVG_PATH].
# $3 is the --num-traces [default = 0].
# $4 is the --start-point [default = 0].
# $5 is the --end-point [default = 0].
# $6 is the --num-pois [default = 2].
# $7 is the --poi-spacing [default = 2].
# $8 is the --variable [default = p_xor_k].
# $9 is the --align or --no-align [default = --no-align].
function attack_profile() {
    ./attack.py ${1---plot} --norm --dataset-path ${2-$ENVRC_DATASET_AVG_PATH} --num-traces ${3-0} --start-point ${4-0} --end-point ${5-0} profile --pois-algo r --num-pois ${6-2} --poi-spacing ${7-2} --variable ${8-p_xor_k} ${9---no-align}
}
