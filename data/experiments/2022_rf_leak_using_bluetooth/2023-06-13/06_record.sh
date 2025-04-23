#!/bin/bash
ssh $REMOTE "cd $REMOTE_WD && source .envrc && python3 ./src/record.py"
mkdir -p record/
rsync -avz --progress $REMOTE:/tmp/USRP_0-127.0MHz-30.0Msps_raw_abs.npy record/
rsync -avz --progress $REMOTE:/tmp/USRP_1-2.419MHz-30.0Msps_raw_abs.npy record/
