"""Load or save the data in datasets. Handle multiple version and format of our
datasets. Keep separate code for keys and plaintexts as format can be
completely different even if names' patterns are similar.

"""

import os
import sys
from os import path
import numpy as np
from tqdm import tqdm

# * Misc

def get_nb(indir):
    """Return the number of traces contained in a dataset."""
    for i in range(0, sys.maxsize):
        if not path.exists(path.join(indir, "{}_trace_nf.npy".format(i))):
            return i-1

def find_bad_entry(arr):
    """Return bad entry (metadata or trace) indexes from the 2D np.array ARR,
    where a bad entry is an entry filled with zeroes."""
    bad = []
    for i in tqdm(range(0, len(arr)), desc="find_bad_entry()"):
        if np.all(np.equal(arr[i], np.zeros((len(arr[0]),)))):
            bad.append(i)
    return bad

def prune_entry(arr, idx):
    """Remove entries from 1D np.array ARR having indexes equal to values in list IDX."""
    return np.delete(arr, idx, 0)

def prune_entry_all_dataset(ks, pt, nf, ff):
    """Remove bad entries for the entire dataset."""
    bad = find_bad_entry(ks) + find_bad_entry(pt) + find_bad_entry(nf) + find_bad_entry(ff)
    assert(len(bad) < len(nf)/100)
    return (prune_entry(ks, bad), prune_entry(pt, bad),
            prune_entry(nf, bad), prune_entry(ff, bad))

def reduce_entry_all_dataset(ks, pt, nf, ff, nb=0):
    """Remove entries above NB for the entire dataset, hence containing NB
    entries. Set to 0 for maximum traces."""
    nb = len(ks) if nb == 0 else nb
    return (prune_entry(ks, range(nb, len(ks))), prune_entry(pt, range(nb, len(ks))),
            prune_entry(nf, range(nb, len(ks))), prune_entry(ff, range(nb, len(ks))))

# * Metadata

def is_key_fixed(dir):
    """Return True if key is fixed inside dataset pointed by dir"""
    assert(path.exists(dir))
    if path.exists(path.join(dir, "k.txt")):
        return True
    elif path.exists(path.join(dir, "k_0.txt")):
        return False
    elif path.exists(path.join(dir, "k.npy")):
        k = np.load(path.join(dir, "k.npy"))
        if k.shape == (1, 16):
            return True
        elif k.shape >= (1, 16):
            return False
    else:
        print("Unknown key mode!")
        return None
            
def load_keys(dir):
    """Return a numpy array containing the keys of shape (nb_traces, 16)"""
    if path.exists(path.join(dir, "k.npy")):
        return np.load(path.join(dir, "k.npy"))
    else:
        print("No loaded key(s)!")
        return None

def load_plaintexts(dir):
    """Return a numpy array containing the plaintexts of shape (nb_traces, 16)"""
    if path.exists(path.join(dir, "p.npy")):
        return np.load(path.join(dir, "p.npy"))
    else:
        print("No loaded plaintexts!")
        return None

def save_keys(dir, k):
    """Save the K keys in DIR"""
    np.save(path.join(dir, "k.npy"), k)

def save_plaintexts(dir, p):
    """Save the P plaintexts in DIR"""
    np.save(path.join(dir, "p.npy"), p)

# * Traces

def print_trace_info(input):
    """Print information about a trace. in should be a 1D nd.array"""
    print("[+] trace information:")
    print("trace.shape={}".format(input.shape))
    print("trace.dtype={}".format(input.dtype))

def print_dataset_info(input):
    """Print information about a trace and/or about a dataset. input should be a 1D or 2D nd.array"""
    print("[+] dataset information:")
    if input.ndim == 1:
        print_trace_info(input)
    if input.ndim == 2:
        print("dataset.shape={}".format(input.shape))
        print("dataset.dtype={}".format(input.dtype))
        print_trace_info(input[0])

