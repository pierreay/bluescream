#!/bin/bash
mv $DIR_RECORD/$SIG_NF $DIR_RECORD/${SIG_NF/.npy/_$(date "+%Y-%m-%d_%H-%M-%S").npy}
mv $DIR_RECORD/$SIG_RF $DIR_RECORD/${SIG_RF/.npy/_$(date "+%Y-%m-%d_%H-%M-%S").npy}
