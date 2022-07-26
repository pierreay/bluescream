"""Allows multiple SDR to be used for recording Screaming Channels leaks.

Global variables:

        Radio: Enumeration of all supported SDRs.

Classes:

        GNUradio: Configure a GNURadio capture.

"""
# Core modules.
import enum

# External modules.
from gnuradio import blocks, gr, uhd, iio
import osmosdr

Radio = enum.Enum("Radio", "USRP USRP_mini USRP_B210 USRP_B210_MIMO HackRF bladeRF PlutoSDR")

class GNUradio(gr.top_block):
    """GNUradio capture from SDR to file."""
    def __init__(self, outfile, radio, address, antenna, frequency=2.464e9, sampling_rate=5e6,
                 usrp_gain=40, hackrf_gain=0, hackrf_gain_if=40, hackrf_gain_bb=44, plutosdr_gain=35):
        gr.top_block.__init__(self, "Top Block")

        self.outfile = outfile
        self.radio = radio
        self.address = address
        self.antenna = antenna

        if self.radio in (Radio.USRP, Radio.USRP_mini, Radio.USRP_B210):
            radio_block = uhd.usrp_source(
                ("addr=" + self.address.encode("ascii"))
                if self.radio == Radio.USRP else "",
                uhd.stream_args(cpu_format="fc32", channels=[0]))
            radio_block.set_center_freq(frequency)
            radio_block.set_samp_rate(sampling_rate)
            radio_block.set_gain(usrp_gain)
            radio_block.set_antenna(self.antenna.encode("ascii"))
        elif self.radio == Radio.USRP_B210_MIMO:
            radio_block = uhd.usrp_source(
        	",".join(('', "")),
        	uhd.stream_args(
        		cpu_format="fc32",
        		channels=range(2),
        	),
            )
            radio_block.set_samp_rate(sampling_rate)
            radio_block.set_center_freq(frequency, 0)
            radio_block.set_gain(usrp_gain, 0)
            radio_block.set_antenna('RX2', 0)
            radio_block.set_bandwidth(sampling_rate/2, 0)
            radio_block.set_center_freq(frequency, 1)
            radio_block.set_gain(usrp_gain, 1)
            radio_block.set_antenna('RX2', 1)
            radio_block.set_bandwidth(sampling_rate/2, 1)
 
        elif self.radio == Radio.HackRF or self.radio == Radio.bladeRF:
            mysdr = str(self.radio).split(".")[1].lower() #get "bladerf" or "hackrf"
            radio_block = osmosdr.source(args="numchan=1 "+mysdr+"=0")
            radio_block.set_center_freq(frequency, 0)
            radio_block.set_sample_rate(sampling_rate)
            # TODO tune parameters
            radio_block.set_freq_corr(0, 0)
            radio_block.set_dc_offset_mode(True, 0)
            radio_block.set_iq_balance_mode(True, 0)
            radio_block.set_gain_mode(True, 0)
            radio_block.set_gain(hackrf_gain, 0)
            radio_block.set_if_gain(hackrf_gain_if, 0)
            radio_block.set_bb_gain(hackrf_gain_bb, 0)
            radio_block.set_antenna('', 0)
            radio_block.set_bandwidth(3e6, 0)
            
        elif self.radio == Radio.PlutoSDR:
            bandwidth = 3e6
            radio_block = iio.pluto_source(self.address.encode("ascii"),
                                           int(frequency), int(sampling_rate),
                                           1 - 1, int(bandwidth), 0x8000, True,
                                           True, True, "manual", plutosdr_gain,
                                           '', True)
        else:
            raise Exception("Radio type %s is not supported" % self.radio)


        self._file_sink = blocks.file_sink(gr.sizeof_gr_complex, self.outfile)
        self.connect((radio_block, 0), (self._file_sink, 0))

        if self.radio == Radio.USRP_B210_MIMO:
            self._file_sink_2 = blocks.file_sink(gr.sizeof_gr_complex,
            self.outfile+"_2")
            self.connect((radio_block, 1), (self._file_sink_2, 0))


    def reset_trace(self):
        """
        Remove the current trace file and get ready for a new trace.
        """
        self._file_sink.open(self.outfile)
        
        if self.radio == Radio.USRP_B210_MIMO:
            self._file_sink_2.open(self.outfile+"_2")

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()
