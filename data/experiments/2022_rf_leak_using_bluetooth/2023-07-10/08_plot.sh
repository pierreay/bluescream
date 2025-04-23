#!/bin/bash
mkdir -p $DIR_PLOT
# Local analysis:
# ./src/plot.py
# Remote analysis:
ssh reaper "cd $REMOTE_WD && source .envrc && python3" < ./src/plot.py
