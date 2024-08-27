#!/usr/bin/env python3

import numpy as np
from matplotlib import pyplot as plt
from matplotlib import mlab
from screamingchannels import analyze
from screamingchannels import radio
from screamingchannels import config
from screamingchannels import device
from screamingchannels import log as l

if __name__ == "__main__":
    l.init(None, "DEBUG")
    file = "/tmp/rx_signal.npy"
    out = "/tmp/rx_signal_plot.png"

    signal = np.load(file)
    # Print data and analyze signal.
    l.LOGGER.info("Data type: {}".format(type(signal)))
    l.LOGGER.info("Number of samples: {}".format(len(signal)))
    l.LOGGER.info("Average Magnitude: {}".format(np.average(signal)))
    l.LOGGER.info("Maximum Magnitude: {}".format(np.max(signal)))
    l.LOGGER.info("Minimum Magnitude: {}".format(np.min(signal)))
    l.LOGGER.info("Standard Deviation: {}".format(np.std(signal)))

    plt.figure()
    ax_time = plt.subplot(2, 1, 1)
    ax_time.plot(signal, lw = 0.3 if out else 0.7)
    plt.title("Time-Domain of {}".format(file))
    plt.xlabel("Samples [#]")
    plt.ylabel("Magnitude")
    ax_specgram = plt.subplot(2, 1, 2, sharex=ax_time)
    ax_specgram.specgram(signal, NFFT=256, Fs=1, Fc=0,
                 detrend=mlab.detrend_none, window=mlab.window_hanning,
                 noverlap=127, cmap=None, xextent=None, pad_to=None,
                 sides='default', scale_by_freq=None, mode='default', scale='default')
    plt.title("Raw [Spectrogram] of {}".format(file))
    plt.xlabel("Time")
    plt.ylabel("Frequency")
    
    if out:
        l.LOGGER.info("Save plot in {} file".format(out))
        plt.savefig(out, dpi=1200)
        #plt.close()
    plt.get_current_fig_manager().full_screen_toggle()
    plt.show(block=True)

