#!/usr/bin/python3

from os import path
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

DIR = None

@click.group(context_settings={'show_default': True})
@click.option("--dir", type=click.Path(), default="/tmp", help="Temporary directory used to hold raw recording.")
def cli(dir):
    """Signal recording utility."""
    global DIR
    DIR = path.expanduser(dir)

@cli.command()
@click.argument("bd_addr")
@click.argument("freq_nf", type=int)
@click.argument("freq_ff", type=int)
@click.argument("samp_rate", type=int)
@click.option("--duration", type=float, default=0.5, help="Duration of the recording.")
@click.option("--radio/--no-radio", default=True, help="Enable or disable the radio recording (allows instrumentation only).")
@click.option("--nf-id", default=-1, help="Enable and associate radio index to near-field (NF) recording.")
@click.option("--ff-id", default=-1, help="Enable and associate radio index to far-field (FF) recording.")
def record(bd_addr, freq_nf, freq_ff, samp_rate, duration, radio, nf_id, ff_id):
    """Record RAW traces to DIR.

    BD_ADDR is the Bluetooth address of the target device to connect to.
    FREQ_NF is the center frequency for the near-field recording.
    FREQ_FF is the center frequency for the far-field recording.
    SAMP_RATE is the sampling rate used for both recording.

    Trigger the target device and store the RAW recording of the communication
    in DIR.

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

    rad = soapysdr.MySoapySDRs()
    if nf_id != -1:
        rad_nf = soapysdr.MySoapySDR(samp_rate, freq_nf, nf_id, radio)
        rad.register(rad_nf)
    if ff_id != -1:
        rad_ff = soapysdr.MySoapySDR(samp_rate, freq_ff, ff_id, radio)
        rad.register(rad_ff)
    if rad.get_nb() <= 0:
        l.LOGGER.error("we need at least one radio index to record!")
        exit(1)
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

    rad.save(DIR)
    rad.close()

@cli.command()
@click.argument("samp_rate", type=int)
@click.argument("id_ref", type=int)
@click.option("--plot/--no-plot", default=True, help="Plot a summary of the processing.")
@click.option("--overwrite/--no-overwrite", default=False, help="Overwrite the original RAW traces with extracted window.")
@click.option("--window", type=float, default=0.1, help="Extracted window in seconds, automatically compute if nothing specified.")
@click.option("--offset", type=float, default=0, help="Offset applied to extracted window in seconds.")
@click.option("--id", type=int, multiple=True, help="Radio indexes on which apply trace extraction (in addition to ID_REF). Can be specified multiple time.")
def extract(samp_rate, id_ref, plot, overwrite, window, offset, id):
    """Extract RAW traces from DIR.

    Extract a rough window around interesting signals from just-recorded RAW
    traces. It uses one raw trace as reference to find the interesting signal
    and extract the rough window for all specified raw traces.

    SAMP_RATE is the sampling rate used for both recording.
    ID_REF is the radio index to use for extraction reference.

    """
    # * Trigger(s) configuration.
    trg_bp_low          = [4e6]
    trg_bp_high         = [4.9e6]
    trg_lp              = 1e3
    trg_peak_prominence = 3/4
    l.LOGGER.debug("peak search prominence={}".format(trg_peak_prominence))

    # * Loading.
    sig_raw_ref = analyze.normalize(analyze.get_amplitude(load.load_raw_trace(DIR, id_ref, 0)))

    # * Triggering.
    assert(len(trg_bp_low) == len(trg_bp_high))
    TRG_NB = len(trg_bp_low)
    # ** Trigger signals.
    nf_triggers = triggers.Triggers()
    for idx in list(range(TRG_NB)):
        nf_triggers.add(triggers.Trigger(sig_raw_ref, trg_bp_low[idx], trg_bp_high[idx], trg_lp, samp_rate))
        l.LOGGER.debug(nf_triggers.get(idx))
    nf_triggers.reduce_add()
    # ** Trigger indexes.
    peaks = signal.find_peaks(nf_triggers.get(0).signal, distance=samp_rate/10, prominence=trg_peak_prominence)
    l.LOGGER.info("number of detected peaks={}".format(len(peaks[0])))

    # * Results.
    if plot:
        libplot.plot_time_spec_sync_axis([sig_raw_ref], samp_rate=samp_rate, peaks=peaks[0], triggers=nf_triggers)
    if len(peaks[0]) != 1:
        l.LOGGER.error("signal locating confusion: multiple peaks detected")
        # TODO: Don't exit but set a bad trace instead.
        exit(1)
    else:
        l.LOGGER.info("peak position={:.2f}%".format((peaks[0][0] / len(sig_raw_ref)) * 100))

    # * Extraction.
    if overwrite:
        peak = peaks[0][0]
        id = tuple(set(id + (id_ref,))) # Add id_ref and only get unique values of radio indexes.
        for idx in id:
            sig_raw = load.load_raw_trace(DIR, idx, 0)
            sig_raw = analyze.extract_time_window(sig_raw, samp_rate, peak, window, offset=offset)
            l.LOGGER.info("overwrite extracted signal #{} in {}".format(idx, DIR))
            load.save_raw_trace(sig_raw, DIR, idx, 0)
    else:
        l.LOGGER.info("ignore overwrite for extracted signal(s)")

@cli.command()
@click.argument("samp_rate", type=int)
@click.option("--amplitude/--no-amplitude", default=False, help="Get the amplitude of the traces.")
@click.option("--phase/--no-phase", default=False, help="Get the phase of the traces.")
@click.option("--nf-id", default=-1, help="Enable and associate radio index to near-field (NF) recording.")
@click.option("--ff-id", default=-1, help="Enable and associate radio index to far-field (FF) recording.")
def plot(samp_rate, amplitude, phase, nf_id, ff_id):
    """Plot RAW traces from DIR.

    SAMP_RATE is the sampling rate used for both recording.

    """
    s_arr = []
    nf_arr = None
    ff_arr = None
    # Load the traces and quit with an error if nothing is choosen.
    if nf_id != -1:
        nf_arr = load.load_raw_trace(DIR, nf_id, 0)
        s_arr.append(nf_arr)
    if ff_id != -1:
        ff_arr = load.load_raw_trace(DIR, ff_id, 0)
        s_arr.append(ff_arr)
    if nf_arr is None and ff_arr is None:
        l.LOGGER.error("we need at least one trace index to plot!")
        exit(1)
    # Truncate the traces to the exact size for plotting using synchronized axis.
    load.truncate_min(s_arr)
    # Get only one component of the IQ if needed.
    component_func = analyze.get_amplitude if amplitude else None
    component_func = analyze.get_phase if phase else component_func
    if component_func is not None:
        s_arr = component_func(s_arr)
    # Plot the result.
    libplot.plot_time_spec_sync_axis(s_arr, samp_rate)

if __name__ == "__main__":
    cli()
