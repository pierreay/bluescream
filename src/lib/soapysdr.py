"""Implement SDR classes using SoapySDR. Allows to use a single or multiple
SDRs in parallel using threads."""

import time
from time import sleep
import os
import errno
from os import path
import numpy as np
from threading import Thread
import SoapySDR

import lib.log as l
import lib.load as load
import lib.analyze as analyze
import lib.plot as libplot
import lib.complex as complex

# Path of the FIFO file used between MySoapySDRs and MySoapySDRsClient.
FIFO_PATH = "/tmp/soapysdr.fifo"

class MySoapySDRs():
    # Polling interval of the listening radio thread, i.e. sleeping time,
    # i.e. interval to check whether a command is queued in the FIFO or
    # not. High enough to not consume too much CPU (here, 5%) but small enough
    # to not introduce noticeable delay to the recording.
    POLLING_INTERVAL = 1e-6

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def __init__(self):
        l.LOGGER.debug("MySoapySDRs.__init__()")
        # List of registered SDRs.
        self.sdrs = []
        # List of registered SDRs' indexes.
        # NOTE: The IDXs must be unique, as the IDX is used as filename
        # identifier and as SoapySDR's result index.
        self.registered_idx = []

    def register(self, sdr):
        l.LOGGER.debug("MySoapySDRs.register(idx={})".format(sdr.idx))
        # Check if SDR is not already initialized.
        if sdr.idx in self.registered_idx:
            raise Exception("The same SDR is registered twice!")
        # Proceed to the registration.
        self.sdrs.append(sdr)
        self.registered_idx.append(sdr.idx)
        # Temporary hack to be compatible with nrf52_whad.py who access
        # self.radio.fs variable. This imply to have the same sampling rate
        # accross two SDRs.
        self.fs = sdr.fs

    def open(self):
        l.LOGGER.debug("MySoapySDRs.open()")
        for sdr in self.sdrs:
            sdr.open()

    def close(self):
        l.LOGGER.debug("MySoapySDRs.close()")
        for sdr in self.sdrs:
            sdr.close()
        if path.exists(FIFO_PATH):
            # Delete the FIFO.
            os.remove(FIFO_PATH)

    def record(self, duration = None):
        """Perform a recording of DURATION seconds.

        Spawn a thread for each radio and start recording. Block until all
        recordings finished and all threads join.

        """
        l.LOGGER.debug("MySoapySDRs.record(duration={}).enter".format(duration))
        thr = [None] * len(self.sdrs)
        for idx, sdr in enumerate(self.sdrs):
            thr[idx] = Thread(target=sdr.record, args=(duration,))
            thr[idx].start()
        for sdr in self.sdrs:
            thr[idx].join()
        l.LOGGER.debug("MySoapySDRs.record(duration={}).exit".format(duration))

    def accept(self):
        l.LOGGER.debug("MySoapySDRs.accept()")
        for sdr in self.sdrs:
            sdr.accept()

    def save(self, dir = None, reinit = True):
        l.LOGGER.debug("MySoapySDRs.save(dir={})".format(dir))
        for sdr in self.sdrs:
            sdr.save(dir, reinit=reinit)

    def disable(self):
        for sdr in self.sdrs:
            sdr.disable()

    def listen(self):
        """Put the radio in server mode.

        This command will create a FIFO and listen for commands on it. The
        MySoapySDRsClient class can be instantiated in another process to
        communicate with this server mode.

        """
        def __ack__():
            """Acknoledge the end of the command execution by opening-closing
            the FIFO in W mode.

            """
            with open(FIFO_PATH, "w") as fifo_w:
                pass

        def __create_fifo():
            """Create the named pipe (FIFO)."""
            # Remove previously created FIFO.
            try:
                os.remove(FIFO_PATH)
            except Exception as e:
                if not isinstance(e, FileNotFoundError):
                    raise e
            # Create the named pipe (FIFO).
            try:
                os.mkfifo(FIFO_PATH)
            except OSError as oe:
                raise
                # if oe.errno != errno.EEXIST:
                #     raise

        # Create the FIFO.
        __create_fifo()
        # Open the FIFO.
        l.LOGGER.info("process #{} ready for listening!".format(os.getpid()))
        with open(FIFO_PATH, "r") as fifo:
            l.LOGGER.debug("opened FIFO at {}".format(FIFO_PATH))
            # Infinitely listen for commands and execute the radio commands accordingly.
            while True:
                cmd = fifo.read()
                if len(cmd) > 0:
                    l.LOGGER.debug("fifo -> {}".format(cmd))
                    # Available commands on server-side.
                    cmds = {"record": self.record, "accept": self.accept, "save": self.save, "disable": self.disable}
                    # Execute the received command and acknowledge its execution.
                    if cmd in cmds:
                        cmds[cmd]()
                        __ack__()
                    elif cmd == "quit":
                        l.LOGGER.info("quit the listening mode")
                        break
                # Smart polling.
                sleep(self.POLLING_INTERVAL)

    def get_nb(self):
        """Get the number of currently registed SDRs."""
        return len(self.sdrs)

    def get_signal(self, idx):
        """Return the receveid signal of radio indexed by IDX."""
        return self.sdrs[idx].get_signal()

