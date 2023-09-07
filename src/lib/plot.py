"""Plot traces."""

from os import path
import numpy as np
import matplotlib.pyplot as plt

# * Global variables

NFFT = 256

# * Matplotlib wrappers

def show_fullscreen():
    """Show the current plot in fullscreen."""
    plt.get_current_fig_manager().full_screen_toggle()
    plt.show()

# * Simple plots used interactively for debugging

def savetmp(filename):
    plt.savefig(path.join("/tmp", filename))
    plt.close()

def plot_time_simple(s):
    plt.plot(s)
    plt.show()

def plot_spec_simple(s):
    plt.specgram(s, NFFT)
    plt.show()

def save_spec_simple(s, i=0):
    plt.specgram(s, NFFT)
    savetmp("spec{}.png".format(i))

def plot_simple(s):
    plot_time_simple(s)
    plot_spec_simple(s)

def plot_time_compare_2(s1, s2):
    assert(s1.shape == s2.shape)
    plot_time_compare_n(np.array([s1, s2]))

def plot_time_compare_n(arr):
    """Show a single time-domain plot superposing every traces contained the 2D
    np.array ARR."""
    assert(len(arr) < 1000) # To not consume too much memory.
    for idx in range(len(arr)):
        plt.plot(arr[idx])
    plt.show()

def plot_spec_compare(s1, s2):
    assert(s1.shape == s2.shape)
    plt.specgram(s1, NFFT)
    savetmp("spec1.png")
    plt.specgram(s2, NFFT)
    savetmp("spec2.png")

# * Plot components to construct advanced plots

# This section was created to separe plot_time_spec_share_nf_ff() subfunctions
# in generic functions that would be located here.

# * Special plot for analysis

def plot_time_spec_share_nf_ff(nf, ff, samp_rate, peaks=None, triggers=None):
    """Screaming Channels templating main plot, displaying NF and FF recordings
    (each one being a 1D np.array). Originaly taken from "plot" subcommand of
    "collect.py".

    """
    SUBPLOT_NB = 4 if ff is not None else 2
    def plot_init(nsamples, duration, nb = 1):
        t = np.linspace(0, duration, nsamples)
        plt.subplots_adjust(hspace = 1)
        ax_time = plt.subplot(SUBPLOT_NB, 1, nb)
        return t, ax_time
    
    def plot_time(t, data, ax_time, label, title=""):
        ax_time.plot(t, data, label = label, lw = 0.7)
        ax_time.legend(loc="upper right")
        plt.title("Time-Domain [{}]".format(title))
        plt.xlabel("Time [s]")
        plt.ylabel("Amplitude [Normalized]")
        secax = ax_time.secondary_xaxis('top', functions=(lambda x: x - ax_time.get_xlim()[0], lambda x: x))
        secax.set_xlabel("Time (relative to zoom) [s]")
        secax.ticklabel_format(scilimits=(0,0))
        
    def plot_freq(fs, data, ax_time, nb = 1, triggers = None):
        ax_specgram = plt.subplot(SUBPLOT_NB, 1, nb, sharex=ax_time)
        ax_specgram.specgram(data, NFFT=256, Fs=fs)
        if triggers is not None:
            for idx in list(range(triggers.nb_composed())):
                ax_specgram.axhline(y=triggers.bandpass_low[idx], color='b', label = "trg(idx={}).bandpass_low".format(idx), lw = 0.3)
                ax_specgram.axhline(y=triggers.bandpass_high[idx], color='b', label = "trg(idx={}).bandpass_high".format(idx), lw = 0.3)
        plt.title("Spectrogram")
        plt.xlabel("Time [s]")
        plt.ylabel("Frequency [Hz]")
        return ax_specgram

    def plot_peaks(peaks, ax, sr):
        """Plot the vertical lines's indexes contained in PEAKS list on the
        Matplotlib axis AX representing time-domain using SR sampling rate.

        """
        for idx in peaks:
            ax.axvline(x = idx / sr, color = "b", ls = "--", lw = 0.75)

    def plot_triggers(triggers, ax, t):
        for idx in list(range(triggers.nb())):
            trg = triggers.get(idx)
            plot_time(t, trg.signal, ax, "triggers(idx={}, trg.lowpass={:.3e})".format(idx, trg.lowpass))
        if triggers.threshold is not None:
            ax.axhline(triggers.threshold, label="trigger threshold")

    nsamples = len(nf)
    duration = nsamples / samp_rate
    t, ax_time = plot_init(nsamples, duration, 1)
    plot_time(t, nf, ax_time, "NF")
    if peaks is not None:
        plot_peaks(peaks, ax_time, samp_rate)
    if triggers is not None:
        plot_triggers(triggers, ax_time, t)
    ax_freq = plot_freq(samp_rate, nf, ax_time, 2, triggers)
    if peaks is not None:
        plot_peaks(peaks, ax_freq, samp_rate)
    if ff is not None:
        t, ax_time = plot_init(nsamples, duration, 3)
        plot_time(t, ff, ax_time, "RF")
        plot_freq(samp_rate, ff, ax_time, 4)
    show_fullscreen()

def plot_metadata_balance(ks, pt):
    """Take 2D np.array of KS keys and PT plaintexts, show a boxplot of imbalance"""
    sbi = ks ^ pt
    cnt = [0] * len(sbi[0])
    for i in range(len(sbi[0])):
        sbiu = np.unique(sbi[:, i], return_counts=True)
        cnt[i] = sbiu[1]
    plt.boxplot(cnt)
    plt.title("balance for each subbyte in dataset")
    plt.suptitle("(perfect balance = very tight box around average at (nb_trace / 256))")
    plt.xlabel("subbyte")
    plt.ylabel("count")
    plt.show()
