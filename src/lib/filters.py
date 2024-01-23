"""DSP functions (e.g. filters, decimation)."""

import numpy as np
import scipy.signal as signal
from scipy.signal import butter, lfilter

def butter_highpass(cutoff, fs, order=5):
    nyq = 0.5 * fs
    normal_cutoff = cutoff / nyq
    b, a = butter(order, normal_cutoff, btype="high", analog=False)
    return b, a

def butter_highpass_filter(data, cutoff, fs, order=5):
    assert(cutoff < fs / 2) # Nyquist
    b, a = butter_highpass(cutoff, fs, order=order)
    y = lfilter(b, a, data)
    return y

def butter_lowpass(cutoff, fs, order=5):
    nyq = 0.5 * fs
    normal_cutoff = cutoff / nyq
    b, a = butter(order, normal_cutoff, btype="low", analog=False)
    return b, a

def butter_lowpass_filter(data, cutoff, fs, order=5):
    assert(cutoff < fs / 2) # Nyquist
    b, a = butter_lowpass(cutoff, fs, order=order)
    y = lfilter(b, a, data)
    return y

def butter_bandpass(lowcut, highcut, fs, order=5):
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq
    b, a = butter(order, [low, high], btype="band")
    return b, a

def butter_bandpass_filter(data, lowcut, highcut, fs, order=5):
    assert(lowcut < fs / 2 and highcut < fs / 2) # Nyquist
    assert(lowcut < highcut)                     # Logic
    b, a = butter_bandpass(lowcut, highcut, fs, order=order)
    y = lfilter(b, a, data)
    return y

def decimate(s, sr, f):
    """Decimate the S signal (a 1D np.array) of sampling rate SR using the
    decimation factor F. Return a tuple of (S, SR) with both S and SR
    decimated.

    """
    if f > 1:
        s = signal.decimate(s, f, ftype="fir")
        sr = sr / f
    return s, sr

def remove_dc(s):
    """Remove the DC component of a signal in time-domain by substracting the
    mean."""
    return s - np.mean(s)

def envelope_square(sig, window):
    """Squared envelop detector.

    Get a signal amplitude envelope using a square signal.

    :param sig: Input signal (must be magnitude / float).
    
    :param window: Number of samples to use as square window.

    :return: A square signal representing the amplitude envelop.

    """
    assert type(sig) == np.ndarray, "Input signal should be Numpy array!"
    assert sig.dtype == np.float32 or sig.dtype == np.float64, "Input data type should be amplitude/float!"
    env = np.zeros_like(sig)
    window = 200
    idx_start = 0
    while idx_start < len(sig):
        idx_end = idx_start + window
        if idx_end < len(sig):
            env[idx_start:idx_end] = np.max(sig[idx_start:idx_end])
        idx_start += window
    # NOTE: DEBUG:
    # plt.plot(sig)
    # plt.plot(env)
    # plt.show()
    return env
