#!/usr/bin/python3

# XXX: Information lost between subset for several processing.
# 
# When using two different processing commands, e.g. average for training
# subset and extralign for attack subset, then we lost information stored
# during the processing of the first subset, like the template and the bad
# entries.

import os
from os import path
import numpy as np
from matplotlib import pyplot as plt
from scipy import signal
import click

import lib.plot as libplot
import lib.utils as utils
import lib.debug as libdebug
import lib.analyze as analyze
import lib.load as load
import lib.device as device
import lib.log as l
import lib.filters as filters
import lib.triggers as triggers
import lib.dataset as dataset

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
              help="Generate plaintexts and keys at initialization instead of runtime.")
@click.option("--input-gen-run/--no-input-gen-run", default=False,
              help="Generate plaintexts and keys at runtime instead of initialization time.")
@click.option("--input-src-serial/--no-input-src-serial", default=False,
              help="Generate plaintexts and keys by reading them on the serial port.")
@click.option("--input-src-pairing/--no-input-src-pairing", default=False,
              help="Generate plaintexts and keys by performing a pairing.")
@click.option("--nb-trace-wanted-train", default=0, help="Number of wanted traces for train subset.")
@click.option("--nb-trace-wanted-attack", default=0, help="Number of wanted traces for attack subset.")
def init(outdir, samp_rate, force, input_gen_init, input_gen_run, input_src_serial, input_src_pairing, nb_trace_wanted_train, nb_trace_wanted_attack):
    """Initialize a dataset.

    Initialize a dataset in OUTDIR following given options.

    SAMP_RATE is the sampling rate used for both recording.

    """
    def input_conf():
        """Configurure the input generation. Return a tuple of
        dataset.InputGeneration and dataset.InputSource. Internally use
        variables of outer function with user switches.

        """
        input_gen, input_src = None, None
        # Determine user-choice of input generation method.
        if input_gen_init is True:
            input_gen = dataset.InputGeneration.INIT_TIME
        elif input_gen_run is True:
            input_gen = dataset.InputGeneration.RUN_TIME
        else:
            l.log_n_exit("Please, choose an input generation method!", 1)
        # Determine user-choice of input source method.
        if input_src_serial is True:
            input_src = dataset.InputSource.SERIAL
        elif input_src_pairing is True:
            input_src = dataset.InputSource.PAIRING
        # Sanity-check of input generation and input source.
        if input_gen == dataset.InputGeneration.INIT_TIME and input_src != None:
            l.LOGGER.warning("The input source will be ignored since input is generated at initialization time!")
        elif input_gen == dataset.InputGeneration.RUN_TIME and input_src == None:
            l.log_n_exit("Please, choose an input source method!", 1)
        return input_gen, input_src

    if path.exists(outdir):
        dset_path = dataset.Dataset.get_path_static(outdir)
        if not path.exists(dset_path) or force is True:
            dset = dataset.Dataset("tmp", outdir, samp_rate)
            # Input generation configurationg.
            input_gen, input_src = input_conf()
            # Create the subset.
            dset.add_subset("train", dataset.SubsetType.TRAIN, input_gen, input_src, nb_trace_wanted=nb_trace_wanted_train)
            dset.add_subset("attack", dataset.SubsetType.ATTACK, input_gen, input_src, nb_trace_wanted=nb_trace_wanted_attack)
            # Save the dataset.
            dset.pickle_dump(force=True, log=True)
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

@cli.command()
@click.argument("indir", type=click.Path())
@click.option("--subset", type=str, default="train", help="If specified, set the debugged subset.")
@click.option("--outdir", type=click.Path(), default=None, help="If specified, set the outdir/savedir of the dataset.")
def debug(indir, subset, outdir):
    """Debug a dataset.

    INDIR is the path of a directory containing a dataset.

    """
    # Handy variables for debugging.
    dproc = dataset.DatasetProcessing(indir, subset, outdir)
    dset = dproc.dset
    sset = dproc.dset.get_subset(subset)
    prof = dproc.dset.profile
    # * Scratchpad:
    print(dproc)
    from IPython import embed; embed()

