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
import lib.plot as libplot
from lib.soapysdr import MySoapySDR

# * Global variables

# Format for current recording used in radio.py

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

DATASET_RAW_INPUT_KEY_PACK="k.txt"
DATASET_RAW_INPUT_KEY_UNPACK="{}_k.txt"
DATASET_RAW_INPUT_PLAINTEXT_PACK="p.txt"
DATASET_RAW_INPUT_PLAINTEXT_UNPACK="{}_p.txt"
DATASET_RAW_INPUT_FORMAT="{}_{}"
DATASET_NPY_INPUT_KEY="k.npy"
DATASET_NPY_INPUT_PLAINTEXT="p.npy"

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
    if ks is not None:
        ks = prune_entry(ks, range(nb, len(ks)))
    if pt is not None:
        pt = prune_entry(pt, range(nb, len(pt)))
    if nf is not None:
        nf = prune_entry(nf, range(nb, len(nf)))
    if ff is not None:
        ff = prune_entry(ff, range(nb, len(ff)))
    return ks, pt, nf, ff

# * Metadata

def is_key_fixed(dir):
    """Return True if key is fixed inside dataset pointed by dir"""
    assert(path.exists(dir))
    if path.exists(path.join(dir, DATASET_RAW_INPUT_KEY_PACK)):
        return True
    elif path.exists(path.join(dir, DATASET_RAW_INPUT_KEY_UNPACK.format(0))):
        return False
    elif path.exists(path.join(dir, DATASET_NPY_INPUT_KEY)):
        k = np.load(path.join(dir, DATASET_NPY_INPUT_KEY))
        if k.shape == (1, 16):
            return True
        elif k.shape >= (1, 16):
            return False
    else:
        print("Unknown key mode!")
        return None

def load_raw_input(data_path, filename, number, fixed=False, hex=True):
    """Extract plaintexts and keys from a RAW collected dataset (hexadecimal in
    .txt) and store them in .npy files containing integers.

    DATA_PATH is the path of a directory containing the raw traces and
    metadatas (plaintexts and keys).

    Example:
    k = np.array(load_raw_input(indir, DATASET_RAW_INPUT_KEY_PACK,       get_nb(indir), fixed = load.is_key_fixed(indir), hex=True))
    p = np.array(load_raw_input(indir, DATASET_RAW_INPUT_PLAINTEXT_PACK, get_nb(indir), fixed = False,                    hex=False))
    np.save("{}/k.npy".format(outdir), k)
    np.save("{}/p.npy".format(outdir), p)

    History: This is a modified, improved and adapted version of the
    load.py/load_all() function of the original Screaming Channels poc.

    """    
    assert(number > 0)
    l.LOGGER.info("load all {}".format(filename))
    if fixed == True:
        filepath = path.join(data_path, filename)
        with open(filepath, "r") as f:
            data = f.readline()[:-1]
    elif fixed == False:
        data = ''
        for i in tqdm(range(0, number)):
            filename_i = DATASET_RAW_INPUT_FORMAT.format(i, filename)
            filepath = path.join(data_path, filename_i)
            with open(filepath, "r") as f:
                tmp = f.readline()
                if hex and len(tmp) != 33:
                    l.LOGGER.info("i={} tmp={} -> bad key, replace with zeros".format(i, tmp))
                    tmp = "00000000000000000000000000000000"
                if not hex:
                    tmp = "{0:0{1}x}".format(int(tmp), 32)
                data += "\n" + tmp
                if data[len(data)-1] == '\n':
                    data = data[0:len(data)-1]
    if data[0] == "\n":
        data = data[1:]
    return [utils.str_hex_to_list_int(line)
            for line in data.split('\n')]
            
def load_keys(dir):
    """Return a numpy array containing the keys of shape (nb_traces, 16)"""
    if path.exists(path.join(dir, DATASET_NPY_INPUT_KEY)):
        return np.load(path.join(dir, DATASET_NPY_INPUT_KEY))
    else:
        l.LOGGER.warning("no loaded key(s)")
        return None

def load_plaintexts(dir):
    """Return a numpy array containing the plaintexts of shape (nb_traces, 16)"""
    if path.exists(path.join(dir, DATASET_NPY_INPUT_PLAINTEXT)):
        return np.load(path.join(dir, DATASET_NPY_INPUT_PLAINTEXT))
    else:
        l.LOGGER.warning("no loaded plaintext(s)")
        return None

