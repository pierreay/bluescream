#!/usr/bin/env python3

import numpy as np
from matplotlib import pyplot as plt
from matplotlib import mlab

# Sample rate [samples / s], hence defining the bandwidth.
fs = 30e6
# Center frequency [Hz].
freq = 127e6
# Signal file.
rx_signal = np.load("record/rx_signal_recorded.npy")

print("Signal samples: {}".format(len(rx_signal)))
print("Signal samples type: {}".format(type(rx_signal[0])))

def myplot(rx_signal):
    plt.figure()
    ax_time = plt.subplot(2, 1, 1)
    t = np.linspace(0, len(rx_signal) / fs, len(rx_signal))
    ax_time.plot(t, rx_signal)
    plt.title("Time-Domain")
    plt.xlabel("Time [s]")
    plt.ylabel("Magnitude [Complex Number]")

    ax_specgram = plt.subplot(2, 1, 2, sharex=ax_time)
    ax_specgram.specgram(rx_signal, NFFT=256, Fs=fs, Fc=0,
                 detrend=mlab.detrend_none, window=mlab.window_hanning,
                 noverlap=127, cmap=None, xextent=None, pad_to=None,
                 sides='default', scale_by_freq=None, mode='default', scale='default')
    plt.title("Spectrogram")
    plt.xlabel("Time [s]")
    plt.ylabel("Frequency (Hz)")
    plt.show()

# 1. Plot signal:
myplot(rx_signal)

# 2. Shrink signal:
myplot(rx_signal[int(len(rx_signal) * 0.075) : int(len(rx_signal) * 0.21)])
