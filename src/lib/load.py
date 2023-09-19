"""Load or save the data in datasets. Handle multiple version and format of our
datasets. Keep separate code for keys and plaintexts as format can be
completely different even if names' patterns are similar.

"""

import os
import sys
from os import path
import numpy as np
from tqdm import tqdm

import lib.log as l

# * Global variables

# Format for current recording used in collect.py

# Format: radio_index [0 | 1] ; recording_index [0 .. n]
REC_RAW_FILENAME="raw_{}_{}.npy"
# Indexes of the radios used to store RAW files.
REC_RAW_NF_IDX = 0
REC_RAW_FF_IDX = 1

# Format for trace storage used everywhere else.

# Format: field_identifier [nf | ff]
DATASET_FILENAME_PACK="traces_{}.npy"
# Format: recording_index [0 .. n] ; field_identifier [nf | ff]
DATASET_FILENAME_UNPACK="{}_trace_{}.npy"
# Identifier of field type.
DATASET_FIELD_ID_NF = "nf"
DATASET_FIELD_ID_FF = "ff"

# * Misc

def get_nb_if_not_set(indir, nb):
    return nb if nb > 0 else get_nb(indir)

def get_nb(dir):
    """Return the number of traces contained in a dataset."""
    if is_raw_traces(dir):
        return 1
    for i in range(0, sys.maxsize):
        if get_dataset_is_nf_exist(dir) and not path.exists(get_dataset_path_unpack_nf(dir, i)):
            return i
        elif get_dataset_is_ff_exist(dir) and not path.exists(get_dataset_path_unpack_ff(dir, i)):
            return i
        elif not get_dataset_is_nf_exist(dir) and not get_dataset_is_ff_exist(dir):
            break
        assert(i < 1e5) # Infinite loop?
    return -1

def find_bad_entry(arr):
    """Return bad entry (metadata or trace) indexes from the 2D np.array ARR,
    where a bad entry is an entry filled with zeroes."""
    bad = []
    for i in tqdm(range(0, len(arr)), desc="find_bad_entry()"):
        if np.all(np.equal(arr[i], np.zeros((len(arr[0]),)))):
            bad.append(i)
    return bad

def prune_entry(arr, idx):
    """Remove entries from 1D np.array ARR having indexes equal to values in
    list IDX. WARNING: np.delete is not in-place, it will return a copy of the
    array, doesn't work well with GB traces."""
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
        l.LOGGER.warning("no loaded key(s)")
        return None

def load_plaintexts(dir):
    """Return a numpy array containing the plaintexts of shape (nb_traces, 16)"""
    if path.exists(path.join(dir, "p.npy")):
        return np.load(path.join(dir, "p.npy"))
    else:
        l.LOGGER.warning("no loaded plaintext(s)")
        return None

def save_keys(dir, k):
    """Save the K keys in DIR"""
    np.save(path.join(dir, "k.npy"), k)

def save_plaintexts(dir, p):
    """Save the P plaintexts in DIR"""
    np.save(path.join(dir, "p.npy"), p)

# * Traces

def get_record_path_raw(dir, radio_idx, i):
    return path.join(dir, REC_RAW_FILENAME.format(radio_idx, i))
def get_record_path_raw_nf(dir, i):
    return path.join(dir, REC_RAW_FILENAME.format(REC_RAW_NF_IDX, i))
def get_record_path_raw_ff(dir, i):
    return path.join(dir, REC_RAW_FILENAME.format(REC_RAW_FF_IDX, i))
def get_dataset_path_pack_nf(dir):
    return path.join(dir, DATASET_FILENAME_PACK.format(DATASET_FIELD_ID_NF))
def get_dataset_path_pack_ff(dir):
    return path.join(dir, DATASET_FILENAME_PACK.format(DATASET_FIELD_ID_FF))
def get_dataset_path_unpack_nf(dir, i):
    return path.join(dir, DATASET_FILENAME_UNPACK.format(i, DATASET_FIELD_ID_NF))
def get_dataset_path_unpack_ff(dir, i):
    return path.join(dir, DATASET_FILENAME_UNPACK.format(i, DATASET_FIELD_ID_FF))

