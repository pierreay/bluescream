#!/usr/bin/python3

from os import path
import numpy as np
from matplotlib import pyplot as plt
from scipy import signal
import click

import lib.dataset as dataset
import lib.debug
import lib.analyze as analyze
import lib.load as load
import lib.device as device
import lib.log as l
import lib.plot as libplot
import lib.filters as filters
import lib.triggers as triggers
import lib.soapysdr as soapysdr
import lib.complex as complex

def exit_on_cond(cond, ret=1):
    if cond is True:
        exit(ret)

DIR = None

@click.group(context_settings={'show_default': True})
@click.option("--dir", type=click.Path(), default="/tmp", help="Temporary directory used to hold raw recording.")
@click.option("--log/--no-log", default=True, help="Enable or disable logging.")
@click.option("--loglevel", default="DEBUG", help="Set the logging level.")
def cli(dir, log, loglevel):
    """Signal recording utility."""
    global DIR
    l.configure(log, loglevel)
    DIR = path.expanduser(dir)

@cli.command()
@click.argument("freq_nf", type=int)
@click.argument("freq_ff", type=int)
@click.argument("samp_rate", type=int)
@click.option("--duration", type=float, default=0.5, help="Duration of the recording.")
@click.option("--nf-id", default=-1, help="Enable and associate radio index to near-field (NF) recording.")
@click.option("--ff-id", default=-1, help="Enable and associate radio index to far-field (FF) recording.")
def listen(freq_nf, freq_ff, samp_rate, duration, nf_id, ff_id):
    """Initialize the radio and listen for commands.
    
    This commands will put our radio module in server mode, where the radio is
    listening for commands from another process through a pipe to perform
    recordings. This process will not go in background automatically, hence,
    use Bash to launch it in the background.

    """
    # Initialize the radio as requested.
    with soapysdr.MySoapySDRs() as rad:
        # Initialize the radios individually.
        try:
            if nf_id != -1:
                rad_nf = soapysdr.MySoapySDR(samp_rate, freq_nf, nf_id, duration=duration, dir=DIR)
                rad.register(rad_nf)
            if ff_id != -1:
                rad_ff = soapysdr.MySoapySDR(samp_rate, freq_ff, ff_id, duration=duration, dir=DIR)
                rad.register(rad_ff)
        except Exception as e:
            l.log_n_exit("Error during radio initialization", 1, e)
        if rad.get_nb() <= 0:
            l.LOGGER.error("we need at least one radio index to record!")
            exit(1)
        # Initialize the driver
        rad.open()
        # Listen for commands from another process.
        rad.listen()

@cli.command()
def quit():
    """Send a quit message to the listening radio server.

    This command is used to properly quit the radio server instead of killing
    it, possibly letting the SDR driver in a bad state.

    """
    soapysdr.MySoapySDRsClient().quit()

@cli.command()
@click.argument("indir", type=click.Path())
@click.argument("subset", type=str)
@click.argument("bd_addr_src")
@click.argument("bd_addr_dest")
@click.argument("ser_port")
@click.option("--radio/--no-radio", default=True, help="Enable or disable the radio recording (instrument only).")
@click.option("--idx", default=0, help="Current recording index to get correct dataset's inputs.")
def instrument(indir, subset, bd_addr_src, bd_addr_dest, ser_port, radio, idx):
    """Instrument the device and record RAW traces to DIR.

    INDIR is the path to the dataset. It is used for collection parameters
    (e.g. sample rate) and input values (e.g. key and plaintext).
    SUBSET corresponds to the subset's name where the inputs comes from.
    BD_ADDR_SRC the Bluetooth address of the spoofed legitimate device.
    BD_ADDR_DEST is the Bluetooth address of the target device to connect to.
    SER_PORT is the serial port of the target device to connect to.

    Trigger the target device and store the RAW recording of the communication
    in DIR.

    """
    # Load the dataset.
    dset = dataset.Dataset.pickle_load(indir, quit_on_error=True)
    sset = dset.get_subset(subset)

    # Initialize the radio client.
    rad = soapysdr.MySoapySDRsClient(enabled=radio)

    # Initalize the device.
    with device.Device(ser_port=ser_port, baud=115200, bd_addr_src=bd_addr_src, bd_addr_dest=bd_addr_dest, radio=rad, dataset=dset, subset=sset) as dev:
        # Configure everything related to current trace index.
        dev.configure(idx)
        # Perform the instrumentation and the recording.
        try:
            dev.execute()
        except Exception as e:
            l.log_n_exit("error during whad instrumentation", 3, e, traceback=True)
    rad.save()
    # NOTE: Here we save the entire dataset, but it is only useful for saving
    # new inputs generated during run time when dset.sset.input_gen ==
    # InputGeneration.RUN_TIME.
    dset.pickle_dump(force=True)

