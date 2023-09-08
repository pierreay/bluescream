"""Functions used to analyze (i.e. get information) about a dataset or traces
already loaded in memory.

"""

import numpy as np
from scipy import signal
from tqdm import tqdm

import lib.plot as plot
import lib.filters as filters
import lib.triggers as triggers
import lib.analyze as analyze

# Note about implementation:
# - We often use np.copy when it comes to get a smaller portion of a
#   signal. This is to get rid of reference to the bigger signal that can be a
#   big trace, when we only want to extract a small portion.

# * Constants

FMT_IQ = 0
FMT_MAGNITUDE = 1

# * Dataset-level

def print_traces_idx_with_ks_n_pt_equal(ks, pt):
    """Print and compute a list of shape (subbyte_nb, subbyte_value) containing
    a list of trace indexes where plaintexts and keys are equal to the given
    subbyte index and subbyte value.

    """
    sub_i_v = [[[] for _ in range(0, 256)] for _ in range(0, 16)]
    for subbyte_idx in range(0, 16):
        for subbyte_val in range(0, 256):
            for trace_idx in range(0, len(ks)):
                if ks[trace_idx][subbyte_idx] == subbyte_val and pt[trace_idx][subbyte_idx] == subbyte_val:
                    sub_i_v[subbyte_idx][subbyte_val].append(trace_idx)
            print("subbyte_idx={} subbyte_val={} trace_idx={}".format(subbyte_idx, subbyte_val, sub_i_v[subbyte_idx][subbyte_val]))

# * Trace-level

def normalize(arr):
    """Apply min-max feature scaling normalization to a 1D np.array ARR
    representing the amplitude of a signal."""
    # Do not normalize I/Q samples (complex numbers). It will center the
    # amplitude value around 0.5 (min/max between 0 and 1) instead of 0
    # (min/max between -1 and 1) in time domain and create a strong DC offset
    # in freq domain.
    assert(arr.dtype == np.float32 or arr.dtype == np.float64)
    return (arr - np.min(arr)) / (np.max(arr) - np.min(arr))

def normalize_zscore(arr):
    """Normalize a trace using Z-Score normalization. Taken from load.py from
    Screaming Channels."""
    mu = np.average(arr)
    std = np.std(arr)
    if std != 0:
        arr = (arr - mu) / std
    return arr

def get_amplitude(traces):
    """From the TRACES 2D np.array of shape (nb_traces, nb_samples) or the 1D
    np.array of shape (nb_samples) containing IQ samples, return an array with
    the same shape containing the amplitude of the traces."""
    return np.abs(traces)

def get_phase(traces):
    """From the TRACES 2D np.array of shape (nb_traces, nb_samples) or the 1D
    np.array of shape (nb_samples) containing IQ samples, return an array with
    the same shape containing the phase of the traces."""
    return np.angle(traces)

def flip_normalized_signal(s):
    """Flip upside-down a normalized signal S in time-domain contained in a 1D
    np.array.

    """
    assert(s.ndim == 1)
    assert(min(s) == 0 and max(s) == 1)
    return 1 - s

def get_trace_format(trace):
    """Return a constant indicating the format of the trace."""
    if trace[0].dtype == np.complex64:
        return FMT_IQ
    elif trace[0].dtype == np.float32:
        return FMT_MAGNITUDE
    else:
        print("Unknown type!")
        return None

def fill_zeros_if_bad(ref, test):
    """If a bad trace TEST is given (i.e. wrong shape or None), it is remplaced
    with a zeroed trace of dtype and shape from REF. Return a tuple (FLAG,
    TEST) where FLAG is 0 if trace was OK and 1 if trace was bad."""
    ret = 0
    if test is None or test.shape != ref.shape:
        test = np.zeros(ref.shape, dtype=ref.dtype)
        ret = 1
    return (ret, test)

