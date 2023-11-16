"""Functions used to analyze (i.e. get information) about a dataset or traces
already loaded in memory.

"""

import numpy as np
from scipy import signal
from tqdm import tqdm

import lib.log as l
import lib.plot as libplot
import lib.filters as filters
import lib.triggers as triggers
import lib.analyze as analyze
import lib.complex as complex

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

from enum import Enum

NormMethod = Enum('NormMethod', ['MINMAX', 'ZSCORE', 'COMPLEX_ABS', 'COMPLEX_ANGLE'])

def normalize(arr, method=NormMethod.MINMAX, arr_complex=False):
    """Return a normalized ARR array.

    Set method to NormMethod.MINMAX to normalize using min-max feature scaling.

    Set method to NormMethod.ZSCORE to normalize using zscore normalization.

    Set method to NormMethod.COMPLEX_ABS to normalize between range of absolute
    value of a complex number.

    Set method to NormMethod.COMPLEX_ANGLE to normalize between range of angle
    of a complex number.

    By default, ARR is a ND np.ndarray containing floating points numbers. It
    should not contains IQ, as normalizing complex numbers doesn't makes sense
    (leads to artifacts). The normalization has to be applied on the magnitude
    and angle of the complex numbers, obtained using polar representation with
    complex.r2p(). Normalizing and converting back to regular representation
    just after doesn't make sense, since the normalization is reverted in the
    complex.p2r() function. Hence, we offer the optional ARR_COMPLEX option. If
    ARR_COMPLEX is set to True, ARR must contains complex numbers, and it will
    be returned a tuple composed of the normalized amplitude and the normalized
    angle. We use an explicit option to more easily show what is the input and
    output in the code that will use this function.

    """
    assert method in NormMethod
    if arr_complex is True:
        assert complex.is_iq(arr), "normalization input should be complex numbers"
        arr_polar = complex.r2p(arr)
        return normalize(arr_polar[0], method=method), normalize(arr_polar[1], method=method)
    else:
        assert arr.dtype == np.float32 or arr.dtype == np.float64, "normalization input should be floating points numbers"
        if method == NormMethod.MINMAX:
            return normalize_minmax(arr)
        elif method == NormMethod.ZSCORE:
            return normalize_zscore(arr)
        elif method == NormMethod.COMPLEX_ABS:
            # Refer to complex.is_p2r_ready() and complex.r2p() for bounds reference.
            return analyze.normalize_generic(arr, {'actual': {'lower': arr.min(), 'upper': arr.max()}, 'desired': {'lower': 0, 'upper': np.iinfo(np.int16).max}})
        elif method == NormMethod.COMPLEX_ANGLE:
            # Refer to complex.is_p2r_ready() and complex.r2p() for bounds reference.
            return analyze.normalize_generic(arr, {'actual': {'lower': arr.min(), 'upper': arr.max()}, 'desired': {'lower': -np.pi, 'upper': np.pi}})

def normalize_minmax(arr):
    """Apply min-max feature scaling normalization to a 1D np.array ARR
    representing the amplitude of a signal.

    Min-Max Scaling will scales data between a range of 0 to 1 in float.

    """
    assert arr.dtype == np.float32 or arr.dtype == np.float64
    return (arr - np.min(arr)) / (np.max(arr) - np.min(arr))

def normalize_zscore(arr, set=False):
    """Normalize a trace using Z-Score normalization.

    Z-Score Normalization will converts data into a normal distribution with a
    mean of 0 and a standard deviation of 1.

    If SET is set to TRUE, apply normalization on the entire set instead of on
    each trace individually.

    Source: load.py from original Screaming Channels.

    """
    # Do not normalize I/Q samples (complex numbers).
    assert arr.dtype == np.float32 or arr.dtype == np.float64
    mu = np.average(arr) if set is False else np.average(arr, axis=0)
    std = np.std(arr) if set is False else np.std(arr, axis=0)
    if std != 0:
        arr = (arr - mu) / std
    return arr

