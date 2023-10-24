"""Plot traces."""

from os import path
import numpy as np
import matplotlib.pyplot as plt

import lib.log as l
import lib.analyze as analyze

# * Global variables

NFFT = 256
USER_SELECT = None

# * Matplotlib wrappers

def show_fullscreen():
    """Show the current plot in fullscreen."""
    plt.get_current_fig_manager().full_screen_toggle()
    plt.show()

# * Simple plots used interactively for debugging

def savetmp(filename):
    plt.savefig(path.join("/tmp", filename))
    plt.close()

def plot_loop(arr, func, nb=0):
    """Iterate over every element of the ARR list or numpy array and apply the
    FUNC plotting function. Break at NB is positive.

    """
    for i in range(len(arr)):
        func(arr[i])
        if nb and i == nb:
            break

def plot_time_simple(s):
    """Show signals' in time-domain on different windows."""
    s = [s] if isinstance(s, np.ndarray) and s.ndim == 1 else s
    assert(len(s) < 15)
    for i in range(len(s)):
        plt.figure()
        plt.plot(s[i])
        plt.title("idx={}".format(i))
    plt.show()

def plot_spec_simple(s):
    """Show signals' spectrogram on different windows."""
    s = [s] if isinstance(s, np.ndarray) and s.ndim == 1 else s
    assert(len(s) < 15)
    for i in range(len(s)):
        plt.figure()
        plt.specgram(s[i], NFFT)
        plt.title("idx={}".format(i))
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

# * Plot components to construct advanced plots

# This section was created to separe plot_time_spec_sync_axis() subfunctions
# in generic functions that would be located here in the future.

# * Special plot for analysis

def plot_time_spec_sync_axis(s_arr, samp_rate=None, peaks=None, triggers=None, cond=True):
    """Plot signals using synchronized time and frequency domains.

    Plot signals contained in the S_ARR array. They must be recorded at the
    sample rate, which can be specified using SAMP_RATE to duration. PEAKS can
    be set to an array of indexes to use as vline. TRIGGERS can be set to to a
    Triggers class containing trigger signals to display. COND can be set to
    False to not plot and return immediatly.

    """
    if cond is False:
        return
    SUBPLOT_NB = len(s_arr) * 2
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
        plt.ylabel("Amplitude")
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

    nsamples = len(s_arr[0])
    if samp_rate is None:
        samp_rate = 1
    duration = nsamples / samp_rate
    for signal_idx, s in enumerate(s_arr):
        assert len(s) == nsamples, "traces should be of the same length!"
        subplot_idx = signal_idx * 2 + 1
        t, ax_time = plot_init(nsamples, duration, subplot_idx)
        plot_time(t, s, ax_time, "idx={}".format(signal_idx))
        if peaks is not None:
            plot_peaks(peaks, ax_time, samp_rate)
        if triggers is not None:
            plot_triggers(triggers, ax_time, t)
        ax_freq = plot_freq(samp_rate, s, ax_time, subplot_idx + 1, triggers)
        if peaks is not None:
            plot_peaks(peaks, ax_freq, samp_rate)
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

# * User interaction

class SignalPlot():
    """Class representing a plot of a signal.

    It allows to easily plot the different components of a signal (amplitude,
    phase) in both time and frequency domains in a uniform way depending on its
    type.

    """
    # Subplot index for amplitude plots.
    IDX_BASE_AMP = 1
    # Subplot index for phase plots.
    IDX_BASE_PHASE = 2

    def __init__(self, sig):
        assert type(sig) == np.ndarray, "sig should be a numpy array"
        # Signal to plot.
        self.sig = sig
        # Compute the number of columns and rows depending on the signal type.
        self.nrows = 2
        self.ncols = 2 if analyze.is_iq(self.sig) else 1

    def __plot_amp(self):
        """Plot the amplitude of the signal in time and frequency domains in a vertical way."""
        sig = analyze.get_amplitude(self.sig)
        plt.subplot(self.nrows, self.ncols, SignalPlot.IDX_BASE_AMP)
        plt.plot(sig)
        plt.title("Amplitude")
        plt.subplot(self.nrows, self.ncols, SignalPlot.IDX_BASE_AMP + self.ncols)
        plt.specgram(sig, NFFT=NFFT)

    def __plot_phase(self):
        """Plot the phase of the signal in time and frequency domains in a vertical way."""
        sig = analyze.get_phase(self.sig)
        plt.subplot(self.nrows, self.ncols, SignalPlot.IDX_BASE_PHASE)
        plt.plot(sig)
        plt.title("Phase")
        plt.subplot(self.nrows, self.ncols, SignalPlot.IDX_BASE_PHASE + self.ncols)
        plt.specgram(sig, NFFT=NFFT)

    def plot(self, block=True):
        """Plot the different components of a signal. If BLOCK is set to False,
        do not block the program execution while plotting."""
        if analyze.is_iq(self.sig):
            self.__plot_amp()
            self.__plot_phase()
        else:
            self.__plot_amp()
        plt.show(block=block)

def select(candidate):
    global USER_SELECT
    USER_SELECT = False
    fig, _ = plt.subplots()
    fig.canvas.mpl_connect('key_press_event', select_input)
    # Ask user confirmation and return choice.
    l.LOGGER.info("Please, press 'y' to select the current trace or 'q' to skip to the next candidate")
    sigplot = SignalPlot(candidate)
    sigplot.plot(block=True)
    return USER_SELECT

def select_input(event):
    global USER_SELECT
    if event.key == 'y':
        USER_SELECT = True
        plt.close()
