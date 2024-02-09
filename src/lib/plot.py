"""Plot traces."""

from os import path
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Button, Slider
from scipy import signal

import lib.log as l
import lib.analyze as analyze
import lib.complex as complex
import lib.load as load

# * Global variables

NFFT = 256
USER_SELECT = None

# * Matplotlib wrappers

def enable_latex_fonts():
    """Use LaTeX for text rendering."""
    # Use pdflatex to generate fonts.
    plt.rcParams.update({
        "text.usetex": True,
        "font.family": "Computer Modern",
        "font.size": 15
    })

def show_fullscreen():
    """Show the current plot in fullscreen."""
    plt.get_current_fig_manager().full_screen_toggle()
    plt.show()

# * Simple plots used interactively for debugging

def savetmp(filename):
    plt.savefig(path.join("/tmp", filename))
    plt.close()

def plot_time_overwrite(traces, align=False, align_sr=0, start=0, end=0):
    """Plot the amplitude component of all signals contained in the 2D numpy
    array TRACES in time-domain on a single figure.

    Allows to truncate the traces using the START and the END indexes.

    Allows to align the traces before the plot and after the truncation using
    the ALIGN bool and the ALIGN_SR sampling rate.

    """
    # Pre-process traces.
    traces = complex.get_comp(traces, complex.CompType.AMPLITUDE)
    traces = load.truncate(traces, start, end)
    if align is True and align_sr != 0:
        traces = analyze.align_all(traces, align_sr, tqdm_log=True)
    # Plot all traces in time-domain.
    for trace in traces:
        plt.plot(trace)
    plt.show()

def plot_loop(arr, func, nb=0):
    """Iterate over every element of the ARR list or numpy array and apply the
    FUNC plotting function. Break at NB is positive.

    """
    for i in range(len(arr)):
        func(arr[i])
        if nb and i == nb:
            break

def plot_time_simple(s, comp=complex.CompType.AMPLITUDE):
    """Show signals' in time-domain on different windows.

    COMP can be set to enumeration of AMPLITUDE or PHASE to print only one
    component of a complex signal.

    """
    s = [s] if isinstance(s, np.ndarray) and s.ndim == 1 else s
    assert(len(s) < 15)
    for i in range(len(s)):
        # Get the corresponding component of the signal.
        s_i = complex.get_comp(s[i], comp)
        plt.figure()
        plt.plot(s_i)
        plt.title("idx={}".format(i))
    plt.show()

def plot_spec_simple(s, comp=complex.CompType.AMPLITUDE):
    """Show signals' spectrogram on different windows.

    COMP can be set to enumeration of AMPLITUDE or PHASE to print only one
    component of a complex signal.

    """
    s = [s] if isinstance(s, np.ndarray) and s.ndim == 1 else s
    assert(len(s) < 15)
    for i in range(len(s)):
        # Get the corresponding component of the signal.
        s_i = complex.get_comp(s[i], comp)
        plt.figure()
        plt.specgram(s_i, NFFT)
        plt.title("idx={}".format(i))
    plt.show()

def plot_simple(s, comp=complex.CompType.AMPLITUDE):
    """Plot signal(s) in time and frequency domains.

    COMP can be set to enumeration of AMPLITUDE or PHASE to print only one
    component of a complex signal.

    """
    plot_time_simple(s, comp=comp)
    plot_spec_simple(s, comp=comp)

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

