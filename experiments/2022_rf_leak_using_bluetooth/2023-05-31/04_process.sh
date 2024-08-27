#!/bin/bash

ssh $REMOTE "cd $REMOTE_WD && source .envrc && python3 ./src/process.py"
# rsync -avz --progress $REMOTE:$REMOTE_HOME/Figure_1.png plot/rx_signal_processed.png
# rsync -avz --progress $REMOTE:$REMOTE_HOME/Figure_2.png plot/rx_signal_processed_zoomed.png