@cli.command()
@click.argument("samp_rate", type=int)
@click.argument("id_ref", type=int)
@click.option("--plot/--no-plot", default=True, help="Plot a summary of the processing.")
@click.option("--overwrite/--no-overwrite", default=False, help="Overwrite the original RAW traces with extracted window.")
@click.option("--window", type=float, default=0.1, help="Extracted window in seconds, automatically compute if nothing specified.")
@click.option("--offset", type=float, default=0, help="Offset applied to extracted window in seconds.")
@click.option("--id", type=int, multiple=True, help="Radio indexes on which apply trace extraction (in addition to ID_REF). Can be specified multiple time.")
@click.option("--exit-on-error/--no-exit-on-error", default=False, help="If true, exit with error on bad AES detection instead of saving a bad trace.")
def extract(samp_rate, id_ref, plot, overwrite, window, offset, id, exit_on_error):
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
    sig_raw_ref = analyze.normalize(complex.get_amplitude(load.load_raw_trace(DIR, id_ref, 0)))

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
    peaks = peaks[0]
    l.LOGGER.info("number of detected peaks={}".format(len(peaks)))

    # * Results.
    libplot.plot_time_spec_sync_axis([sig_raw_ref], samp_rate=samp_rate, peaks=peaks, triggers=nf_triggers, cond=plot)
    libplot.plot_time_spec_sync_axis([analyze.extract_time_window(sig_raw_ref, samp_rate, peaks[0], window, offset=offset)], samp_rate=samp_rate, cond=plot)    
    peak_detect_ok = len(peaks) == 1
    if peak_detect_ok is False:
        l.LOGGER.error("signal locating confusion: no or multiple peaks detected")
        exit_on_cond(exit_on_error)
    else:
        peak_position = (peaks[0] / len(sig_raw_ref)) * 100
        l.LOGGER.info("peak position={:.2f}%".format(peak_position))
        if peak_position < 25 or peak_position > 75:
            l.LOGGER.warning("maybe increase recording time to center the aes on the recording")

    # * Extraction.
    if overwrite:
        id = tuple(set(id + (id_ref,))) # Add id_ref and only get unique values of radio indexes.
        for idx in id:
            sig_raw = load.load_raw_trace(DIR, idx, 0)
            if peak_detect_ok is False:
                l.LOGGER.warning("replace recording by a bad trace")
                sig_raw = analyze.get_bad_trace(sig_raw)
                # Extract at middle of trace.
                peak = int(len(sig_raw) / 2)
            else:
                peak = peaks[0]
            sig_raw = analyze.extract_time_window(sig_raw, samp_rate, peak, window, offset=offset)
            l.LOGGER.info("overwrite extracted signal #{} in {}".format(idx, DIR))
            load.save_raw_trace(sig_raw, DIR, idx, 0)
    else:
        l.LOGGER.info("ignore overwrite for extracted signal(s)")

@cli.command()
@click.argument("samp_rate", type=int)
@click.option("--amplitude/--no-amplitude", default=True, help="Plot the amplitude of the traces.")
@click.option("--phase/--no-phase", default=False, help="Plot the phase of the traces.")
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
        nf_arr = load.load_raw_trace(DIR, nf_id, 0, log=True)
        s_arr.append(nf_arr)
    if ff_id != -1:
        ff_arr = load.load_raw_trace(DIR, ff_id, 0, log=True)
        s_arr.append(ff_arr)
    if nf_arr is None and ff_arr is None:
        l.LOGGER.error("we need at least one trace index to plot!")
        exit(1)
    # Truncate the traces to the exact size for plotting using synchronized axis.
    s_arr = np.asarray(load.truncate_min(s_arr))
    # Plot the result.
    if amplitude is True:
        libplot.plot_time_spec_sync_axis(s_arr, samp_rate, comp=complex.CompType.AMPLITUDE)
    if phase is True:
        libplot.plot_time_spec_sync_axis(s_arr, samp_rate, comp=complex.CompType.PHASE)

if __name__ == "__main__":
    cli()
