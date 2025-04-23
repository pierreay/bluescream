#!/bin/bash
ssh $REMOTE "cd $REMOTE_WD && source .envrc && python3 ./src/record.py"
# rsync -avz --progress $REMOTE:/tmp/rx_signal.npy $DIR_RECORD/rx_signal_recorded.npy
# tar cjvf $DIR_RECORD/rx_signal_recorded.npy.tar.bz2 $DIR_RECORD/rx_signal_recorded.npy
# rm -rf $DIR_RECORD/rx_signal_recorded.npy
