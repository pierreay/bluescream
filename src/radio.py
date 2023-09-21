#!/usr/bin/python3

import numpy as np
from matplotlib import pyplot as plt
from scipy import signal
import click

import lib.debug
import lib.analyze as analyze
import lib.load as load
import lib.device as device
import lib.log as l
import lib.plot as libplot
import lib.filters as filters
import lib.triggers as triggers
import lib.soapysdr as soapysdr

@click.group(context_settings={'show_default': True})
def cli():
    """Signal recording utility."""
    pass

@cli.command()
@click.argument("bd_addr")
@click.argument("freq_nf", type=int)
@click.argument("freq_ff", type=int)
@click.argument("samp_rate", type=int)
@click.option("--duration", type=float, default=0.5, help="Duration of the recording.")
@click.option("--radio/--no-radio", default=True, help="Enable or disable the radio recording.")
def record(bd_addr, freq_nf, freq_ff, samp_rate, duration, radio):
    """Record RAW traces to /tmp.

    BD_ADDR is the Bluetooth address of the target device to connect to.
    FREQ_NF is the center frequency for the near-field recording.
    FREQ_FF is the center frequency for the far-field recording.
    SAMP_RATE is the sampling rate used for both recording.

    Trigger the target device and store the RAW recording of the communication
    in /tmp.

    """
    ret_exit_and_resume = 3
    num_points = 1
    num_traces_per_point = 1
    outpath = "/tmp"

    device_config = {"type": "NRF52_WHAD",
                     "fixed_plaintext": False,
                     "ltk_path": "/tmp/mirage_output_ltk",
                     "addr_path": "/tmp/mirage_output_addr",
                     "rand_path": "/tmp/mirage_output_rand",
                     "ediv_path": "/tmp/mirage_output_ediv",
                     "record_duration": duration
                     }

    rad1 = soapysdr.MySoapySDR(samp_rate, freq_nf, load.REC_RAW_NF_IDX, radio)
    rad2 = soapysdr.MySoapySDR(samp_rate, freq_ff, load.REC_RAW_FF_IDX, radio)
    rad = soapysdr.MySoapySDRs()
    rad.register(rad1)
    rad.register(rad2)
    rad.open()

    with device.Device.create(device_config, baud=115200, ser=bd_addr) as dev:
        dev.generate(num=num_points, path=outpath)
        dev.init(rep=num_traces_per_point)
        dev.radio = rad

        for idx in list(range(num_points)):
            dev.configure(idx)
            try:
                dev.execute()
            except OSError as e:
                l.log_n_exit(e, e.strerror, ret_exit_and_resume, traceback=True)
            dev.reset()

    rad.save(outpath)
    rad.close()

@cli.command()
@click.argument("samp_rate", type=int)
@click.option("--plot/--no-plot", default=True, help="Plot a summary of the processing.")
@click.option("--overwrite/--no-overwrite", default=False, help="Overwrite the original RAW traces with extracted window.")
@click.option("--window", type=float, default=0.1, help="Extracted window in seconds, automatically compute if nothing specified.")
@click.option("--offset", type=float, default=0, help="Offset applied to extracted window in seconds.")
def extract(samp_rate, plot, overwrite, window, offset):
    """Extract RAW traces from /tmp.

    Extract a rough window around interesting signals from just-recorded RAW
    traces.

    SAMP_RATE is the sampling rate used for both recording.

    """
    # * Trigger(s) configuration.
    trg_bp_low          = [9.0e6, 4.5e6]
    trg_bp_high         = [9.4e6, 6.8e6]
    trg_lp              = 0.75e3
    trg_peak_prominence = 3/4
    l.LOGGER.debug("peak search prominence={}".format(trg_peak_prominence))

    # * Loading.
    nf = analyze.get_amplitude(load.load_raw_trace("/tmp", load.REC_RAW_NF_IDX, 0))
    nf = analyze.normalize(nf)

    # * Triggering.
    assert(len(trg_bp_low) == len(trg_bp_high))
    TRG_NB = len(trg_bp_low)
    # ** Trigger signals.
    nf_triggers = triggers.Triggers()
    for idx in list(range(TRG_NB)):
        nf_triggers.add(triggers.Trigger(nf, trg_bp_low[idx], trg_bp_high[idx], trg_lp, samp_rate))
        l.LOGGER.debug(nf_triggers.get(idx))
    nf_triggers.reduce_add()
    # ** Trigger indexes.
    peaks = signal.find_peaks(nf_triggers.get(0).signal, distance=samp_rate/10, prominence=trg_peak_prominence)
    l.LOGGER.info("number of detected peaks={}".format(len(peaks[0])))

    # * Results.
    if plot:
        libplot.plot_time_spec_share_nf_ff(nf, None, samp_rate, peaks[0], nf_triggers)
    if len(peaks[0]) != 1:
        l.LOGGER.error("signal locating confusion: multiple peaks detected")
        exit(1)
    else:
        l.LOGGER.info("peak position={:.2f}%".format((peaks[0][0] / len(nf)) * 100))

    # * Extraction.
    nf = load.load_raw_trace("/tmp", load.REC_RAW_NF_IDX, 0)
    ff = load.load_raw_trace("/tmp", load.REC_RAW_FF_IDX, 0)
    nf, ff = load.truncate_min(nf, ff)
    peak = peaks[0][0]
    bl = int(peak + (offset * samp_rate) - (window / 2) * samp_rate)
    bl = bl if bl > 0 else 0
    bh = int(peak + (offset * samp_rate) + (window / 2) * samp_rate)
    bh = bh if bh < len(nf) else len(nf)
    l.LOGGER.debug("window={}:{}".format(bl, bh))
    nf = nf[bl:bh]
    ff = ff[bl:bh]
    if overwrite:
        l.LOGGER.info("overwrite extracted signal in /tmp")
        load.save_raw_trace(nf, "/tmp", load.REC_RAW_NF_IDX, 0)
        load.save_raw_trace(ff, "/tmp", load.REC_RAW_FF_IDX, 0)
    else:
        l.LOGGER.debug("ignore extraction overwrite")

@cli.command()
@click.argument("samp_rate", type=int)
@click.option("--amplitude/--no-amplitude", default=False, help="Get the amplitude of the traces.")
@click.option("--phase/--no-phase", default=False, help="Get the phase of the traces.")
def plot(samp_rate, amplitude, phase):
    """Plot RAW traces from /tmp.

    SAMP_RATE is the sampling rate used for both recording.

    Idea: this function could be now turn into a debug function, just like
    dataset.py/debug.

    """
    nf = load.load_raw_trace("/tmp", load.REC_RAW_NF_IDX, 0)
    ff = load.load_raw_trace("/tmp", load.REC_RAW_FF_IDX, 0)
    load.print_trace_info(nf, samp_rate, "nf")
    load.print_trace_info(ff, samp_rate, "ff")
    nf, ff = load.truncate_min(nf, ff)
    if amplitude:
        nf = analyze.get_amplitude(nf)
        ff = analyze.get_amplitude(ff)
    elif phase:
        nf = analyze.get_phase(nf)
        ff = analyze.get_phase(ff)
    libplot.plot_time_spec_share_nf_ff(nf, ff, samp_rate)

if __name__ == "__main__":
    cli()
