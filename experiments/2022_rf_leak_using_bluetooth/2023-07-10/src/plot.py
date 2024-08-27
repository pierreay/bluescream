#!/usr/bin/python3

import os
import numpy as np
import matplotlib.pyplot as plt
import scipy.signal as signal

# Input
SIG_NF_PATH = "/tmp/{}".format(os.getenv("SIG_NF"))
SIG_RF_PATH = "/tmp/{}".format(os.getenv("SIG_RF"))
SIG_SR = int(30e6)

# Processing.
DECIMATION_FACTOR = 1

# Plot configuration
LINEWIDTH = 0.7
SUBPLOT_NUMBER = 4
SUBPLOT_HSPACE = 1

def load_sigs():
    print("load_sigs()")
    sig_nf = np.load(SIG_NF_PATH)
    sig_rf = np.load(SIG_RF_PATH)
    assert(sig_nf is not None)
    assert(sig_rf is not None)
    return sig_nf, sig_rf

def normalize(arr):
    """Apply min-max feature scaling normalization to a 1D array."""
    return (arr - np.min(arr)) / (np.max(arr) - np.min(arr))

def truncate_len(sig1, sig2, sig_sr):
    print("truncate_len()")
    sig1_duration = len(sig1) / sig_sr # [s]
    sig2_duration = len(sig2) / sig_sr # [s]
    if sig1_duration < sig2_duration:
        print("sig1_duration < sig2_duration == True")
        return sig1[0:int(sig1_duration * sig_sr)], sig2[0:int(sig1_duration * sig_sr)]
    elif sig2_duration < sig1_duration:
        print("sig2_duration < sig1_duration == True")
        return sig1[0:int(sig2_duration * sig_sr)], sig2[0:int(sig2_duration * sig_sr)]
    else:
        return sig1, sig2

def plot_init(nsamples, duration, nb = 1):
    print("plot_init(nsamples={}, duration={})".format(nsamples, duration))
    t = np.linspace(0, duration, nsamples)
    plt.subplots_adjust(hspace = SUBPLOT_HSPACE)
    ax_time = plt.subplot(SUBPLOT_NUMBER, 1, nb)
    return t, ax_time

def plot_time(t, data, ax_time, label, title):
    print("plot_time(label={},title={})".format(label, title))
    ax_time.plot(t, data, label = label, lw = LINEWIDTH)
    ax_time.legend(loc="upper right")

    plt.title("Time-Domain [{}]".format(title))
    plt.xlabel("Time [s]")
    plt.ylabel("Amplitude [Normalized]")

    secax = ax_time.secondary_xaxis('top', functions=(lambda x: x - ax_time.get_xlim()[0], lambda x: x))
    secax.set_xlabel("Time (relative to zoom) [s]")
    secax.ticklabel_format(scilimits=(0,0))

def plot_freq(fs, data, ax_time, nb = 1):
    print("plot_freq()")
    ax_specgram = plt.subplot(SUBPLOT_NUMBER, 1, nb, sharex=ax_time)
    ax_specgram.specgram(data, NFFT=256, Fs=fs)
    
    plt.title("Spectrogram")
    plt.xlabel("Time [s]")
    plt.ylabel("Frequency [Hz]")

def plot_show():
    print("plot_show()")
    plt.get_current_fig_manager().full_screen_toggle()
    plt.show(block=True)

if __name__ == "__main__":
    sig_nf, sig_rf = load_sigs()
    if DECIMATION_FACTOR > 1:
        print("DECIMATION_FACTOR={}".format(DECIMATION_FACTOR))
        sig_nf = signal.decimate(sig_nf, DECIMATION_FACTOR, ftype="fir")
        sig_rf = signal.decimate(sig_rf, DECIMATION_FACTOR, ftype="fir")
        SIG_SR = SIG_SR / DECIMATION_FACTOR
    sig_nf = normalize(sig_nf)
    sig_rf = normalize(sig_rf)
    sig_nf, sig_rf = truncate_len(sig_nf, sig_rf, SIG_SR)
    
    nsamples = len(sig_nf)
    duration = nsamples / SIG_SR
    
    t, ax_time = plot_init(nsamples, duration, 1)
    plot_time(t, sig_nf, ax_time, "NF", SIG_NF_PATH)
    plot_freq(SIG_SR, sig_nf, ax_time, 2)

    t, ax_time = plot_init(nsamples, duration, 3)
    plot_time(t, sig_rf, ax_time, "RF", SIG_RF_PATH)
    plot_freq(SIG_SR, sig_rf, ax_time, 4)
    
    plot_show()
