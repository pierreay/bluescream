"""Utilities functions to work with Python.

First created to implement type conversion helper functions."""

import lib.load as load

import numpy as np

def str_hex_to_npy_int(str_hex):
    """Convert a string contain an hexadecimal number STR_HEX to a Numpy
    array containing integers. NOTE: The string should not be prefixed
    using 0x.

    """
    assert(type(str_hex) == str)
    return np.array(str_hex_to_list_int(str_hex), dtype=np.uint8)

def str_hex_to_list_int(str_hex):
    """Convert a string contain an hexadecimal number STR_HEX to a Python list
    containing integers. NOTE: The string should not be prefixed using 0x.

    """
    assert(type(str_hex) == str)
    return [int(c) for c in bytearray.fromhex(str_hex)]

def npy_int_to_str_hex(npy_int):
    """Convert a Numpy array NPY_INT containing integers to a string contain an
    hexadecimal number. NOTE: The integers have to be np.uint8 and the string
    will not be prefixed using 0x.

    """
    assert(type(npy_int) == np.ndarray and npy_int.dtype == np.uint8)
    return "".join([f'{y:x}' for y in npy_int.tobytes()])

def npy_int_to_list_str_hex(npy_int):
    """Convert a Numpy array NPY_INT containing integers to a list containing
    strings representing an hexadecimal number.

    """
    assert(type(npy_int) == np.ndarray and npy_int.dtype == np.uint8)
    return [hex(x) for x in npy_int]

def list_array_to_2d_array(arr):
    """Convert a list or a 1D array to a 2D array.

    Convert ARR, a Python list containing 1D np.array or a single 1D np.array,
    to a 2D np.array.

    Return the 2D np.array, but if ARR is None, return None.

    """
    if arr is None:
        return None
    elif isinstance(arr, list) and load.reshape_needed(arr):
        arr = load.reshape(arr)
    return np.array(arr, ndmin=2)
