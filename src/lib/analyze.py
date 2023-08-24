"""Functions used to analyze (i.e. get information) about a dataset or traces
already loaded in memory.

"""

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
    """Apply min-max feature scaling normalization to a 1D array."""
    assert(arr.dtype == np.float32)
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

def get_trace_format(trace):
    """Return a constant indicating the format of the trace."""
    if trace[0].dtype == np.complex64:
        return FMT_IQ
    elif trace[0].dtype == np.float32:
        return FMT_MAGNITUDE
    else:
        print("Unknown type!")
        return None
