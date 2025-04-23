#!/bin/bash

ssh $REMOTE "cd $REMOTE_NIMBLE && make all"
rsync -avz --progress $REMOTE:/tmp/mynewt-firmware.hex build/firmware-nimble.hex
