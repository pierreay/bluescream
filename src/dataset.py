#!/usr/bin/python3

# FIXME: Information lost between subset for several processing.
# 
# When using two different processing commands, e.g. average for training
# subset and extralign for attack subset, then we lost information stored
# during the processing of the first subset, like the template and the bad
# entries.

from multiprocessing import Process, Queue
import os
from os import path
import numpy as np
from matplotlib import pyplot as plt
from scipy import signal
import click
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm

import lib.utils as utils
import lib.debug as libdebug
import lib.analyze as analyze
import lib.load as load
import lib.device as device
import lib.log as l
import lib.plot as libplot
import lib.filters as filters
import lib.triggers as triggers
import lib.dataset as dataset
import lib.complex as complex

@click.group(context_settings={'show_default': True})
@click.option("--log/--no-log", default=True, help="Enable or disable logging.")
@click.option("--loglevel", default="DEBUG", help="Set the logging level.")
def cli(log, loglevel):
    """Dataset processing utility."""
    l.configure(log, loglevel)

@cli.command()
@click.argument("outdir", type=click.Path())
@click.argument("samp_rate", type=int)
@click.option("--force/--no-force", default=False, help="Force an overwriting of an existing initialized dataset.")
@click.option("--input-gen-init/--no-input-gen-init", default=False,
              help="Generate plaintexts and keys at initialization instead of real-time.")
@click.option("--nb-trace-wanted-train", default=0, help="Number of wanted traces for train subset.")
@click.option("--nb-trace-wanted-attack", default=0, help="Number of wanted traces for attack subset.")
def init(outdir, samp_rate, force, input_gen_init, nb_trace_wanted_train, nb_trace_wanted_attack):
    """Initialize a dataset.

    Initialize a dataset in OUTDIR following given options.

    SAMP_RATE is the sampling rate used for both recording.

    """
    if path.exists(outdir):
        dset_path = dataset.Dataset.get_path_static(outdir)
        if not path.exists(dset_path) or force is True:
            dset = dataset.Dataset("tmp", outdir, samp_rate)
            input_gen = dataset.InputGeneration.INIT_TIME if input_gen_init else dataset.InputGeneration.REAL_TIME
            dset.add_subset("train", dataset.SubsetType.TRAIN, input_gen, nb_trace_wanted=nb_trace_wanted_train)
            dset.add_subset("attack", dataset.SubsetType.ATTACK, input_gen, nb_trace_wanted=nb_trace_wanted_attack)
            dset.pickle_dump(force=True)
            l.LOGGER.info("save dataset in {}".format(dset.get_path(save=True)))
        else:
            l.log_n_exit("{} already exists!".format(dset_path), 1)
    else:
        l.log_n_exit("{} doesn't exists!".format(outdir), 1)

@cli.command()
@click.argument("indir", type=click.Path())
@click.option("--train/--no-train", default=False, help="Interrogate the train set.")
@click.option("--attack/--no-attack", default=False, help="Interrogate the attack set.")
@click.option("--pt-gen-init/--no-pt-gen-init", default=False, help="Return 1 if plaintexts were generated at initialization.")
@click.option("--ks-gen-init/--no-ks-gen-init", default=False, help="Return 1 if kets were generated at initialization.")
def query(indir, train, attack, pt_gen_init, ks_gen_init):
    """Query dataset information.

    Query an information about a dataset. Mainly used for external scripts
    (e.g. bash). Return 1 for a True answer, 0 for a False answer, -1 for an
    error. Otherwise, print the response value on the standard output.

    """
    dset = dataset.Dataset.pickle_load(indir)
    if dset is None:
        l.LOGGER.error("dataset doesn't exists!")
        exit(-1)
    subset = None
    subset = dset.train_set if train and not attack else subset
    subset = dset.attack_set if attack and not train else subset
    if subset is None:
        l.LOGGER.error("please, select a subset!")
        exit(-1)
    if pt_gen_init:
        exit(subset.pt_gen == dataset.InputGeneration.INIT_TIME)
    if ks_gen_init:
        exit(subset.ks_gen == dataset.InputGeneration.INIT_TIME)

