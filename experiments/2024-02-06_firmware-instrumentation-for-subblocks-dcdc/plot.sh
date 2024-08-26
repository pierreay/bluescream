#!/bin/bash

SCRIPT_WD="$(dirname $(realpath $0))"

function plot_display() {
    export SR=$3; export FC=$2; export G=$4; export DIR=$1; export SUFFIX=$5
    echo SR=$SR; echo FC=$FC; echo G=$G; DIR=$DIR; SUFFIX=$SUFFIX
    cd $SC_SRC
    ./radio.py plot-file $SR --freq $FC $SCRIPT_WD/$DIR/FC_${FC}_SR_${SR}_${G}db${SUFFIX}.npy --npy --no-cut
}

# * Compare NF wide-band and NF narrow-band

# DONE:
# plot_display nf 128e6 30e6 76 &
# plot_display nf 138e6 8e6 76

# NOTE of todo: Use a custom Python to plot the NF narrow band, without x axis
# sync, and show how the full AES looks like in amplitude for both time and
# frequency.

# * Compare FF wide-band

# DONE:
# plot_display ff 2.500e9 56e6 76 &
# plot_display ff 2.545e9 56e6 76

# NOTE of todo: Use a custom Python to plot the FF wide band at 2.500e9,
# keeping only the specgram of the amplitude, and show how we can observe the
# 3rd harmonic of the 32 MHz sub-clock at 2.496e9 by looking at the
# mirror-looking AES signal.

echo Subclocks at 16 MHz harmonics:
echo "2.400e9 + (3 * 16e6) = 2448000000."
echo "2.400e9 + (4 * 16e6) = 2464000000."
echo "2.400e9 + (5 * 16e6) = 2480000000."
echo "2.400e9 + (6 * 16e6) = 2496000000."
echo "2.400e9 + (7 * 16e6) = 2512000000."
echo "2.400e9 + (8 * 16e6) = 2528000000."
echo "2.400e9 + (9 * 16e6) = 2544000000."
echo "2.400e9 + (10 * 16e6) = 2560000000."
echo "2.400e9 + (11 * 16e6) = 2576000000."
echo "2.400e9 + (12 * 16e6) = 2592000000."
echo "2.400e9 + (13 * 16e6) = 2608000000."

echo Subclocks at 32 MHz harmonics:
echo "2.400e9 + (2 * 32e6) = 2464000000."
echo "2.400e9 + (3 * 32e6) = 2496000000."
echo "2.400e9 + (4 * 32e6) = 2528000000."
echo "2.400e9 + (5 * 32e6) = 2560000000."
echo "2.400e9 + (6 * 32e6) = 2592000000."

# * Compare FF narrow-band

# DONE:
# plot_display ff 2.400e9 5e6 40 &
# plot_display ff 2.510e9 8e6 76 &
# plot_display ff 2.512e9 8e6 76

# NOTE of todo: Use a custom Python to plot the FF narrow band at 2.510e8,
# without x axis sync, and show how the full AES looks like in amplitude for
# both time and frequency.

# * Compare DCDC register

# DONE:
# plot_display ff 2.400e9 5e6 40 &
# plot_display ff 2.400e9 5e6 40 _dcdc-on

# DONE:
# plot_display ff 2.512e9 8e6 76 &
# plot_display ff 2.512e9 8e6 76 _dcdc-on