def normalize_generic(values, bounds):
    """Normalize VALUES between BOUNDS.

    VALUES is a ND np.ndarray. BOUNDS is a dictionnary with two entries,
    "desired" and "actual", each one having the "upper" and "lower"
    bounds. This dictionnary is used to rescale the values from the "actual"
    bounds to the "desired" ones.

    Source:
    https://stackoverflow.com/questions/48109228/normalizing-data-to-certain-range-of-values

    """
    assert values.dtype == np.float32 or values.dtype == np.float64
    return bounds['desired']['lower'] + (values - bounds['actual']['lower']) * (bounds['desired']['upper'] - bounds['desired']['lower']) / (bounds['actual']['upper'] - bounds['actual']['lower'])

def is_normalized(values):
    """Return True if values contained in VALUES are normalized.

    VALUES is a 1D ndarray containing floating-points numbers.

    NOTE: In this function, we assume normalization means min-max feature
    scaling (floats between 0 and 1) and that a zeroed signal is not a
    normalized signal.

    NOTE: VALUES cannot contains IQ (complex numbers) as it doesn't make sense
    to have a normalized signal (assuming 0 and 1) in the cartesian / regular
    representation.

    """
    assert type(values) == np.ndarray
    assert values.ndim == 1
    assert values.dtype == np.float32 or values.dtype == np.float64
    zeroed = values.nonzero()[0].shape == (0,)
    interval = values[values < 0].shape == (0,) and values[values > 1].shape == (0,)
    return not zeroed and interval

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

def fill_zeros_if_bad(ref, test, log=True, log_idx=-1):
    """If a bad trace TEST is given (i.e. wrong shape or None), return a bad
    trace using REF as trace reference. Return a tuple (FLAG, TEST) where FLAG
    is False if trace was OK and True if trace was bad.

    """
    if test is None or test.shape != ref.shape:
        if log is True:
            l.LOGGER.warning("trace {} filled with zeroes!".format(log_idx))
        return True, get_bad_trace(ref)
    return False, test

def get_bad_trace(ref):
    """Return what we call a bad trace using the REF trace as a reference for
    the shape and the dtype. A bad trace is a recording which is remplaced with
    a zeroed trace because of a an analysis step that lead to an error
    (e.g. wrong AES finding or extraction).

    """
    assert(type(ref) == np.ndarray)
    return np.zeros(ref.shape, dtype=ref.dtype)

def find_aes(s, sr, bpl, bph, nb_aes = 1, lp = 0, offset = 0, flip=True, plot=False):
    """Find the indexes of AES computations inside a trace.

    Find the start (beginning of the key scheduling) of every AES computation
    contained in the signal S of sampling rate SR. The signal must contained
    approximately NB_AES number of AES. BPL, BPH, LP are the bandpass and
    lowpass filters values used to create the trigger signal.

    Return the list of start indexes and the Triggers object used for the
    trigger signal.

    """
    assert(isinstance(s, np.ndarray))
    # * Pre-processing.
    # This function will work on the amplitude and not the phase of the signal.
    s = complex.get_amplitude(s)

    # * Trigger signal.
    trigger   = triggers.Trigger(s, bpl, bph, lp, sr)
    trigger_l = triggers.Triggers()
    trigger_l.add(trigger)

    # * AES indexes finding.
    # Flip the signal if needed to recover peaks.
    if flip is True:
        trigger.signal = analyze.flip_normalized_signal(trigger.signal)
    # Assume the distances between peaks will be the length of the signal
    # divided by the number of AES and that at least 1/4 of the signal is
    # fullfilled with AES computations.
    peaks = signal.find_peaks(trigger.signal, distance=len(trigger.signal) / nb_aes / 4, prominence=0.25)
    offset_duration = offset * sr
    peaks = peaks[0] + offset_duration

    # * Plot result if asked.
    libplot.plot_time_spec_sync_axis([s], samp_rate=sr, peaks=peaks, triggers=trigger_l, cond=plot)

    # * Prune bad indexes.
    if np.shape(peaks[peaks <= 0]) != (0,):
        l.LOGGER.warning("discard detected aes turned negatives because of the offset")
        peaks = peaks[peaks >= 0]
    return peaks, trigger_l

def choose_signal(arr, i = -1):
    """From the ARR 2D numpy array, propose every sub-signals (1D numpy array)
    to the user and return a copy of the choosen signal, or None if there is
    none. If I is specified, automatically choose this template index instead
    of prompting.

    """
    if i == -1:
        for i in range(len(arr)):
            if libplot.select(arr[i]):
                l.LOGGER.info("Select signal #{}".format(i))
                return np.copy(arr[i])
    else:
        l.LOGGER.debug("Automatically select signal #{}".format(i))
        return np.copy(arr[i])

