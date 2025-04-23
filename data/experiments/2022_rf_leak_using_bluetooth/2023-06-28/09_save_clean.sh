#!/bin/bash
tar cjvf $DIR_RECORD/$SIG_NF.tar.bz2 $DIR_RECORD/$SIG_NF
rm -rf $DIR_RECORD/$SIG_NF
tar cjvf $DIR_RECORD/$SIG_RF.tar.bz2 $DIR_RECORD/$SIG_RF
rm -rf $DIR_RECORD/$SIG_RF