def find_aes(s, sr, bpl, bph, nb_aes = 1, lp = 0, offset = 0):
    """Find the start (beginning of the key scheduling) of every AES
    computation contained in the signal S of sampling rate SR. The signal must
    contained approximately NB_AES number of AES. BPL, BPH, LP are the bandpass
    and lowpass filters values used to create the trigger signal. Return the
    list of start indexes and the Triggers object used for the trigger signal.

    """
    # * Trigger signal.
    trigger   = triggers.Trigger(s, bpl, bph, lp, sr)
    trigger_l = triggers.Triggers()
    trigger_l.add(trigger)

    # * AES indexes finding.
    # Flip the signal to recover peaks.
    trigger.signal = analyze.flip_normalized_signal(trigger.signal)
    # Assume the distances between peaks will be the length of the signal
    # divided by the number of AES and that at least 1/4 of the signal is
    # fullfilled with AES computations.
    peaks = signal.find_peaks(trigger.signal, distance=len(trigger.signal) / nb_aes / 4, prominence=0.25)
    offset_duration = offset * sr
    return peaks[0] + offset_duration, trigger_l

def choose_signal(arr, i = -1):
    """From the ARR 2D numpy array, propose every sub-signals (1D numpy array)
    to the user and return a copy of the choosen signal, or None if there is
    none. If I is specified, automatically choose this template index instead
    of prompting.

    """
    if i == -1:
        for i in range(len(arr)):
            if plot.select(arr[i]):
                return np.copy(arr[i])
    else:
        return np.copy(arr[i])

def extract(s, starts, length = 0):
    """Exract sub-signals of S delimited by STARTS.

    The extraction use a list of STARTS indexes as delimiters of a 1D numpy
    array S. Returned sub-signals are copies of the original one.

    If LENGTH is specified, extract every sub-signals using its start index and
    specified length. Result is a consistent length 2D numpy array of shape
    (len(starts), length). If LENGTH is not specified, extract every
    sub-signals using its start index and the next start index as stop
    index. Result is a Python list of variable length signals.

    """
    assert(s.ndim == 1)
    if length > 0:
        extracted = np.zeros((len(starts), length))
        for i in range(len(starts)):
            condition = np.zeros((len(s)))
            condition[int(starts[i]):int(starts[i] + length)] = 1
            extracted[i] = np.copy(np.extract(condition, s))
        return extracted
    else:
        extracted = [0] * len(starts)
        for i in range(0, len(starts)):
            length = starts[i] - starts[i-1] if i == len(starts) - 1 else starts[i+1] - starts[i]
            extracted[i] = np.copy(s[int(starts[i]):int(starts[i] + length)])
        return extracted

def align(template, target, sr, ignore=True):
    """Return the TARGET signal aligned (1D np.array) using cross-correlation
    along the TEMPLATE signal, where SR is the sampling rates of signals. The
    shift is filled with zeros shuch that shape is not modified. If IGNORE is
    set to false, raise an assertion for high shift values.

    """
    # +++===+++++++++
    # +++++++===+++++ -> shift > 0 -> shift left target -> shrink template from right or pad target to right
    # ===++++++++++++ -> shift < 0 -> shift right target -> shrink template from left or pad target to left

    lpf_freq     = sr / 4
    template_lpf = filters.butter_lowpass_filter(template, lpf_freq, sr)
    target_lpf   = filters.butter_lowpass_filter(target, lpf_freq, sr)
    corr         = signal.correlate(target_lpf, template_lpf)
    shift        = np.argmax(corr) - (len(template) - 1)
    if shift > 0:
        if not ignore:
            assert shift < len(template/10), "shift is too high, inspect"
        target = target[shift:]
        target = np.append(target, np.zeros(shift))
    elif shift < 0:
        if not ignore:
            assert -shift < len(template/10), "shift is too high, inspect"
        target = target[:shift]
        target = np.insert(target, 0, np.zeros(-shift))
    return target

def align_nb(s, nb, sr, template):
    s_aligned = [0] * nb
    for idx in tqdm(range(0, nb), desc="align"):
        s_aligned[idx] = align(template, s[idx], sr)
    s_aligned = np.array(s_aligned, dtype=s.dtype)
    return s_aligned

def align_all(s, sr, template=None):
    """Align the signals contained in the S 2D np.array of sampling rate
    SR. Use TEMPLATE signal (1D np.array) as template/reference signal if
    specified, otherwise use the first signal of the S array.

    """
    return align_nb(s, len(s), sr, template if template is not None else s[0])
