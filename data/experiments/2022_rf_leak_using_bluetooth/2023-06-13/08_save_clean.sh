#!/bin/bash
file="record/USRP_0-127.0MHz-30.0Msps_raw_abs.npy"
tar cjvf $file.tar.bz2 $file
file="record/USRP_1-2.419MHz-30.0Msps_raw_abs.npy"
tar cjvf $file.tar.bz2 $file
