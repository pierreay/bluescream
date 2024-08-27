#!/usr/bin/env python3

import os
import numpy as np
from matplotlib import pyplot as plt
from scipy import signal
from scipy.signal import butter, lfilter

# * Configuration

# Inputs
SIG_NF_PATH = "record/{}".format(os.getenv("SIG_NF"))
SIG_RF_PATH = "record/{}".format(os.getenv("SIG_RF"))
SIG_SR = int(30e6)

# Trigger(s)
TRG_BP_LOW  = [9.0e6, 4.5e6]
TRG_BP_HIGH = [9.4e6, 6.8e6]
assert(len(TRG_BP_LOW) == len(TRG_BP_HIGH))
TRG_NB = len(TRG_BP_LOW)
TRG_LP = 1e3
TRG_LP_ORDER = 4

# Plot configuration
SUBPLOT_NUMBER = 2
SUBPLOT_HSPACE = 0.5

# * Signals

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

# * Filters

def butter_bandpass(lowcut, highcut, fs, order=5):
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq
    b, a = butter(order, [low, high], btype="band")
    return b, a

def butter_bandpass_filter(data, lowcut, highcut, fs, order=5):
    b, a = butter_bandpass(lowcut, highcut, fs, order=order)
    y = lfilter(b, a, data)
    return y

def butter_lowpass(cutoff, fs, order=5):
    nyq = 0.5 * fs
    normal_cutoff = cutoff / nyq
    b, a = butter(order, normal_cutoff, btype="low", analog=False)
    return b, a

def butter_lowpass_filter(data, cutoff, fs, order=5):
    b, a = butter_lowpass(cutoff, fs, order=order)
    y = lfilter(b, a, data)
    return y

# * Plot

def plot_init(nsamples, duration, nb = 1):
    print("plot_init(nsamples={}, duration={})".format(nsamples, duration))
    t = np.linspace(0, duration, nsamples)
    plt.subplots_adjust(hspace = SUBPLOT_HSPACE)
    ax_time = plt.subplot(SUBPLOT_NUMBER, 1, nb)
    return t, ax_time

def plot_time(t, data, ax_time, label):
    print("plot_time(label={})".format(label))
    ax_time.plot(t, data, label = label, lw = 0.7)
    ax_time.legend(loc="upper right")

    plt.title("Time-Domain")
    plt.xlabel("Time [s]")
    plt.ylabel("Amplitude [Normalized]")

    secax = ax_time.secondary_xaxis('top', functions=(lambda x: x - ax_time.get_xlim()[0], lambda x: x))
    secax.set_xlabel("Time (relative to zoom) [s]")
    secax.ticklabel_format(scilimits=(0,0))

def plot_peaks(peaks, ax):
    i = 0
    for idx in peaks:
        i = i + 1
        ax.axvline(x = idx / SIG_SR, color = "b", label = 'peak={}'.format(i), ls = "--", lw = 0.75)

def plot_freq(fs, data, ax_time, nb = 1, triggers = None):
    print("plot_freq()")
    ax_specgram = plt.subplot(SUBPLOT_NUMBER, 1, nb, sharex=ax_time)
    ax_specgram.specgram(data, NFFT=256, Fs=fs)

    if triggers is not None:
        for idx in list(range(triggers.nb_composed())):
            ax_specgram.axhline(y=triggers.bandpass_low[idx], color='b', label = "trg(idx={}).bandpass_low".format(idx), lw = 0.3)
            ax_specgram.axhline(y=triggers.bandpass_high[idx], color='b', label = "trg(idx={}).bandpass_high".format(idx), lw = 0.3)

    plt.title("Spectrogram")
    plt.xlabel("Time [s]")
    plt.ylabel("Frequency [Hz]")
    return ax_specgram

def plot_show():
    print("plot_show()")
    plt.get_current_fig_manager().full_screen_toggle()
    plt.show(block=True)

# * Trigger

class Triggers():
    def __init__(self):
        self.triggers = []
        self.bandpass_low = []
        self.bandpass_high = []
        pass
    def add(self, t):
        self.triggers.append(t)
        self.bandpass_low.append(t.bandpass_low)
        self.bandpass_high.append(t.bandpass_high)
    def get(self, idx):
        return self.triggers[idx]
    def nb(self):
        return len(self.triggers)
    def nb_composed(self):
        return len(self.bandpass_low)
    def reduce_add(self):
        while self.nb() > 1:
            print("Triggers.reduce_add().nb()={}".format(self.nb()))
            trigger = self.triggers.pop()
            self.triggers[0].signal += trigger.signal
        self.triggers[0].signal = normalize(self.triggers[0].signal)
        print("Triggers.reduce_add().nb()={}".format(self.nb()))

class Trigger():
    def __init__(self, s, bpl, bph, lp):
        self.bandpass_low = bpl
        self.bandpass_high = bph
        self.lowpass = lp
        signal = butter_bandpass_filter(s, bpl, bph, SIG_SR)
        signal = np.abs(signal)
        signal = butter_lowpass_filter(signal, lp, SIG_SR, TRG_LP_ORDER)
        signal = normalize(signal)
        self.signal = signal

# * Output

def store_csv(x, file):
    print("store_csv(x={}, file={})".format(x, file))
    with open(file, 'w', newline='') as f:
        for item in x:
            f.write(str(item))
            f.write(";")

# * Script

def post_process_nf(sig_nf, nsamples, duration):
    print("post_process_nf()")
    # * Triggering.
    # Create trigger signals.
    sig_nf_triggers = Triggers()
    for idx in list(range(TRG_NB)):
        sig_nf_triggers.add(Trigger(sig_nf, TRG_BP_LOW[idx], TRG_BP_HIGH[idx], TRG_LP))
    sig_nf_triggers.reduce_add()
    # Create trigger indexes.
    peaks = signal.find_peaks(sig_nf_triggers.get(0).signal, distance=SIG_SR/10, prominence=1/2)
    print("peaks_nb={}".format(len(peaks[0])))
    # Store trigger indexes.
    store_csv(peaks[0], "{}/nf_peaks.csv".format(os.getenv("DIR_CSV")))

    # * Plotting.
    t, ax_time = plot_init(nsamples, duration, 1)
    plot_time(t, sig_nf, ax_time, "sig_nf")
    plot_peaks(peaks[0], ax_time)
    for idx in list(range(sig_nf_triggers.nb())):
        trg = sig_nf_triggers.get(idx)
        plot_time(t, trg.signal, ax_time, "sig_nf_triggers(idx={}, trg.lowpass={:.3e})".format(idx, trg.lowpass))
    ax_freq = plot_freq(SIG_SR, sig_nf, ax_time, 2, sig_nf_triggers)
    plot_peaks(peaks[0], ax_freq)
    plot_show()

def post_process_rf(sig_rf, nsamples, duration):
    print("post_process_rf()")
    # * Plotting.
    t, ax_time = plot_init(nsamples, duration, 1)
    plot_time(t, sig_rf, ax_time, "sig_rf")
    ax_freq = plot_freq(SIG_SR, sig_rf, ax_time, 2)
    plot_show()

if __name__ == "__main__":
    # * Loading.
    sig_nf, sig_rf = load_sigs()
    sig_nf = normalize(sig_nf)
    sig_rf = normalize(sig_rf)
    sig_nf, sig_rf = truncate_len(sig_nf, sig_rf, SIG_SR)
    nsamples = len(sig_nf)
    duration = nsamples / SIG_SR

    # * Post-process near-field trace.
    post_process_nf(sig_nf, nsamples, duration)
    # * Post-process radio-frequency trace.
    post_process_rf(sig_rf, nsamples, duration)