def plot_time_spec_sync_axis(s_arr, samp_rate=None, peaks=None, triggers=None, cond=True, comp=complex.CompType.AMPLITUDE, norm=False, xtime=True, title="", fast=False):
    """Plot signals using synchronized time and frequency domains.

    Plot signals contained in the S_ARR 2D np.ndarray or list containing 1D
    np.ndarray. They must be recorded at the same sample rate, which can be
    specified using SAMP_RATE to show duration.

    - PEAKS can be set to an array of indexes to use as vline.
    - TRIGGERS can be set to to a Triggers class containing trigger signals to
      display.
    - COND can be set to False to not plot and return immediatly.
    - COMP can be set to enumeration of AMPLITUDE or PHASE to print only one
      component of a complex signal.
    - NORM can be set to True to normalize each signals individually.
    - XTIME can be set to False to always display sample index on the X axis
      instead of time in seconds.
    - TITLE can be set to a string to set a plot title.
    - FALSE can be to True to speed-up plotting by decimating the signal.

    """
    assert type(s_arr) == list or type(s_arr) == np.ndarray, "Not a list or an array!"
    assert type(s_arr) == np.ndarray and s_arr.ndim == 2 if type(s_arr) == list is False else True, "Bad dimensions for Numpy array!"
    # NOTE: Tried to implement a non-blocking version of this function, but
    # when using plt.plot(block=False) and re-entering this function again for
    # another plot, both plots are plotted on same figure.
    if cond is False:
        return
    # Get the corresponding component of the signal and convert s_arr into Numpy array.
    s_arr = complex.get_comp(np.array(s_arr), comp)
    # Normalize if requested.
    if norm is True:
        s_arr = analyze.normalize(s_arr)
    SUBPLOT_NB = len(s_arr) * 2
    XLABEL = "Time [s]" if xtime is True else "Sample [#]"

    # Decimate signal if needed to increase plotting speed.
    if fast is True:
        factor = int(samp_rate / 1e6)
        l.LOGGER.info("Perform signal decimation using {} as factor".format(factor))
        s_arr = signal.decimate(s_arr, factor)
        samp_rate /= factor
    
    def plot_init(nsamples, duration, nb = 1):
        plt.suptitle(title)
        t = np.linspace(0, duration, nsamples)
        plt.subplots_adjust(hspace = 1)
        ax_time = plt.subplot(SUBPLOT_NB, 1, nb)
        return t, ax_time

    def plot_time(t, data, ax_time, label):
        if xtime is True:
            ax_time.plot(t, data, label = label, lw = 0.7)
        else:
            ax_time.plot(data, label = label, lw = 0.7)
        ax_time.legend(loc="upper right")
        plt.xlabel(XLABEL)
        if comp == complex.CompType.AMPLITUDE:
            plt.ylabel("Amplitude")
        else:
            plt.ylabel("Phase")
        secax = ax_time.secondary_xaxis('top', functions=(lambda x: x - ax_time.get_xlim()[0], lambda x: x))
        secax.set_xlabel("Relative time [s]")
        secax.ticklabel_format(scilimits=(0,0))

    def plot_freq(fs, data, ax_time, nb = 1, triggers = None):
        ax_specgram = plt.subplot(SUBPLOT_NB, 1, nb, sharex=ax_time)
        ax_specgram.specgram(data, NFFT=256, Fs=fs)
        if triggers is not None:
            for idx in list(range(triggers.nb_composed())):
                ax_specgram.axhline(y=triggers.bandpass_low[idx], color='b', label = "trg(idx={}).bandpass_low".format(idx), lw = 0.3)
                ax_specgram.axhline(y=triggers.bandpass_high[idx], color='b', label = "trg(idx={}).bandpass_high".format(idx), lw = 0.3)
        plt.xlabel(XLABEL)
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
    plt.show()

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

