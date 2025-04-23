#!/bin/bash

ssh $REMOTE "cd $REMOTE_WD && source .envrc && python3 ./plot.py"
rsync -avz --progress $REMOTE:/tmp/avg_0.png plot.png
