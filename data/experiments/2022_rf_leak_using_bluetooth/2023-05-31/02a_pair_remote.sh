#!/bin/bash

ssh $REMOTE "cd $REMOTE_WD && bash -s" < ./02b_pair_local.sh
