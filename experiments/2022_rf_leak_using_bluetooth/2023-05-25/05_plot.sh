#!/bin/bash

ssh $REMOTE "cd $REMOTE_WD && source .envrc && python3 ./src/plot.py"
rsync -avz --progress $REMOTE:/tmp/rx_signal_plot.png plot/rx_signal_plot.png
