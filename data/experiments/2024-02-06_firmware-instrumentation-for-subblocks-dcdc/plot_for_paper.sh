#!/bin/bash

SCRIPT_WD="$(dirname $(realpath $0))"

# * Plot the subclock intermodulation

function plot_sub_clock() {
    export DIR=ff; export FC=2.500e9; export SR=56e6; G=76
    echo DIR=$DIR; echo FC=$FC; echo SR=$SR; echo G=$G
    file=$SCRIPT_WD/$DIR/FC_${FC}_SR_${SR}_${G}db${SUFFIX}.npy
    python3 << EOF
import numpy as np
import matplotlib.pyplot as plt
import lib.plot as libplot
import lib.complex as complex

sig = np.load("$file")

libplot.enable_latex_fonts()
fig, (ax_ampl) = plt.subplots(nrows=1, ncols=1)
ax_ampl.specgram(sig, mode="magnitude", sides="twosided", NFFT=256, Fc=$FC, Fs=$SR)
ax_ampl.set_xlabel("Sample [\#]")
ax_ampl.set_xlim(left=0.1535, right=0.1560)
ax_ampl.set_ylabel("Frequency [Hz]")
#ax_ampl.set_ylim(bottom=2.472e9, top=2.547e9)
ax_ampl.axhline(y=2.496e9, label="2.496 GHz")

# plt.subplots_adjust(top=0.35)
plt.legend()
#plt.show()
plt.savefig("subclock_intermodulation.pdf")
EOF
}

# DONE: Use a custom Python to plot the FF wide band at 2.500e9, keeping only
# the specgram of the amplitude, and show how we can observe the 3rd harmonic of
# the 32 MHz sub-clock at 2.496e9 by looking at the mirror-looking AES signal.
# plot_sub_clock
