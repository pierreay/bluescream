#!/bin/bash

ssh $REMOTE "cd $REMOTE_WD && source .envrc && python3 ./process.py"
rsync -avz --progress $REMOTE:/tmp/avg_0.npy process.npy
rsync -avz --progress $REMOTE:$REMOTE_HOME/Figure_1.png process.png