def get_dataset_shape_type(dir):
    """Return a tuple composed of the DIR dataset's traces shape and dtype.

    To do so, it loads the first trace found from NF or FF in the dataset of
    path DIR, and use it as a reference for the others.

    """
    ref_nf = np_load_if_exist(get_dataset_path_unpack_nf(dir, 0))
    ref_ff = np_load_if_exist(get_dataset_path_unpack_ff(dir, 0))
    ref    = ref_nf if ref_nf is not None else ref_ff
    assert(ref is not None)
    return ref.shape, ref.dtype

def get_dataset_is_nf_exist(dir):
    """Return True if NF traces exists in DIR dataset, False otherwise."""
    nf_raw    = path.exists(get_record_path_raw_nf(dir, 0))
    nf_pack   = path.exists(get_dataset_path_pack_nf(dir))
    nf_unpack = path.exists(get_dataset_path_unpack_nf(dir, 0))
    return nf_raw or nf_pack or nf_unpack
    
def get_dataset_is_ff_exist(dir):
    """Return True if FF traces exists in DIR dataset, False otherwise."""
    ff_raw    = path.exists(get_record_path_raw_ff(dir, 0))
    ff_pack   = path.exists(get_dataset_path_pack_ff(dir))
    ff_unpack = path.exists(get_dataset_path_unpack_ff(dir, 0))
    return ff_raw or ff_pack or ff_unpack

def np_load_if_exist(fp):
    """Load the FP numpy array from disk if it exists, otherwise return None."""
    return None if not path.exists(fp) else np.load(fp)

def is_dataset_packed(dir):
    """Return True if the dataset is packed, False otherwise."""
    packed_nf = path.exists(get_dataset_path_pack_nf(dir))
    packed_ff = path.exists(get_dataset_path_pack_ff(dir))
    return packed_nf or packed_ff

def is_dataset_unpacked(dir):
    """Return True if the dataset is unpacked, False otherwise."""
    unpacked_nf = path.exists(get_dataset_path_unpack_nf(dir, 0))
    unpacked_ff = path.exists(get_dataset_path_unpack_ff(dir, 0))
    return unpacked_nf or unpacked_ff

def is_raw_traces(dir):
    """Return True if DIR is a folder containing raw traces."""
    nf_exist = path.exists(get_record_path_raw_nf(dir, 0))
    ff_exist = path.exists(get_record_path_raw_ff(dir, 0))
    return nf_exist or ff_exist

def print_trace_info(s, sr=0, id=""):
    """Print information about a trace/signal S (a 1D nd.array). If the
    sampling rate SR is provided, display the duration. If ID is provided, use
    it as an identifier.

    """
    assert(s.ndim == 1)
    l.LOGGER.info("trace information: {}".format(id))
    l.LOGGER.info("shape={}".format(s.shape))
    l.LOGGER.info("dtype={}".format(s.dtype))
    if sr:
        l.LOGGER.info("duration={:.4}s".format(len(s) / sr))

def print_dataset_info(input, label=""):
    """Print information about a trace and/or about a dataset. input should be a 1D or 2D nd.array"""
    l.LOGGER.info("dataset information: {}".format(label))
    if input.ndim == 1:
        print_trace_info(input)
    if input.ndim == 2:
        l.LOGGER.info("shape={}".format(input.shape))
        l.LOGGER.info("dtype={}".format(input.dtype))
        print_trace_info(input[0], id=label + "[0]")

def save_raw_trace(trace, dir, rad_idx, rec_idx):
    assert(path.exists(dir))
    np.save(get_record_path_raw(dir, rad_idx, rec_idx), trace)

def load_raw_trace(dir, rad_idx, rec_idx):
    fp = get_record_path_raw(dir, rad_idx, rec_idx)
    assert(path.exists(fp))
    try:
        trace = np.load(fp)
    except Exception as e:
        print(e)
    assert(trace is not None)
    return trace