def save_keys(dir, k):
    """Save the K keys in DIR"""
    np.save(path.join(dir, DATASET_NPY_INPUT_KEY), k)

def save_plaintexts(dir, p):
    """Save the P plaintexts in DIR"""
    np.save(path.join(dir, DATASET_NPY_INPUT_PLAINTEXT), p)

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
    """Load the FP numpy array from disk if it exists, otherwise return
    None. NOTE: Use this function only for traces, not for inputs.

    """
    return None if not path.exists(fp) else MySoapySDR.numpy_load(fp)

def is_dataset_packed(dir):
    """Return True if the dataset is packed, False otherwise."""
    packed_nf = path.exists(get_dataset_path_pack_nf(dir))
    packed_ff = path.exists(get_dataset_path_pack_ff(dir))
    return packed_nf or packed_ff

def is_dataset_unpacked(dir, idx=0):
    """Return True if the dataset is unpacked, False otherwise. If IDX is
    specified, then check for a specific trace index."""
    unpacked_nf = path.exists(get_dataset_path_unpack_nf(dir, idx))
    unpacked_ff = path.exists(get_dataset_path_unpack_ff(dir, idx))
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

def save_raw_trace(trace, dir, rad_idx, rec_idx):
    assert(path.exists(dir))
    MySoapySDR.numpy_save(get_record_path_raw(dir, rad_idx, rec_idx), trace)

def load_raw_trace(dir, rad_idx, rec_idx, log=False):
    trace = None
    fp = get_record_path_raw(dir, rad_idx, rec_idx)
    if path.exists(fp):
        l.LOGGER.info("Load RAW trace from {}".format(fp))
        try:
            trace = MySoapySDR.numpy_load(fp)
        except Exception as e:
            print(e)
    else:
        l.LOGGER.warning("No loaded raw trace for radio index #{}!".format(rad_idx))
    return trace

def save_pair_trace(dir, idx, nf, ff):
    """Save one pair of traces (NF & FF) located in directory DIR at index
    IDX. If NF or FF are None, they are ignored. """
    if nf is not None:
        MySoapySDR.numpy_save(get_dataset_path_unpack_nf(dir, idx), nf)
    if ff is not None:
        MySoapySDR.numpy_save(get_dataset_path_unpack_ff(dir, idx), ff)
 
def load_pair_trace(dir, idx, nf=True, ff=True):
    """Load one pair of traces (NF & FF) located in directory DIR at index
    IDX. Return a tuple composed of NF then FF trace, or None on loading
    error. NF and FF can be set to False to not load them in an unpacked
    dataset.

    """
    trace_nf = None
    trace_ff = None
    try:
        trace_nf = None if nf is False else MySoapySDR.numpy_load(get_dataset_path_unpack_nf(dir, idx))
    except Exception as e:
        l.LOGGER.warn(e)
    try:
        trace_ff = None if ff is False else MySoapySDR.numpy_load(get_dataset_path_unpack_ff(dir, idx))
    except Exception as e:
        l.LOGGER.warn(e)
    return trace_nf, trace_ff

def save_all_traces(dir, nf, ff, packed=False, start=0, stop=0):
    """Save traces in DIR. NF and FF can be a 2D np.array of shape (nb_traces,
    nb_samples) or None. If PACKED is set to True or if STOP is set to < 1,
    then all the traces are saved. Othserwise, START and STOP can be specified
    to save a specific range of file to the disk.

    """
    l.LOGGER.info("saving traces...")
    if packed:
        # NOTE: Following code is not working anymore without
        # MySoapySDR.numpy_save stub, but I don't know if it can handle packed
        # dataset for now.
        if nf is not None:
            np.save(get_dataset_path_pack_nf(dir), nf)
        if ff is not None:
            np.save(get_dataset_path_pack_ff(dir), ff)
    else:
        if stop < 1:
            stop = len(nf) if nf is not None else len(ff) 
        for i in tqdm(range(start, stop), desc="save all traces"):
            if nf is not None:
                MySoapySDR.numpy_save(get_dataset_path_unpack_nf(dir, i), nf[i - start])
            if ff is not None:
                MySoapySDR.numpy_save(get_dataset_path_unpack_ff(dir, i), ff[i - start])
    l.LOGGER.info("done!")