class SignalQuadPlot():
    """Quad plot of a signal.

    Plot the amplitude and the phase of a signal in both time and frequency
    domains. The phase is only plotted if the signal is complex.

    """
    # Signal variables.

    # Signal to plot [np.ndarray].
    sig = None
    # Sampling rate of the plotted signal [Msps].
    sr = None
    # Center frequency of the plotted signal [Hz].
    fc = None
    # Duration of the plotted signal [s].
    duration = None

    # Plotting variables.

    # Number of rows [integer].
    nrows = None
    # Number of columns [integer].
    ncols = None
    # If we sould use a shared x axis accross plot [bool].
    sync = False
    # Time vector used for shared x axis [np.ndarray].
    t = None
    # Amplitude time-domain axes [Matplotlib Axes].
    ax_ampl_time = None
    # Amplitude frequency-domain axes [Matplotlib Axes].
    ax_ampl_freq = None
    # Phase time-domain axes [Matplotlib Axes].
    ax_phase_time = None
    # Phase frequency-domain axes [Matplotlib Axes].
    ax_phase_freq = None

    def __init__(self, sig, sr = None, fc = None):
        assert type(sig) == np.ndarray, "sig should be a numpy array (np.ndarray)!"
        self.sig = sig
        self.sr = sr
        self.fc = fc
        # Compute the duration of the signal if possible.
        if sr is not None:
            self.duration = len(sig) / sr
        # Compute the number of columns and rows depending on the signal type.
        self.nrows = 2
        self.ncols = 2 if complex.is_iq(self.sig) else 1
        # Use a shared x-axis only if duration is available for time vector
        # creation.
        if self.duration is not None:
            self.sync = True

    def __plot_amp(self):
        """Plot the amplitude of the signal in time and frequency domains in a vertical way."""
        sig = complex.get_amplitude(self.sig)
        if self.sync is True:
            self.ax_ampl_time.plot(self.t, sig)
            self.ax_ampl_freq.set_xlabel("Time [s]")
        else:
            self.ax_ampl_time.plot(sig)
            self.ax_ampl_time.set_xlabel("Sample [#]")
            self.ax_ampl_freq.set_xlabel("Sample [#]")
        self.ax_ampl_freq.specgram(self.sig, NFFT=NFFT, Fs=self.sr, Fc=self.fc, sides="twosided", mode="magnitude")
        self.ax_ampl_time.set_ylabel("Amplitude [ADC value]")
        self.ax_ampl_freq.set_ylabel("Frequency [Hz]")

    def __plot_phase(self):
        """Plot the phase of the signal in time and frequency domains in a vertical way."""
        # Filter the signal for better visualization then compute phase rotation:
        sos = signal.butter(1, 2e6, 'low', fs=self.sr, output='sos')
        sig = np.array(signal.sosfilt(sos, self.sig), dtype=np.complex64) # NOTE: sosfilt returns np.complex128.
        sig = complex.get_phase_rot(sig)
        if self.sync is True:
            self.ax_phase_time.plot(self.t, sig)
            self.ax_phase_freq.set_xlabel("Time [s]")
        else:
            self.ax_phase_time.plot(sig)
            self.ax_phase_time.set_xlabel("Sample [#]")
            self.ax_phase_freq.set_xlabel("Sample [#]")
        self.ax_phase_freq.specgram(sig, NFFT=NFFT, Fs=self.sr, Fc=self.fc)
        self.ax_phase_time.set_ylabel("Phase rotation [Radian]")
        self.ax_phase_freq.set_ylabel("Frequency [Hz]")

    def plot(self, block=True, save=None, title=None):
        """Plot the different components of a signal.

        :param block: If set to False, do not block the program execution while
        plotting.

        :param save: If set to a file path, use this to save the plot instead
        of interactive display.

        :param title: If set to a string, use it as plot title.

        """
        assert self.nrows == 2, "Bad nrows value"
        assert self.ncols == 1 or self.ncols == 2, "Bad ncols value"
        # Create the plot layout.
        sharex = "col" if self.sync is True else None
        if self.ncols == 1:
            self.fig, (self.ax_ampl_time, self.ax_ampl_freq) = plt.subplots(nrows=self.nrows, ncols=self.ncols, sharex=sharex)
        elif self.ncols == 2:
            self.fig, ((self.ax_ampl_time, self.ax_phase_time), (self.ax_ampl_freq, self.ax_phase_freq)) = plt.subplots(nrows=self.nrows, ncols=self.ncols, sharex=sharex)
        # Generate a time vector if shared x-axis is required.
        if self.sync is True:
            self.t = np.linspace(0, self.duration, len(self.sig))
            assert len(self.t) == len(self.sig), "Bad length matching between time vector and signal!"
            # NOTE: For plt.specgram():
            # - If Fs is not set, it will generates an x-axis of "len(self.sig) / 2".
            # - If Fs is set, it will generates an x-axis of "duration * sampling rate".
        self.__plot_amp()
        if self.ncols == 2:
            self.__plot_phase()
        # Enable tight_layout for larger plots.
        plt.tight_layout()
        # Add the title if needed.
        if title is not None and title != "":
            self.fig.suptitle(title)
        if save is None or save == "":
            plt.show(block=block)
        else:
            plt.savefig(save, dpi=600)

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

