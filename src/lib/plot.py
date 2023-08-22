"""Plot traces."""

from os import path
import numpy as np
import matplotlib.pyplot as plt

# * Global variables

NFFT = 256

# * Simple plots used interactively for debugging

def savetmp(filename):
    plt.savefig(path.join("/tmp", filename))
    plt.close()

def plot_time_simple(s):
    plt.plot(s)
    plt.show()

def plot_spec_simple(s):
    plt.specgram(s, NFFT)
    plt.show()

def save_spec_simple(s, i=0):
    plt.specgram(s, NFFT)
    savetmp("spec{}.png".format(i))

def plot_simple(s):
    plot_time_simple(s)
    plot_spec_simple(s)

def plot_time_compare(s1, s2):
    assert(s1.shape == s2.shape)
    plt.plot(s1)
    plt.plot(s2)
    plt.show()

def plot_spec_compare(s1, s2):
    assert(s1.shape == s2.shape)
    plt.specgram(s1, NFFT)
    savetmp("spec1.png")
    plt.specgram(s2, NFFT)
    savetmp("spec2.png")

# * Special plot for analysis

def plot_metadata_balance(ks, pt):
    """Take 2D np.array of KS keys and PT plaintexts, show a boxplot of imbalance"""
    sbi = ks ^ pt
    cnt = [0] * len(sbi[0])
    for i in range(len(sbi[0])):
        sbiu = np.unique(sbi[:, i], return_counts=True)
        cnt[i] = sbiu[1]
    plt.boxplot(cnt)
    plt.title("balance for each subbyte in dataset")
    plt.suptitle("(perfect balance = very tight box around average at (nb_trace / 256))")
    plt.xlabel("subbyte")
    plt.ylabel("count")
    plt.show()