def load_all_traces(dir, start=0, stop=0, nf_wanted=True, ff_wanted=True, bar=True, start_point=0, end_point=0):
    """Load traces contained in DIR. Can be packed or unpacked. Return a 2D
    np.array of shape (nb_traces, nb_samples). START and STOP can be specified
    to load a specific range of file from the disk for an unpacked
    dataset. This function load traces conditionnaly, it returns
    None/empty/zeroes if traces doesn't exists. Beware to not overflow the
    memory. NF and FF can be set to False to not load them in an unpacked
    dataset.

    Traces truncation during loading can be achieved using START_POINT and
    END_POINT. If START_POINT is set to different from 0, use it as start index
    during loading the traces. If END_POINT is set to different from 0, use it
    as end index during loading the traces.

    """
    l.LOGGER.info("Loading traces...")
    if is_dataset_packed(dir):
        # NOTE: Following code is not working anymore without
        # MySoapySDR.numpy_load stub, but I don't know if it can handle packed
        # dataset for now.
        nf_p = get_dataset_path_pack_nf(dir)
        ff_p = get_dataset_path_pack_ff(dir)
        assert(path.exists(nf_p) and path.exists(ff_p))
        l.LOGGER.info("Done!")
        return np.load(nf_p), np.load(ff_p)
    elif is_dataset_unpacked(dir):
        nf, ff = None, None
        stop = get_nb(dir) if stop < 1 else stop
        nb = stop - start
        nf_exist = get_dataset_is_nf_exist(dir)
        ff_exist = get_dataset_is_ff_exist(dir)
        if nf_wanted is True and nf_exist is True:
            nf = [None] * nb
            iterator = tqdm(range(start, stop), desc="Load NF traces") if bar else list(range(start, stop))
            for i in iterator:
                nf_p = get_dataset_path_unpack_nf(dir, i)
                # NOTE: Make sure "copy" is enabled to not overflow the memory
                # after truncating loaded trace.
                nf[i - start] = truncate(MySoapySDR.numpy_load(nf_p), start=start_point, end=end_point, copy=True)
        else:
             l.LOGGER.warning("No loaded NF traces!")
        if ff_wanted is True and ff_exist is True:
            ff = [None] * nb
            iterator = tqdm(range(start, stop), desc="Load FF traces") if bar else list(range(start, stop))
            for i in iterator:
                ff_p = get_dataset_path_unpack_ff(dir, i)
                # NOTE: Make sure "copy" is enabled to not overflow the memory
                # after truncating loaded trace.
                ff[i - start] = truncate(MySoapySDR.numpy_load(ff_p), start=start_point, end=end_point, copy=True)
        else:
            l.LOGGER.warning("No loaded FF traces!")
        if nf_exist or ff_exist:
            l.LOGGER.info("Done!")
            return nf, ff
        else:
            l.LOGGER.error("No loaded traces!")
            return None, None
    else:
        l.LOGGER.error("Unknown dataset format!")
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

def reshape_needed(arr):
    """Return True if all arrays inside ARR are not of equal length (i.e. a
    reshape() call is needed before to create a 2D np.array).

    """
    len_ref = len(arr[0])
    for i in range(len(arr)):
        if len(arr[i]) != len_ref:
            return True
    return False

def reshape(arr):
    """Reshape a Python list of 1D np.array to same dimension.

    It find the array of minimum len and use this length to shrink other array
    from their end. It allows to create a 2D .np.array.

    """
    len_min = sys.maxsize
    for i in range(len(arr)):
        if len(arr[i]) < len_min:
            len_min = len(arr[i])
    for i in range(len(arr)):
        arr[i] = arr[i][:len_min]
    return arr

def truncate_min(arr):
    """Truncate traces to minimum of the array in place.

    Truncate all the traces (1D np.array) contained in ARR (list) to the length
    of the smaller one. Usefull to create a 2D np.array.

    This function work in place, but returns the new array ARR with truncated
    traces for scripting convenience.

    """
    target_len = sys.maxsize
    for s in arr:
        target_len = len(s) if len(s) < target_len else target_len
    for idx, s in enumerate(arr):
        arr[idx] = s[:target_len]
    return arr

def truncate(traces, start=0, end=0, copy=False):
    """Truncate all traces containted in TRACES (1D or 2D np.array) according
    to START and END if they are set.

    If COPY is set to True, return a copy of the input traces (useful to delete
    the old reference to input traces if their size is huge).

    """
    if traces.ndim == 2:
        if start != 0:
            traces = traces[:,start:]
        if end != 0:
            traces = traces[:,:end-start]
    elif traces.ndim == 1:
        if start != 0:
            traces = traces[start:]
        if end != 0:
            traces = traces[:end-start]
    return traces if copy is False else np.copy(traces)