def save_pair_trace(dir, idx, nf, ff):
    """Save one pair of traces (NF & FF) located in directory DIR at index
    IDX."""
    nf_p = path.join(dir, "{}_trace_nf.npy".format(idx))
    ff_p = path.join(dir, "{}_trace_ff.npy".format(idx))
    np.save(nf_p, nf)
    np.save(ff_p, ff)
 
def load_pair_trace(dir, idx):
    """Load one pair of traces (NF & FF) located in directory DIR at index
    IDX. Return a tuple composed of NF then FF trace, or None on loading
    error.

    """
    trace_nf_p = "{}/{}_trace_nf.npy".format(dir, idx)
    trace_ff_p = "{}/{}_trace_rf.npy".format(dir, idx)
    trace_nf = None
    trace_ff = None
    try:
        trace_nf = np.load(trace_nf_p)
    except Exception as e:
        print(e)
    try:
        trace_ff = np.load(trace_ff_p)
    except Exception as e:
        print(e)
    return trace_nf, trace_ff

def save_all_traces(dir, nf, ff):
    """Save all the traces in DIR. NF is a 2D np.array of shape (nb_traces,
    nb_samples), same for FF."""
    np.save(path.join(dir, "traces_nf.npy"), nf)
    np.save(path.join(dir, "traces_ff.npy"), ff)

def load_all_traces(dir, nb=0):
    """Load traces contained in DIR. Can be packed or unpacked. Return a 2D
    np.array of shape (nb_traces, nb_samples). Only load NB traces if specified
    for unpacked dataset. Beware to not overflow the memory.
    """
    print("[+] loading traces...")
    if path.exists(path.join(dir, "traces_nf.npy")):
        packed = True
        nf_p = path.join(dir, "traces_nf.npy")
        ff_p = path.join(dir, "traces_ff.npy")
        assert(path.exists(nf_p) and path.exists(ff_p))
        print("[+] done!")
        return np.load(nf_p), np.load(ff_p)
    elif path.exists(path.join(dir, "0_trace_nf.npy")):
        import ipdb; ipdb.set_trace()
        packed = False
        ref = np.load(path.join(dir, "0_trace_nf.npy"))
        nb = get_nb(dir) if nb < 1 else nb
        traces_nf = np.empty((nb, ref.shape[0]), dtype=ref.dtype)
        traces_ff = np.empty((nb, ref.shape[0]), dtype=ref.dtype)
        for i in tqdm(range(0, nb), desc="load_all_traces()"):
            nf_p = path.join(dir, "{}_trace_nf.npy".format(i))
            ff_p = path.join(dir, "{}_trace_ff.npy".format(i))
            traces_nf[i] = np.load(nf_p)
            traces_ff[i] = np.load(ff_p)
        return traces_nf, traces_ff

def reshape_trimming_zeroes():
    """I don't need it, but in case of future needs...
    np.trim_zeros:
    -++===+++ -> ++===+++
    --+===+++ -> +===+++
    +++===+++ -> +++===+++
    1. Find the trace with most zeroes at the beginning => nb_zeroes.
    2. Shrink all traces from the beginning using nb_zeroes.
    4. Shrink all traces from the end using the length of the trace used in 1.
    """
    pass

def reshape(arr):
    """Reshape a Python list of 1D np.array to same dimension.

    It find the array of minimum len and use this length to shrink other array
    from their end. It allows to create a 2D .np.array.

    """
    len_min = sys.maxsize
    for i in tqdm(range(len(arr)), desc="reshape()"):
        if len(arr[i]) < len_min:
            len_min = len(arr[i])
    for i in tqdm(range(len(arr)), desc="reshape()"):
        arr[i] = arr[i][:len_min]
    return arr

def truncate(traces, start=0, end=0):
    """Truncate all traces containted in TRACES (2D np.array) according to
    START and END if they are set."""
    if start:
        traces = traces[:,start:]
    if end:
        traces = traces[:,:end-start]
    return traces