def extract_time_window(s, sr, center, length, offset=0):
    """Extract a time window from a signal S.

    The sample rate of the signal is SR. The window will be extracted using
    CENTER (index) as center index of the window in the signal and LENGTH
    (seconds) as the duration of the window, optionally applying the offset
    OFFSET (seconds) to the CENTER index. The function will return the
    extracted signal.

    """
    bl = int(center + (offset * sr) - (length / 2) * sr)
    bl = bl if bl > 0 else 0
    bh = int(center + (offset * sr) + (length / 2) * sr)
    bh = bh if bh < len(s) else len(s)
    return s[bl:bh]

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
    # Extract a fixed length.
    if length > 0:
        extracted = np.zeros((len(starts), length), dtype=s.dtype)
        for i in range(len(starts)):
            condition = np.zeros((len(s)), dtype=s.dtype)
            condition[int(starts[i]):int(starts[i] + length)] = 1
            extracted[i] = np.copy(np.extract(condition, s))
        return extracted
    # Extract a variable length.
    else:
        extracted = [0] * len(starts)
        for i in range(0, len(starts)):
            length = starts[i] - starts[i-1] if i == len(starts) - 1 else starts[i+1] - starts[i]
            extracted[i] = np.copy(s[int(starts[i]):int(starts[i] + length)])
        return extracted

def align(template, target, sr, ignore=True, log=False):
    """Align a signal against a template.

    Return the TARGET signal aligned (1D np.array) using cross-correlation
    along the TEMPLATE signal, where SR is the sampling rates of signals. The
    shift is filled with zeros shuch that shape is not modified.

    - If IGNORE is set to false, raise an assertion for high shift values.
    - If LOG is set to True, log the shift produced by the cross-correlation.

    NOTE: The cross-correlation shift is computed based on amplitude
    (np.float64) of signals.

    """
    # +++===+++++++++
    # +++++++===+++++ -> shift > 0 -> shift left target -> shrink template from right or pad target to right
    # ===++++++++++++ -> shift < 0 -> shift right target -> shrink template from left or pad target to left
    assert(template.shape == target.shape)
    assert(template.ndim == 1 and target.ndim == 1)
    # Compute the cross-correlation and find shift across amplitude.
    lpf_freq     = sr / 4
    template_lpf = filters.butter_lowpass_filter(complex.get_amplitude(template), lpf_freq, sr)
    target_lpf   = filters.butter_lowpass_filter(complex.get_amplitude(target), lpf_freq, sr)
    corr         = signal.correlate(target_lpf, template_lpf)
    shift        = np.argmax(corr) - (len(template) - 1)
    # Log and check shift value.
    if log:
        l.LOGGER.debug("shift to maximize cross correlation is {}".format(shift))
    if not ignore:
        assert np.abs(shift) < len(template/10), "shift is too high, inspect"
    # Apply shift on the raw target signal.
    return analyze.shift(target, shift)

def align_nb(s, nb, sr, template, tqdm_log=True):
    s_aligned = [0] * nb
    if tqdm_log:
        lrange = tqdm(range(0, nb), desc="align")
    else:
        lrange = list(range(0, nb))
    for idx in lrange:
        s_aligned[idx] = align(template, s[idx], sr)
    s_aligned = np.array(s_aligned, dtype=s.dtype)
    return s_aligned

def align_all(s, sr, template=None, tqdm_log=True):
    """Align the signals contained in the S 2D np.array of sampling rate
    SR. Use TEMPLATE signal (1D np.array) as template/reference signal if
    specified, otherwise use the first signal of the S array.

    """
    return align_nb(s, len(s), sr, template if template is not None else s[0], tqdm_log)

def average(arr, norm=False):
    """Average a series of signals between them.

    Return the average signal of all signals composing the ARR 2D numpy
    array. The signals can be IQ or amplitude/phase.

    If NORM is set to True, normalize each signals individually. If signals are
    IQ, normalize each components (amplitude and phase) individually. Depending
    on the usage, it may not make sense to average signal without normalization
    if signals are representing the same transmission/operation.

    """
    assert(arr.ndim == 2)
    # 2D array (traces) of signal's IQ.
    if complex.is_iq(arr):
        arr_polar = complex.r2p(arr)
        return complex.p2r(average(arr_polar[0], norm=norm), average(arr_polar[1], norm=norm))
    # 2D array (traces) of signal's amplitude or phase.
    else:
        # Normalize before averaging if requested.
        if norm is True:
            arr = analyze.normalize(arr)
        return np.average(arr, axis=0)

