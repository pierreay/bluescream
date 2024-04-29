import sys

def np_size(npobj):
    """Return the size in megabytes (10e6) of the NPOBJ numpy object."""
    return npobj.size * npobj.itemsize / 1e6

def info(type, value, tb):
    if hasattr(sys, 'ps1') or not sys.stderr.isatty() or type != AssertionError:
        # We are in interactive mode or we don't have a tty-like
        # device, so we call the default hook.
        sys.__excepthook__(type, value, tb)
    else:
        import traceback, ipdb
        # We are not in interactive mode, print the exception.
        traceback.print_exception(type, value, tb)
        print
        # Then start the debugger in post-mortem mode.
        ipdb.pm()

def plot_oneline(arr):
    import numpy as np; import matplotlib.pyplot as plt; plt.plot(np.abs(arr)); plt.show()

sys.excepthook = info
