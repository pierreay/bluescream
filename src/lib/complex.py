"""Operations on complex numbers.

Functions:

- is_iq(): Is a signal composed of IQ samples.

- get_amplitude(): Get the magnitude of a signal from IQ samples.

- get_phase(): Get the phase of a signal from IQ samples.

- p2r(): Convert an IQ signal to regular/cartesian representation.

- r2p(): Convert an IQ signal to polar representation.

"""

import numpy as np

def is_iq(s):
    """Return True is the signal S is composed of IQ samples, False otherwise."""
    return s.dtype == np.complex64

def get_amplitude(traces):
    """Get the amplitude of one or multiples traces.

    From the TRACES 2D np.array of shape (nb_traces, nb_samples) or the 1D
    np.array of shape (nb_samples) containing IQ samples, return an array with
    the same shape containing the amplitude of the traces.

    If traces contains signals in another format than np.complex64, silently
    return the input traces such that this function can be called multiple
    times.

    """
    if traces.dtype == np.complex64:
        return np.abs(traces)
    else:
        return traces

def get_phase(traces):
    """Get the phase of one or multiples traces.

    From the TRACES 2D np.array of shape (nb_traces, nb_samples) or the 1D
    np.array of shape (nb_samples) containing IQ samples, return an array with
    the same shape containing the phase of the traces.

    If traces contains signals in another format than np.complex64, silently
    return the input traces such that this function can be called multiple
    times.

    """
    if traces.dtype == np.complex64:
        return np.angle(traces)
    else:
        return traces

def p2r(radii, angles):
    """Complex polar to regular.

    Convert a complex number from Polar coordinate to Regular (Cartesian)
    coordinates.

    The input and output is symmetric to the r2p() function. RADII is
    the magnitude while ANGLES is the angles in radians (default for
    np.angle()).

    Example using r2p for a regular-polar-regular conversion:
    > polar = r2p(2d_ndarray_containing_iq)
    > polar[0].shape
    (262, 2629)
    > polar[1].shape
    (262, 2629)
    > regular = p2r(polar[0], polar[1])
    > regular.shape
    (262, 2629)
    > np.array_equal(arr, regular)
    False
    > np.isclose(arr, regular)
    array([[ True,  True,  True, ...,  True,  True,  True], ..., [ True,  True,  True, ...,  True,  True,  True]])

    Source: https://stackoverflow.com/questions/16444719/python-numpy-complex-numbers-is-there-a-function-for-polar-to-rectangular-co?rq=4
    """
    return radii * np.exp(1j * angles)

def r2p(x):
    """Complex regular to polar.

    Convert a complex number from Regular (Cartesian) coordinates to Polar
    coordinates.

    The input X can be a 1) single complex number 2) a 1D ndarray of complex
    numbers 3) a 2D ndarray of complex numbers. The returned output is a tuple
    composed of a 1) two scalars (float32) representing magnitude and phase 2)
    two ndarray containing the scalars.

    Example using a 2D ndarray as input:
    r2p(arr)[0][1][0] -> magnitude of 1st IQ of 2nd trace.2
    r2p(arr)[1][0][1] -> phase of 2nd IQ of 1st trace.

    Source: https://stackoverflow.com/questions/16444719/python-numpy-complex-numbers-is-there-a-function-for-polar-to-rectangular-co?rq=4
    """
    return np.abs(x), np.angle(x)