def average_aes_dproc(dset, sset, plot, args):
    """Wrapper around average_aes() for the DatasetProcessing class."""
    # Get supplementary arguments.
    nb_aes = args[0]
    template = args[1]
    # * Get the average of all AES and the template.
    ff_avg, sset.template = analyze.average_aes(sset.ff[0], dset.samp_rate, nb_aes, template if sset.template is None else sset.template, plot_enable=plot)
    # * Return the averaged trace.
    # NOTE: The template will be modified in the final Subset object if this
    # function is ran by the MainProcess.
    return ff_avg
    
def average_aes(arr, sr, nb_aes, template, plot_enable=True):
    """Average multiple AES execution contained in trace ARR into a single
    trace. To average multiple AES runs inside one trace, this command will
    perform:

    1. AES detection
    2. Templating selection
    3. Extraction
    4. Alignment
    5. Averaging

    SR is the sampling rate of ARR.
    NB_AES is the number of AES executions in the trace ARR.
    TEMPLATE can be set to -1 for interactive template selection, to an index
    for the automatic template selection, or a template signal.
    If PLOT is set to True, plot triggers and start indexes.
    Return a tuple of the averaged trace (np.ndarray) (or None on error) and the template.

    """
    # * Find AES.
    # XXX: Find a better way to configure this function than modifying this place of the source code.
    # First version of find_aes used for training set:
    # starts, trigger = analyze.find_aes(arr, sr, 8.8e6, 9.5e6, nb_aes, 1e4, -0.5e-4, flip=True)
    # Second version of find_aes used for attack set:
    # starts, trigger = analyze.find_aes(arr, sr, 8.1e6, 8.5e6, nb_aes, 1e4, -0.5e-4, flip=False)
    # Third version of find_aes used to train set using 10 MHz bandwidth:
    starts, trigger = analyze.find_aes(arr, sr, 2.9e6, 3.3e6, nb_aes, 1e4, -0.5e-4, flip=True, plot=plot_enable)
    check_nb = len(starts) < (1.1 * nb_aes) and len(starts) > (0.8 * nb_aes)
    if check_nb:
        l.LOGGER.debug("number of detected aes: {}".format(len(starts)))
    else:
        l.LOGGER.error("number of detected aes seems to be aberrant: {}".format(len(starts)))
        return None, template

    # * Select one extraction as template.
    if isinstance(template, int):
        l.LOGGER.debug("Start template selection...")
        extracted  = analyze.extract(arr, starts)
        template_s = analyze.choose_signal(extracted, template)
    elif isinstance(template, np.ndarray):
        l.LOGGER.debug("Use provided template signal")
        template_s = template
    assert(template_s is not None)

    # * Extract all AES and average them.
    extracted = analyze.extract(arr, starts, len(template_s))
    aligned   = analyze.align_all(extracted, sr, template_s, False)
    # Set NORM to False as we average signals extracted from a single trace,
    # hence with same amplitude levels.
    averaged  = analyze.average(aligned, norm=False)

    # * Debuging code.
    # Compare result of alignement to debug if needed. The 13 here is a trace
    # index that produced a "high" shift.
    # libplot.plot_time_spec_sync_axis([template_s, extracted[13], aligned[13]])

    return averaged, template_s

def is_nan(arr):
    """Return True if at least one NAN (not a number) is contained in ARR."""
    test = np.isnan(arr)
    return len(test[test == True]) >= 1

def shift(sig, shift):
    """Shift a signal SIG from the SHIFT offset.

    Shift a signal SIG to left (positive SHIFT) or right (negative
    SHIFT). Empty parts of the signal are completed using np.zeros of same
    dtype as SIG.

    SHIFT can be the output of the signal.correlate() function.

    """
    if shift > 0:
        sig = sig[shift:]
        sig = np.append(sig, np.zeros(shift, dtype=sig.dtype))
    elif shift < 0:
        sig = sig[:shift]
        sig = np.insert(sig, 0, np.zeros(-shift, dtype=sig.dtype))
    return sig
