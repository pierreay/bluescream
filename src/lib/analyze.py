"""Functions used to analyze (i.e. get information) about a dataset or traces
already loaded in memory.

"""

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
