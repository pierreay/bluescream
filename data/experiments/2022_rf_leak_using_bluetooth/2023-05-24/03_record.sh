#!/bin/bash

ssh $REMOTE "cd $REMOTE_WD && source .envrc && python3 ./record.py"
