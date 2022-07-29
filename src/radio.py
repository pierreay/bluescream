"""Allows multiple SDR to be used for recording Screaming Channels leaks.

Classes:

        RadioType: Enumeration of all supported SDRs.
        GNURadio: SDR configured through GNURadio interface.
        SoapySDR: SDR configured through SoapySDR interface.

"""
# Core modules.
import enum

# External modules.
from gnuradio import blocks, gr, uhd, iio
import osmosdr

# Local modules.
import log as l

RadioType = enum.Enum("RadioType", ["USRP", "HACKRF", "BLADERF", "PLUTOSDR"])

class GNURadio(gr.top_block):
    """Class of a supported SDR accessed through GNURadio.

    Methods:

        start: Start the recording.
        reset: Reset the current trace.
        stop: Stop the recording.

    """
    def __init__(self, outfile, radio, address, antenna, frequency,
                 sampling_rate, usrp_gain, hackrf_gain, hackrf_gain_if,
                 hackrf_gain_bb, plutosdr_gain):
        """Initialize the SDR.

        Initialize and configure the SDR. Ready to record.

        :raises Exception: If the radio 'type' is not supported.

        """
        l.LOGGER.debug("Initialize the '{}' SDR".format(radio))
        super().__init__(self, "Top Block")

        # Set common parameters.
        self.outfile       = outfile
        self.radio         = RadioType[radio]
        self.address       = address
        self.antenna       = antenna
        self.frequency     = frequency
        self.sampling_rate = sampling_rate

        # Create source radio blocks and set per-radio parameters.
        if self.radio in (RadioType.USRP):
            rad_addr    = "addr={}".format(self.address)
            rad_stream  = uhd.stream_args(cpu_format="fc32", channels=[0])
            radio_block = uhd.usrp_source(rad_addr, rad_stream)
            radio_block.set_center_freq(self.frequency)
            radio_block.set_sample_rate(self.sampling_rate)
            radio_block.set_antenna(self.antenna)
            radio_block.set_gain(usrp_gain)
        elif self.radio in (RadioType.HACKRF, RadioType.BLADERF):
            gr_args = "numchan=1 {}=0".format("hackrf" if self.Radio == RadioType.HACKRF else "bladerf")
            radio_block = osmosdr.source(args=gr_args)
            radio_block.set_center_freq(self.frequency, 0)
            radio_block.set_sample_rate(self.sampling_rate, 0)
            radio_block.set_bandwidth(self.sampling_rate, 0)
            radio_block.set_antenna("", 0)
            radio_block.set_gain_mode(True, 0)
            radio_block.set_gain(hackrf_gain, 0)
            radio_block.set_if_gain(hackrf_gain_if, 0)
            radio_block.set_bb_gain(hackrf_gain_bb, 0)
            radio_block.set_dc_offset_mode(True, 0)
            radio_block.set_iq_balance_mode(True, 0)
        elif self.radio == RadioType.PLUTOSDR:
            uri = self.address.encode("ascii")
            freq = int(frequency)
            sr = int(sampling_rate)
            bw = sr
            bufsize = 0x8000
            gainmode = "manual"
            radio_block = iio.pluto_source(uri, freq, sr, 1 - 1, bw, bufsize,
                                           True, True, True, gain_mode,
                                           plutosdr_gain, "", True)
        else:
            raise Exception("Radio type '{}' is not supported".format(self.radio))

        # Create sink file blocks and connect them.
        self._file_sink = blocks.file_sink(gr.sizeof_gr_complex, self.outfile)
        self.connect((radio_block, 0), (self._file_sink, 0))

    def reset(self):
        """Remove the current trace file and get ready for a new trace."""
        self._file_sink.open(self.outfile)

    def start(self):
        """Start recording with a delay after."""
        super().start()
        time.sleep(0.08)

    def stop(self):
        """Stop recording with a delay before."""
        time.sleep(0.08)
        super().stop()
        super().wait()

class SoapySDR():
    """TODO To implement."""

    def __init__(self):
        super().__init__()
        raise NotImplementedError