class MySoapySDR():
    """SoapySDR controlled radio.

    Typical workflow:

    1. Initialize: __init__() -> open()

    2. Records: [ record() -> accept() ] ... -> save()

    3. Records: [ record() -> accept() ] ... -> save()

    4. Deinitialize: close()

    """
    # * Custom dtype
    # It is used to match the CS16 type of SoapySDR, allowing to save disk
    # space but requires conversion happening in this module, since Numpy can
    # only work with np.complex64 using float32.
    DTYPE = np.dtype([('real', np.int16), ('imag', np.int16)])
    # XXX: May be simpler to use np.float16?
    # To not waste space but get ride of int <-> float casting/rescaling? Since
    # we need float anyway for signal processing...

    @staticmethod
    def numpy_save(file, arr):
        """Stub for numpy.save handling our custom dtype.

        Save to disk the trace stored in ARR using our custom dtype. ARR.dtype
        can be np.complex64 (will be converted) or MySoapySDR.DTYPE (will be
        saved as it).

        """
        assert(arr.dtype == np.complex64 or arr.dtype == MySoapySDR.DTYPE)
        if arr.dtype == np.complex64:
            arr = MySoapySDR.complex64_to_dtype(arr)
        arr.tofile(file)

    @staticmethod
    def numpy_load(file):
        """Stub for numpy.load handling our custom dtype.

        The loaded FILE has to be in the MySoapySDR.DTYPE format, which will be
        converted into np.complex64 for processing.

        """
        return MySoapySDR.dtype_to_complex64(np.fromfile(file, dtype=MySoapySDR.DTYPE))

    @staticmethod
    def dtype_to_complex64(arr):
        """Convert an array from our custom DTYPE to a standard np.complex64
        (composed of 2 np.float32)."""
        assert(arr.dtype == MySoapySDR.DTYPE)
        # Don't need to check any boundaries here since casting from np.int16
        # to np.float32 is safe.
        return arr.view(np.int16).astype(np.float32).view(np.complex64)

    @staticmethod
    def complex64_to_dtype(arr):
        """Convert an array from a standard np.complex64 (composed of 2
        np.float32) to our custom DTYPE."""
        assert(arr.dtype == np.complex64)
        # Check that the signal ready to convert is not normalized, otherwise,
        # it will give a zeroed signal. It should not happened with the
        # hardened complex.p2r() function.
        assert not analyze.is_normalized(complex.get_amplitude(arr)), "tried to save normalized signal, it will give a zeroed signal"
        assert not analyze.is_normalized(complex.get_phase(arr)), "tried to save normalized signal, it will give a zeroed signal"
        # Check that no value contained in arr is superior to maximum or
        # inferior to minimum of np.int16 (-2^15 or +2^15), since casting from
        # np.float32 to np.int16 is not safe.
        assert(arr[arr.real < np.iinfo(np.int16).min].shape == (0,))
        assert(arr[arr.real > np.iinfo(np.int16).max].shape == (0,))
        assert(arr[arr.imag < np.iinfo(np.int16).min].shape == (0,))
        assert(arr[arr.imag > np.iinfo(np.int16).max].shape == (0,))
        return arr.view(np.float32).astype(np.int16).view(MySoapySDR.DTYPE)

    def __init__(self, fs, freq, idx = 0, enabled = True, duration = 1, dir = "/tmp", gain = 76):
        l.LOGGER.debug("MySoapySDR.__init__(fs={},freq={},idx={},enabled={},duration={},dir={},gain={})".format(fs, freq, idx, enabled, duration, dir, gain))
        assert gain >= 0, "Gain should be positive!"
        # NOTE: Automatically convert floats to integers (allows using scentific notation, e.g. e6 or e9).
        self.fs = int(fs)
        self.freq = int(freq)
        self.gain = int(gain)
        self.idx = idx
        self.enabled = enabled
        # Default duration if nothing is specified during self.record().
        self.duration = duration
        # Default directory if nothing is specified during self.save().
        self.dir = dir
        # Recording acceptation flag.
        self.accepted = False # Set to True by accept() and to False by save().
        # Recording buffers.
        self.rx_signal = None
        self.rx_signal_candidate = None
        # Initialize the SDR driver.
        if self.enabled:
            results = SoapySDR.Device.enumerate()
            # Check result of device detection and requested index.
            if len(results) == 0:
                raise Exception("SoapySDR didn't detected any device!")
            if idx > len(results):
                raise Exception("SoapySDR didn't detected the requested radio index!")
            # Initialize the radio with requested parameters.
            self.sdr = SoapySDR.Device(results[idx])
            self.sdr.setSampleRate(SoapySDR.SOAPY_SDR_RX, 0, fs)
            self.sdr.setFrequency(SoapySDR.SOAPY_SDR_RX, 0, freq)
            self.sdr.setGain(SoapySDR.SOAPY_SDR_RX, 0, gain)
            self.sdr.setAntenna(SoapySDR.SOAPY_SDR_RX, 0, "TX/RX")

    def open(self):
        # Initialize the SoapySDR streams.
        if self.enabled:
            l.LOGGER.info("initialize streams for radio #{}".format(self.idx))
            # From SoapySDR/include/SoapySDR/Device.h:
            # - "CF32" - complex float32 (8 bytes per element)
            # - "CS16" - complex int16   (4 bytes per element)
            # From SoapyUHD/SoapyUHDDevice.cpp/getNativeStreamFormat():
            # UHD and the hardware use "CS16" format in the underlying transport layer.
            self.rx_stream = self.sdr.setupStream(SoapySDR.SOAPY_SDR_RX, SoapySDR.SOAPY_SDR_CS16)
            self.sdr.activateStream(self.rx_stream)
            # Initialize for first recordings.
            self.reinit()

    def close(self):
        if self.rx_stream is not None:
            l.LOGGER.debug("MySoapySDR(idx={}).close().enter".format(self.idx))
            self.sdr.deactivateStream(self.rx_stream)
            self.sdr.closeStream(self.rx_stream)
            l.LOGGER.debug("MySoapySDR(idx={}).close().leave".format(self.idx))

    def record(self, duration = None):
        # Choose default duration configured during __init__ if None is given.
        if duration is None:
            duration = self.duration
        if self.enabled:
            l.LOGGER.info("start record for radio #{} during {:.2}s".format(self.idx, duration))
            samples = int(duration * self.fs)
            # XXX: Adjust rx_buff_len dynamically based on the duration/number
            # of samples.
            # NOTE: Increasing this limits will prevent overflow or underruns,
            # but will also increase the minimal recording time (relative to
            # the sampling rate). Good values are between 2^20 for small
            # recordings (e.g. 0.1 s) and 2^24 for large recordings (e.g. 3 s).
            rx_buff_len = pow(2, 20)
            rx_buff = np.array([0] * rx_buff_len, MySoapySDR.DTYPE)
            self.rx_signal_candidate = np.array([0], MySoapySDR.DTYPE)
            while len(self.rx_signal_candidate) < samples:
                sr = self.sdr.readStream(self.rx_stream, [rx_buff], rx_buff_len, timeoutUs=10000000)
                if sr.ret == rx_buff_len and sr.flags == 1 << 2:
                    self.rx_signal_candidate = np.concatenate((self.rx_signal_candidate, rx_buff))
            l.LOGGER.debug("MySoapySDR(idx={}).record().leave".format(self.idx))
        else:
            time.sleep(duration)

    def accept(self):
        if self.enabled:
            l.LOGGER.debug("MySoapySDR(idx={}).accept()".format(self.idx))
            self.accepted = True
            self.rx_signal = np.concatenate((self.rx_signal, self.rx_signal_candidate))

    def save(self, dir = None, reinit = True):
        """Save the last accepted recording on disk.

        The saved .npy file will use the MySoapySDR.DTYPE data type.

        :param reinit: If set to False, do not re-initialize the radio for a
        next recording. MySoapySDR.reinit() should be called manually later.

        """
        if dir is None:
            dir = self.dir
        if self.enabled is True and self.accepted is True:
            dir = path.expanduser(dir)
            l.LOGGER.info("save recording of radio #{} into directory {}".format(self.idx, dir))
            load.save_raw_trace(self.rx_signal, dir, self.idx, 0)
            # Re-initialize for further recordings if requested [default].
            if reinit is True:
                self.reinit()

    def reinit(self):
        """Re-initialize the recording state and buffers such that a new
        recording can occur."""
        l.LOGGER.debug("re-initialization")
        self.accepted = False
        # Delete the signals since buffers can be large.
        if self.rx_signal is not None:
            del self.rx_signal
        self.rx_signal = np.array([0], MySoapySDR.DTYPE)
        if self.rx_signal_candidate is not None:
            del self.rx_signal_candidate
        self.rx_signal_candidate = None

    def disable(self):
        """Disable the radio."""
        l.LOGGER.info("disable radio #{}".format(self.idx))
        self.enabled = False

    def get_signal(self):
        """Return the receveid signal.

        The returned signal will be I/Q represented using np.complex64 numbers.

        """
        sig = MySoapySDR.dtype_to_complex64(self.rx_signal)
        assert sig.dtype == np.complex64, "Signal should be complex numbers!"
        return sig
