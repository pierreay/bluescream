"""Utilities functions to work with Python.

First created to implement type conversion helper functions."""

import lib.load as load

import numpy as np

def bytes_hex_to_npy_int(input):
    """Convert INPUT bytes representing an hexadecimal number in ASCII to a
    Numpy array of uint8.

    Example:
    > bytes_hex_to_npy_int(b'bbaaaabb')
    [187, 170, 170, 187]

    """
    assert type(input) == bytes
    # NOTE: Remove unwanted quotes from bytes to string conversion.
    # NOTE: Verify that this function is not fucked up if there is zeroes in
    # the input. To prevent using it without verifying it, put a debug here.
    import ipdb; ipdb.set_trace()
    return np.array([int(c) for c in bytearray.fromhex(str(input)[2:-1])], dtype=np.uint8)

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

def hamw(n):
    """Return the Hamming Weight of the number N."""
    # NOTE: Alternative implementation using str built-in class.
    # return bin(n).count("1")
    return int(n).bit_count()

def hamd(n, m):
    """Return the Hamming Distance between numbers N and M."""
    return hamw(n ^ m)
