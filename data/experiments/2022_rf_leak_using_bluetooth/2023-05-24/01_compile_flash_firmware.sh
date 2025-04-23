#!/bin/bash

ssh $REMOTE "cd $REMOTE_NIMBLE && make all"
rsync -avz --progress $REMOTE:/tmp/mynewt-firmware.hex firmware-nimble.hex