def average_fn(q, dset, sset, i, stop, nb_aes, template, plot):
    """Main function for processes used in the average command/function."""
    l.LOGGER.debug("start average_fn for trace #{}".format(i))
    # * If process start with trace out of bound, return.
    if i >= stop:
        q.put((None, None, i))
        return 0
    # * Load the trace to process.
    sset.load_trace(i, nf=False, ff=True, check=True)
    # * Get the average of all AES and the template.
    ff_avg, sset.template = analyze.average_aes(sset.ff[0], dset.samp_rate, nb_aes, template if sset.template is None else sset.template, plot_enable=plot)
    sset.replace_trace(ff_avg, dataset.TraceType.FF)
    # * Check the trace is valid. The trace #0 is assumed be valid.
    check = False
    if i > 0:
        check, ff_checked = analyze.fill_zeros_if_bad(sset.template, sset.ff[0], log=True, log_idx=i)
        sset.replace_trace(ff_checked, dataset.TraceType.FF)
    # * Plot the averaged trace if wanted and average succeed.
    if sset.ff[0] is not None:
        libplot.plot_time_spec_sync_axis(sset.ff[0:1], samp_rate=dset.samp_rate, cond=plot, comp=complex.CompType.AMPLITUDE)
    # * Save the processed trace.
    sset.save_trace(nf=False)
    q.put((sset.template, check, i))
    l.LOGGER.debug("end average_fn for trace #{}".format(i))

@cli.command()
@click.argument("indir", type=click.Path())
@click.option("--subset", type=str, default="train", help="If specified, set the debugged subset.")
@click.option("--outdir", type=click.Path(), default=None, help="If specified, set the outdir/savedir of the dataset.")
def debug(indir, subset, outdir):
    """Debug a dataset.

    INDIR is the path of a directory containing a dataset.

    """
    dproc = dataset.DatasetProcessing(indir, subset, outdir)
    # * Scratchpad:
    print(dproc)
    from IPython import embed; embed()

@cli.command()
@click.argument("indir", type=click.Path())
@click.argument("outdir", type=click.Path())
@click.argument("subset", type=str)
@click.option("--nb-aes", default=1, help="Number of AES in the trace.")
@click.option("--plot/--no-plot", default=True, help="Plot a summary of the processing.")
@click.option("--template", default=-1, help="Specify template signal index to use. -1 means prompting.")
@click.option("--stop", default=1, help="Range of traces to process in the subset of the dataset. Set to -1 for maximum.")
@click.option("--force/--no-force", default=False, help="Force a restart of the processing even if resuming is detected.")
def average(indir, outdir, subset, nb_aes, plot, template, stop, force):
    """Average multiple AES executions.

    INDIR corresponds to a directory containing a dataset with traces
    containing multiple AES. For each trace, the program will search every AES
    computation and will construct a new dataset by averaging them.

    OUTDIR corresponds to the directory where the new dataset will be stored.

    SUBSET corresponds to the subset's name that will be proceed.


    """
    start = 0
    # * Load input dataset and selected subset.
    dproc = dataset.DatasetProcessing(indir, subset=subset, outdir=outdir)
    dset = dproc.dset
    sset = dproc.sset
    # * Fetch template from previously saved dataset in case of resuming.
    if force is False and dset.get_savedir_dirty():
        dset.resume_from_savedir(subset)
        start = dset.dirty_idx
        l.LOGGER.info("resume at trace {} using template from previous processing".format(start))
        l.LOGGER.debug("template shape={}".format(sset.template.shape))
    if stop == -1:
        stop = sset.get_nb_trace_ondisk()
    # Load traces one by one since traces containing multiple AES executions
    # can be large (> 30 MB).
    with logging_redirect_tqdm(loggers=[l.LOGGER]):
        with tqdm(initial=start, total=stop, desc="average") as pbar:
            i = start
            while i < stop:
                # * Load trace and save current processing step in dataset.
                dset.dirty_idx = i

                # * Process start. First trace is always progressed sequentially.
                q = Queue()
                if i == 0:
                    average_fn(q, dset, sset, i, stop, nb_aes, template, plot)
                    sset.template, check, _ = q.get()
                    if check is True:
                        sset.bad_entries.append(i)
                    i = i + 1
                    pbar.update(1)
                else:
                    ps = [None] * (os.cpu_count() - 1)
                    for pidx in range(len(ps)):
                        ps[pidx] = Process(target=average_fn, args=(q, dset, sset, i + pidx, stop, nb_aes, template, plot,))
                    for pidx in range(len(ps)):
                        l.LOGGER.debug("start process pidx={}".format(pidx))
                        ps[pidx].start()
                    for pidx in range(len(ps)):
                        l.LOGGER.debug("get from process pidx={}".format(pidx))
                        _, check, pidx_get = q.get()
                        if check is True:
                            sset.bad_entries.append(i + pidx_get)
                    for pidx in range(len(ps)):
                        ps[pidx].join()
                        l.LOGGER.debug("end process pidx={}".format(pidx))
                    i = i + len(ps)
                    pbar.update(len(ps))

                # * Save dataset for resuming if not finishing the loop.
                dset.pickle_dump(unload=False, log=False)
                # * Disable plot for remainaing traces.
                plot = False
    dset.dirty_idx = stop # Can be less than stop because of "i = i + len(ps)".
    sset.prune_input(save=True)
    dset.pickle_dump()
    
