#!/bin/bash
mkdir -p $DIR_CSV
# Local analysis:
# ./src/post-process.py
# Remote analysis:
ssh reaper "cd $REMOTE_WD && source .envrc && python3" < ./src/post-process.py
