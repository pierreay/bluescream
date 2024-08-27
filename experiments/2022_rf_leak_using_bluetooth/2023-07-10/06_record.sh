#!/bin/bash
ssh $REMOTE "cd $REMOTE_WD && source .envrc && python3 ./src/record.py"
# For local analysis:
# rsync -avz --progress $REMOTE:/tmp/$SIG_NF /tmp
# rsync -avz --progress $REMOTE:/tmp/$SIG_RF /tmp
