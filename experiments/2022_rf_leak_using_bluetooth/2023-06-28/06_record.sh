#!/bin/bash
ssh $REMOTE "cd $REMOTE_WD && source .envrc && python3 ./src/record.py"
mkdir -p record/
rsync -avz --progress $REMOTE:"/tmp/$SIG_NF" record/
rsync -avz --progress $REMOTE:"/tmp/$SIG_RF" record/
