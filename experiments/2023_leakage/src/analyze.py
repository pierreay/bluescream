#!/usr/bin/env python3

import os
import io
import numpy as np
from tqdm import tqdm
from matplotlib import pyplot as plt

# * Global variables

# Input.
INPUT_DIR = os.getenv("SCREAMING_CHANNELS_ANNEX")
INPUT_NB = 99

# Debug flag.
DEBUG = False

# * Debug

def print_number(x, label="x"):
    print("{}_base2_size={} bits".format(label, len("{:b}".format(x))))
    print("{}_base2=0b{:b}".format(label, x))
    print("{}_base10={}".format(label, x))
    print("{}_base16=0x{:x}".format(label, x))

# * Input

def read_file(path):
    with io.open(path, "r") as f:
        return f.readline()[:-1]

def load_trace(dir, nb):
    trace_nf_p = "{}/{}_trace_nf.npy".format(dir, nb)
    trace_ff_p = "{}/{}_trace_rf.npy".format(dir, nb)
    if DEBUG:
        print("np.load({})".format(trace_nf_p))
        print("np.load({})".format(trace_ff_p))
    trace_nf = np.load(trace_nf_p) 
    trace_ff = np.load(trace_ff_p)
    if DEBUG:
        print("trace_nf.shape={}".format(trace_nf.shape))
        print("trace_ff.shape={}".format(trace_ff.shape))
    return trace_nf, trace_ff

def load_traces(dir, nb):
    trace_nf, trace_ff = load_trace(dir, 0)
    for i in tqdm(range(1, nb)):
        trace_nf_i, trace_ff_i = load_trace(dir, i)
        trace_nf = np.vstack((trace_nf, trace_nf_i))
        trace_ff = np.vstack((trace_ff, trace_ff_i))
    return trace_nf, trace_ff

def load_metadata(dir, nb):
    p = read_file("{}/{}_p.txt".format(dir, nb))
    # Only for 67059239-5b11-49b2-86ba-6c6ed84c3f28 dataset, where the saving
    # mechanism for SKC_C was broken, but SKD_C was chosen and fixed, so we can
    # recreate it here.
    p = (int(p) << 64) | 0xdeadbeefdeadbeef
    if DEBUG:
        print_number(p, "p")
    k = read_file("{}/k.txt".format(dir))
    k = int(k, 16)
    if DEBUG:
        print_number(k, "k")
    param_nf = []
    param_ff = []
    with io.open("{}/params.txt".format(dir), "r") as f:
        param_nf = f.readline()[:-1]
        param_ff = f.readline()[:-1]
    params = [param_nf, param_ff]
    if DEBUG:
        print("params={}".format(params))
    return p, k, params

def load_metadatas(dir, nb):
    p, k, params = load_metadata(dir, 0)
    for i in list(range(1, nb)):
        p_i, _1, _2 = load_metadata(dir, i)
        p = np.vstack((p, p_i))
    return p, k, params

# * Analysis

def normalize(arr):
    """Apply min-max feature scaling normalization to a 1D array."""
    return (arr - np.min(arr)) / (np.max(arr) - np.min(arr))

def subbyte(x, nb):
    return (x >> nb * 8) & 0xFF

def plot_trace_variance(trace, title=""):
    var = np.var(trace, axis=0)
    plt.plot(trace[0], label="trace[0]")
    plt.plot(var, label="np.var(trace, axis=0)")
    plt.title(title)
    plt.legend()
    plt.show()

# * Script

if __name__ == "__main__":
    # * Input.
    trace_nf, trace_ff = load_traces(INPUT_DIR, INPUT_NB)
    p, k, params = load_metadatas(INPUT_DIR, INPUT_NB)
    # * Analysis.
    plot_trace_variance(trace_nf, title="trace_nf")
    plot_trace_variance(trace_ff, title="trace_ff")