class PlotOnce():
    """Plot only once by switching off the flag."""

    def __init__(self, default=True):
        self.state = default

    def pop(self):
        val = self.get()
        self.off()
        return val

    def get(self):
        return self.state is True

    def off(self):
        self.state = False
 
class PlotShrink():
    """Plot signal and visually skrink it.

    Plot the amplitude of a signal in temporal and frequency domain and interactively shrink the signal.

    Typical use case:

    pltshrk = PlotShrink(signal)
    # The user will visually shrink the signal.
    pltshrk.plot()
    # Get the result.
    signal = pltshrk.get_signal()

    """
    # Plotted signal (numpy ND array of complex numbers).
    signal = None
    # Matplotlib main figure (from plt.subplots()).
    fig = None
    # Matplotlib axis for temporal plot (from plt.subplots()).
    axampl = None
    # Matplotlib axis for frequential plot (from plt.subplots()).
    axspec = None
    # Integer defining the current lower bound of the signal.
    lb = None
    # Integer defining the current uper bound of the signal.
    ub = None

    def __init__(self, signal):
        """Initialize the signal and the bounds.

        The signal must be complex.

        """
        # Sanity-check.
        assert type(signal) == np.ndarray
        assert signal.dtype == np.complex64
        # Initialization.
        self.signal = signal
        self.lb = 0
        self.ub = len(signal)

    def update(self):
        """Clear plots and redraw them using current bounds."""
        # Clear the axis from last plots.
        self.axampl.clear()
        self.axspec.clear()
        # Plot the signal using new lower bound.
        self.axampl.plot(complex.get_amplitude(self.signal[self.lb:self.ub]))
        self.axspec.specgram(self.signal[self.lb:self.ub], NFFT=NFFT, sides="twosided", mode="magnitude")
        # Redraw the figure.
        self.fig.canvas.draw()

    def update_lb(self, val):
        """Update plots with new lower bound."""
        # Save new bound.
        self.lb = int(val)
        # Update plots.
        self.update()

    def update_ub(self, val):
        """Update plots with new upper bound."""
        # Save new bound.
        self.ub = int(val)
        # Update plots.
        self.update()
    
    def plot(self):
        """Start the plot for interactive shrink."""
        # Create the figure and plot the signal.
        self.fig, (self.axampl, self.axspec) = plt.subplots(nrows=2, ncols=1)
        self.axampl.plot(complex.get_amplitude(self.signal))
        self.axampl.set_xlabel('Sample [#]')
        self.axampl.set_ylabel('Amplitude')
        self.axspec.specgram(self.signal, NFFT=NFFT, sides="twosided", mode="magnitude")
        self.axspec.set_xlabel('Sample [#]')
        self.axspec.set_ylabel('Frequency [Ratio]')

        # Adjust the main plot to make room for the sliders.
        self.fig.subplots_adjust(bottom=0.25)

        # Make two horizontal sliders.
        # Dimensions: [left, bottom, width, height]
        axlb = self.fig.add_axes([0.25, 0.14, 0.65, 0.03])
        axub = self.fig.add_axes([0.25, 0.07, 0.65, 0.03])
        lb_slider = Slider(
            ax=axlb,
            label='Lower bound index',
            valmin=0,
            valmax=len(self.signal),
            valinit=0,
        )
        ub_slider = Slider(
            ax=axub,
            label='Upper bound index',
            valmin=0,
            valmax=len(self.signal),
            valinit=len(self.signal),
        )

        # Register the update function with each slider.
        lb_slider.on_changed(self.update_lb)
        ub_slider.on_changed(self.update_ub)

        # Start interactive plot.
        plt.show()

    def get_signal(self):
        """Get the shrinked signal from the object."""
        return self.get_signal_from(self.signal)
    
    def get_signal_from(self, signal):
        """Get the skrinked signal from external signal but with current bounds."""
        return signal[self.lb:self.ub]
