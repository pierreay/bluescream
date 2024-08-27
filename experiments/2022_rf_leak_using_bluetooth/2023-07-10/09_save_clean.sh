#!/bin/bash
key='a4b39a14-8f44-4ef9-a5e2-21503c3dbec1'
ssh $REMOTE "mkdir $REMOTE_ANNEX/$key"
ssh $REMOTE "cd $REMOTE_ANNEX/$key && mv /tmp/$SIG_NF ./${SIG_NF/.npy/_$(date "+%Y-%m-%d_%H-%M-%S").npy}"
ssh $REMOTE "cd $REMOTE_ANNEX/$key && mv /tmp/$SIG_RF ./${SIG_RF/.npy/_$(date "+%Y-%m-%d_%H-%M-%S").npy}"
ssh $REMOTE "cd $REMOTE_ANNEX/$key && git add ."
ssh $REMOTE "cd $REMOTE_ANNEX/$key && git annex sync"
