"""Utilities functions to work with Python."""

import numpy as np

def str_hex_to_npy_int(str_hex):
    """Convert a string contain an hexadecimal number STR_HEX to a Numpy
    array containing integers. NOTE: The string should not be prefixed
    using 0x.

    """
    return np.array(str_hex_to_list_int(str_hex))

def str_hex_to_list_int(str_hex):
    """Convert a string contain an hexadecimal number STR_HEX to a Python list
    containing integers. NOTE: The string should not be prefixed using 0x.

    """
    return [int(c) for c in bytearray.fromhex(str_hex)]
