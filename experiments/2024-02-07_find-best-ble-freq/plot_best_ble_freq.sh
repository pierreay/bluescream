#!/bin/bash

export PYTHONPATH=/home/drac/git/screaming_channels_ble/src
dir="$(dirname $(realpath $0))"
echo dir=$dir

function plot_display() {
    export SR=8e6; export FC=$1; export G=76;
    echo SR=$SR; echo FC=$FC; echo G=$G
    file=$dir/fc_${FC}_sr_${SR}_g_${G}db_aes.npy
    python3 << EOF
import numpy as np
import matplotlib.pyplot as plt
import lib.plot as libplot
import lib.complex as complex

sig = np.load("$file")

libplot.enable_latex_fonts()
fig, (ax_ampl, ax_phase) = plt.subplots(nrows=1, ncols=2)
ax_ampl.plot(complex.get_amplitude(sig))
ax_ampl.set_xlabel("Sample [\#]")
ax_ampl.set_ylabel("Amplitude [ADC Value]")
ax_phase.plot(complex.get_phase_rot(sig))
ax_phase.set_xlabel("Sample [\#]")
ax_phase.set_ylabel("Phase rotation [Radian]")

plt.subplots_adjust(top=0.35)
plt.show()
EOF
}

plot_display 2.533e9
mv ~/Figure_1.png $dir/plot_best_ble_freq.png
mv ~/Figure_1.svg $dir/plot_best_ble_freq.svg
mv ~/Figure_1.pdf $dir/plot_best_ble_freq.pdf
