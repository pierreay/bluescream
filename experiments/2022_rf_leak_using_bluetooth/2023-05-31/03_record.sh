#!/bin/bash

ssh $REMOTE "cd $REMOTE_WD && source .envrc && python3 ./src/record.py"
# rsync -avz --progress $REMOTE:/tmp/rx_signal.npy record/rx_signal_recorded.npy
# tar cjvf record/rx_signal_recorded.npy.tar.bz2 record/rx_signal_recorded.npy
# rm -rf record/rx_signal_recorded.npy