def save_pair_trace(dir, idx, nf, ff):
    """Save one pair of traces (NF & FF) located in directory DIR at index
    IDX. If NF or FF are None, they are ignored."""
    if nf is not None:
        np.save(get_dataset_path_unpack_nf(dir, idx), nf)
    if ff is not None:
        np.save(get_dataset_path_unpack_ff(dir, idx), ff)
 
def load_pair_trace(dir, idx):
    """Load one pair of traces (NF & FF) located in directory DIR at index
    IDX. Return a tuple composed of NF then FF trace, or None on loading
    error.

    """
    trace_nf = None
    trace_ff = None
    try:
        trace_nf = np.load(get_dataset_path_unpack_nf(dir, idx))
    except Exception as e:
        print(e)
    try:
        trace_ff = np.load(get_dataset_path_unpack_ff(dir, idx))
    except Exception as e:
        print(e)
    return trace_nf, trace_ff

def save_all_traces(dir, nf, ff, packed=True):
    """Save all the traces in DIR. NF is a 2D np.array of shape (nb_traces,
    nb_samples), same for FF."""
    l.LOGGER.info("saving traces...")
    if packed:
        np.save(get_dataset_path_pack_nf(dir), nf)
        np.save(get_dataset_path_pack_ff(dir), ff)
    else:
        for i in tqdm(range(len(nf)), desc="save_all_traces()"):
            np.save(get_dataset_path_unpack_nf(dir, i), nf[i])
            np.save(get_dataset_path_unpack_ff(dir, i), ff[i])
    l.LOGGER.info("done!")

def load_all_traces(dir, nb=0):
    """Load traces contained in DIR. Can be packed or unpacked. Return a 2D
    np.array of shape (nb_traces, nb_samples). Only load NB traces if specified
    for unpacked dataset. Load traces conditionnaly, meaning if NF is present
    but FF is not, load NF and return None/empty/zeroes for FF. Beware to not
    overflow the memory.

    """
    l.LOGGER.info("loading traces...")
    if is_dataset_packed(dir):
        nf_p = get_dataset_path_pack_nf(dir)
        ff_p = get_dataset_path_pack_ff(dir)
        assert(path.exists(nf_p) and path.exists(ff_p))
        l.LOGGER.info("done!")
        return np.load(nf_p), np.load(ff_p)
    elif is_dataset_unpacked(dir):
        nf, ff = None, None
        nb = get_nb(dir) if nb < 1 else nb
        ref_shape, ref_dtype = get_dataset_shape_type(dir)
        nf_exist = get_dataset_is_nf_exist(dir)
        ff_exist = get_dataset_is_ff_exist(dir)
        if nf_exist:
            nf = np.empty((nb, ref_shape[0]), dtype=ref_dtype)
            for i in tqdm(range(0, nb), desc="load all nf traces"):
                nf_p = get_dataset_path_unpack_nf(dir, i)
                nf[i] = np.load(nf_p)
        else:
             l.LOGGER.warning("no loaded nf traces!")
        if ff_exist:
            ff = np.empty((nb, ref_shape[0]), dtype=ref_dtype)
            for i in tqdm(range(0, nb), desc="load all ff traces"):
                ff_p = get_dataset_path_unpack_ff(dir, i)
                ff[i] = np.load(ff_p)
        else:
            l.LOGGER.warning("no loaded ff traces!")
        if nf_exist or ff_exist:
            l.LOGGER.info("done!")
            return nf, ff
        else:
            l.LOGGER.error("no loaded traces!")
            return None, None
    else:
        l.LOGGER.error("unknown dataset format!")
        return None, None

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

def truncate_min(s1, s2):
    """Truncate two traces S1 and S2 (1D np.array) to the length of the smaller
    one."""
    assert(s1.ndim == 1 and s1.ndim == s2.ndim)
    target_len = len(s1) if len(s1) < len(s2) else len(s2)
    return s1[:target_len], s2[:target_len]

def truncate(traces, start=0, end=0):
    """Truncate all traces containted in TRACES (2D np.array) according to
    START and END if they are set."""
    if start:
        traces = traces[:,start:]
    if end:
        traces = traces[:,:end-start]
    return traces