if __name__ == "__main__":
    cli()

# * Deprectated

# @cli.command()
# @click.argument("indir", type=click.Path())
# @click.argument("outdir", type=click.Path())
# @click.argument("subset", type=str)
# @click.option("--plot/--no-plot", default=True, help="Plot AES finding and template validation.")
# @click.option("--offset", default=0, help="Number of samples to addition to the detected AES.")
# @click.option("--length", default=10000, help="Number of samples of the window to extract.")
# @click.option("--stop", default=1, help="Range of traces to process in the subset of the dataset. Set to -1 for maximum.")
# @click.option("--force/--no-force", default=False, help="Force a restart of the processing even if resuming is detected.")
# def extralign(indir, outdir, subset, plot, offset, length, stop, force):
#     """[DEPRECATED] Extract roughly the AES from RAW FF traces and align them.

#     INDIR corresponds to the input dataset directory.
#     OUTDIR corresponds to the output dataset directory.
#     SUBSET corresponds to the subset's name that will be proceed.

#     """
#     start = 0
#     # * Load input dataset and selected subset.
#     dset, sset = load_dataset_or_quit(indir, subset, outdir=outdir)
#     # * Resume from previously saved dataset if needed.
#     if force is False and dset.get_savedir_dirty():
#         dset.resume_from_savedir(subset)
#         start = dset.dirty_idx
#         l.LOGGER.info("resume at trace {} using template from previous processing".format(start))
#         l.LOGGER.debug("template shape={}".format(sset.template.shape))
#     if stop == -1:
#         stop = sset.get_nb_trace_ondisk()
#     with logging_redirect_tqdm(loggers=[l.LOGGER]):
#         for i in tqdm(range(start, stop), desc="extralign"):
#             # * Load trace and save current processing step in dataset.
#             dset.dirty_idx = i
#             sset.load_trace(i, nf=False, ff=True, check=True)
#             # * Find AES and check for error.
#             # XXX: I think the following line will not work since dtype are different... To test.
#             sset.ff[0] = complex.get_amplitude(sset.ff[0])
#             starts, trigger = analyze.find_aes(sset.ff[0], dset.samp_rate, 1e6, 10e6, 1, lp=1e5, offset=-1.5e-4, flip=False)
#             # XXX: Refactor all of the following insde the find_aes function?
#             if len(starts) == 1:
#                 l.LOGGER.debug("number of detected aes: {}".format(len(starts)))
#             else:
#                 l.LOGGER.error("number of detected aes is aberrant: {}".format(len(starts)))
#                 # If plot is ON, we are debugging/configuring or processing trace #1, hence don't continue.
#                 if plot:
#                     libplot.plot_time_spec_sync_axis(sset.ff[0:1], samp_rate=dset.samp_rate, peaks=starts, triggers=trigger)
#                     raise Exception("aes detection failed!")
#             if plot:
#                 libplot.plot_time_spec_sync_axis(sset.ff[0:1], samp_rate=dset.samp_rate, peaks=starts, triggers=trigger)
#             # * If trace 0, interactively valid the extraction as the template for further traces.
#             if i == 0:
#                 extracted     = analyze.extract(sset.ff[0], starts, length=length)
#                 sset.template = analyze.choose_signal(extracted, -1 if plot is True else 0)
#                 if sset.template is None:
#                     raise Exception("no choosen template signal")
#             # * Align current trace against the template.
#             if len(starts) == 1: # Only process if find_aes returned correctly, otherwise, set a bad trace.
#                 extracted = analyze.extract(sset.ff[0], starts, len(sset.template))
#                 aligned   = analyze.align(sset.template, extracted[0], dset.samp_rate, ignore=False, log=False)
#             else:
#                 aligned = None
#             # * Check the trace is valid. The trace #0 is assumed be valid.
#             check = False
#             # XXX: Is the trace #0 saved if we do not enter this block, since this block seems to save at the same time at checking?
#             if i > 0:
#                 check, sset.ff[0] = analyze.fill_zeros_if_bad(sset.template, aligned, log=True, log_idx=i)
#             if check is True:
#                 sset.bad_entries.append(i)
#             # * Save dataset for resuming if not finishing the loop.
#             sset.save_trace(nf=False)
#             dset.pickle_dump(unload=False, log=False)
#             # * Disable plot for remainaing traces.
#             plot = False
#     sset.prune_input(save=True)
#     save_dataset_and_quit(dset)