@cli.command()
@click.argument("indir", type=click.Path())
def debug_profile(indir):
    """Debug a profile.

    INDIR is the path of a directory containing a profile.

    """
    prof = dataset.Profile(fp=indir)
    prof.load()
    print(prof)
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
@click.option("--jobs", default=0, help="Number of workers for processing parallelization [0 = single process ; -1 = maximum].")
def average(indir, outdir, subset, nb_aes, plot, template, stop, force, jobs):
    """Average multiple AES executions.

    INDIR corresponds to a directory containing a dataset with traces
    containing multiple AES. For each trace, the program will search every AES
    computation and will construct a new dataset by averaging them.

    OUTDIR corresponds to the directory where the new dataset will be stored.

    SUBSET corresponds to the subset's name that will be proceed.

    """
    # * Load input dataset and selected subset.
    dproc = dataset.DatasetProcessing(indir, subset, outdir=outdir, stop=stop)
    # * Resume from previously saved dataset.
    dproc.resume(from_zero=force)
    # * Define and run the processing.
    dproc.create("Average", analyze.average_aes_dproc, libplot.PlotOnce(default=plot), (nb_aes, template), nb=jobs)
    dproc.process()
    # * Save the resulting dataset.
    dproc.sset.prune_input(save=True)
    dproc.dset.pickle_dump()

@cli.command()
@click.argument("indir", type=click.Path())
@click.argument("outdir", type=click.Path())
@click.argument("subset", type=str)
@click.option("--nb-aes", default=1, help="Number of AES in the trace.")
@click.option("--plot/--no-plot", default=True, help="Plot a summary of the processing.")
@click.option("--template", default=-1, help="Specify template signal index to use. -1 means prompting.")
@click.option("--stop", default=1, help="Range of traces to process in the subset of the dataset. Set to -1 for maximum.")
@click.option("--force/--no-force", default=False, help="Force a restart of the processing even if resuming is detected.")
@click.option("--jobs", default=0, help="Number of workers for processing parallelization [0 = single process ; -1 = maximum].")
@click.option("--idx", default=0, help="Index of the AES to extract from the trace.")
@click.option("--window", default=0, help="Sample window extracted around the detected AES.")
def extract(indir, outdir, subset, nb_aes, plot, template, stop, force, jobs, idx, window):
    """Extract an aligned AES.

    INDIR corresponds to a directory containing a dataset with traces
    containing multiple AES. For each trace, the program will extract the
    desired AES computation and will align it with a template.

    OUTDIR corresponds to the directory where the new dataset will be stored.

    SUBSET corresponds to the subset's name that will be proceed.

    """
    # NOTE: If modifying this function, it is possible to also need to modify
    # average().
    # * Load input dataset and selected subset.
    dproc = dataset.DatasetProcessing(indir, subset, outdir=outdir, stop=stop)
    # * Resume from previously saved dataset.
    dproc.resume(from_zero=force)
    # * Define and run the processing.
    dproc.create("Extract", analyze.extract_aes_dproc, libplot.PlotOnce(default=plot), (nb_aes, template, idx, window), nb=jobs)
    dproc.process()
    # * Save the resulting dataset.
    dproc.sset.prune_input(save=True)
    dproc.dset.pickle_dump()
    
if __name__ == "__main__":
    cli()

# * Deprectated

# XXX: Started to implement the following function but finally, I'll try
# another approach.
# @cli.command()
# @click.argument("indir", type=click.Path())
# def register_profile(indir):
#     """Register the on-disk profile inside a dataset.

#     INDIR is the path of a directory containing a dataset.

#     """
#     # Handy variables for debugging.
#     dset = dataset.Dataset.pickle_load(indir, quit_on_error=True)
#     from IPython import embed; embed()
#     # XXX: To implement.

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
