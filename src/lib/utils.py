"""Utilities functions to work with Python.

First created to implement type conversion helper functions."""

import math

import numpy as np

import lib.load as load

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

def bytes_hex_to_npy_int2(x, len):
    """Convert a number in X stored as bytes (hexadecimal in base 16) into a
    Numpy array of uint8 (digits in base 10 between 0 and 255). For LEN, refer
    to int_to_str_hex() documentation.

    """
    assert type(x) == bytes
    # NOTE: Needs to specify length when using format, otherwise zeroes are not
    # printed and bytearray will throw an error.
    y = str_hex_to_npy_int(int_to_str_hex(bytes_hex_to_int_single(x), len))
    assert type(y) == np.ndarray
    return y

def int_to_str_hex(x, len):
    """Return an hexadecimal (base 16) representation contained in a string of
    the X integer in base 10. LEN is the size of X in bytes and is required to
    handle leading or trailing zeroes.

    """
    return "{:0{}x}".format(x, len * 2)

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
    return "".join([f'{y:02x}' for y in npy_int.tobytes()])

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

def bytes_hex_to_int_single(x):
    """Convert a number in X stored as bytes (hexadecimal in base 16) into a
    single integer (digits in base 10).

    """
    assert type(x) == bytes
    y = int("".join([f'{xi:02x}' for xi in x]), base=16)
    assert type(y) == int
    return y

def hamw(n):
    """Return the Hamming Weight of the number N."""
    # NOTE: Alternative implementation using str built-in class.
    # return bin(n).count("1")
    return int(n).bit_count()

def hamd(n, m):
    """Return the Hamming Distance between numbers N and M."""
    return hamw(n ^ m)

def db2m(db):
    """Convert an attenuation [dB] to distance [meters] using Free Space Path
    Loss (FSPL) equation.

    """
    # NOTE: Assume using 2.4 GHz band.
    return 10 ** ((db - 20 * math.log10(2.4e9) + 147.55) / 20)

def m2db(m):
    """Convert a distance [meters] to an attenuation [dB] using Free Space Path
    Loss (FSPL) equation.

    """
    return 20 * math.log10(m) + 20 * math.log10(2.4e9) - 147.55