class MySoapySDRsClient():
    """Control a MySoapySDRs object living in another process.

    This class implements a command sending mechanism through a named pipe
    (FIFO) mechanism allowing to control another process that initialized the
    radio at startup. It allows to perform multiple radio recordings without
    re-initializing the radio's driver while using different Python process
    because of different calls from Bash.

    """
    # Time sleeped to simulate wait a SoapySDR server's command return [s].
    STUB_WAIT = 0.5

    def __init__(self, enabled = True):
        l.LOGGER.info("Initialize a SoapySDR client... (enabled={})".format(enabled))
        self.enabled = enabled

    def __cmd__(self, cmd):
        """Send a command through the FIFO."""
        # NOTE: The only way I found to reliably send the commands individually
        # is to open/close/sleep for each commands. Otherwise, the commands
        # arrived concatenated at the reader process.
        if self.enabled is True:
            l.LOGGER.debug("fifo <- {}".format(cmd))
            with open(FIFO_PATH, "w") as fifo:
                fifo.write(cmd)
            sleep(0.1)

    def __wait__(self):
        """Wait for the previous command to complete."""
        if self.enabled is True:
            # NOTE: Hacky trick here, Linux is making the opening of a FIFO in
            # read mode blocking until a writer opened it. Here, we simply wait
            # for the radio server to open it in write mode, and exit
            # immediately. Use this only for long command, because if the
            # server-side opening in write mode happen before the client-side
            # opening in read mode, then it will deadlock.
            l.LOGGER.debug("waiting...")
            with open(FIFO_PATH, "r") as fifo:
                pass
            l.LOGGER.debug("wait completed")
        else:
            l.LOGGER.debug("Waiting stub for disabled SoapySDR client by sleeping {}s".format(self.STUB_WAIT))
            sleep(self.STUB_WAIT)

    def record(self):
        """Call the MySoapySDRs.record() method through the FIFO. Wait for the
        command to complete.

        """
        self.__cmd__("record")
        self.__wait__()

    def accept(self):
        """Call the MySoapySDRs.accept() method through the FIFO. Returns
        immediately."""
        self.__cmd__("accept")

    def save(self):
        """Call the MySoapySDRs.save() method through the FIFO. Returns
        immediately."""
        self.__cmd__("save")

    def disable(self):
        """Call the MySoapySDRs.disable() method through the FIFO. Returns
        immediately."""
        self.__cmd__("disable")

    def quit(self):
        """Send instruction to quit the radio listening in server mode. Returns
        immediately.

        """
        self.__cmd__("quit")
