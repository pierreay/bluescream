#!/bin/bash
ssh $REMOTE "cd $REMOTE_WD && bash -s" < ./src/pair.sh
