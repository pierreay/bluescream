#!/usr/bin/python3

from os import path
import numpy as np
from matplotlib import pyplot as plt
from scipy import signal
import click
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm

import lib.debug as libdebug
import lib.analyze as analyze
import lib.load as load
import lib.device as device
import lib.log as l
import lib.plot as libplot
import lib.filters as filters
import lib.triggers as triggers
import lib.dataset as dataset

def load_dataset_or_quit(indir, subset, outdir=None):
    dset = dataset.Dataset.pickle_load(indir)
    if dset is None:
        l.LOGGER.error("dataset doesn't exists!")
        exit(-1)
    if outdir is not None:
        dset.set_dirsave(outdir)
    dset.dirty = True
    return dset, dset.get_subset(subset)

def save_dataset_and_quit(dset):
    # Disable setting dirty to False, otherwise, after a completeed averaging,
    # we are not able to extend a previous averaging.
    # dset.dirty = False
    dset.pickle_dump()
    exit(0)

@click.group(context_settings={'show_default': True})
def cli():
    """Dataset processing utility."""
    pass

@cli.command()
@click.argument("outdir", type=click.Path())
@click.argument("samp_rate", type=int)
@click.option("--input-gen-init/--no-input-gen-init", default=False,
              help="Generate plaintexts and keys at initialization instead of real-time.")
@click.option("--nb-trace-wanted-train", default=0, help="Number of wanted traces for train subset.")
@click.option("--nb-trace-wanted-attack", default=0, help="Number of wanted traces for attack subset.")
def init(outdir, samp_rate, input_gen_init, nb_trace_wanted_train, nb_trace_wanted_attack):
    """Initialize a dataset.

    Initialize a dataset in OUTDIR following given options.

    SAMP_RATE is the sampling rate used for both recording.

    """
    if path.exists(outdir):
        dset = dataset.Dataset("tmp", outdir, samp_rate)
        input_gen = dataset.InputGeneration.INIT_TIME if input_gen_init else dataset.InputGeneration.REAL_TIME
        dset.add_subset("train", dataset.SubsetType.TRAIN, input_gen, nb_trace_wanted=nb_trace_wanted_train)
        dset.add_subset("attack", dataset.SubsetType.ATTACK, input_gen, nb_trace_wanted=nb_trace_wanted_attack)
        dset.pickle_dump(force=True)
        l.LOGGER.info("save dataset in {}".format(dset.get_path(save=True)))
    else:
        l.LOGGER.error("{} doesn't exists!".format(indir))
        return 1

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
@click.option("--outdir", type=click.Path(), default=None, help="If specified, set the outdir/savedir of the dataset.")
def debug(indir, outdir):
    """Debug a dataset.

    INDIR is the path of a directory containing a dataset.

    """
    dset, sset = load_dataset_or_quit(indir, "train", outdir)
    # * Scratchpad:
    import ipdb; ipdb.set_trace()
    print(dset)

@cli.command()
@click.argument("indir", type=click.Path())
@click.argument("outdir", type=click.Path())
@click.argument("subset", type=str)
@click.option("--nb-aes", default=1, help="Number of AES in the trace.")
@click.option("--plot/--no-plot", default=True, help="Plot a summary of the processing.")
@click.option("--template", default=-1, help="Specify template signal index to use. -1 means prompting.")
@click.option("--stop", default=1, help="Range of traces to process in the subset of the dataset. Set to -1 for maximum.")
def average(indir, outdir, subset, nb_aes, plot, template, stop):
    """Average multiple AES executions.

    INDIR corresponds to a directory containing a dataset with traces
    containing multiple AES. For each trace, the program will search every AES
    computation and will construct a new dataset by averaging them.

    OUTDIR corresponds to the directory where the new dataset will be stored.

    SUBSET corresponds to the subset's name that will be proceed.


    """
    start = 0
    # * Load input dataset and selected subset.
    dset, sset = load_dataset_or_quit(indir, subset, outdir=outdir)
    # * Fetch template from previously saved dataset in case of resuming.
    if dset.get_savedir_dirty():
        dset.resume_from_savedir(subset)
        start = dset.dirty_idx
        l.LOGGER.info("resume at trace {} using template from previous processing".format(start))
        l.LOGGER.debug("template shape={}".format(sset.template.shape))
    # Load traces one by one since traces containing multiple AES executions
    # can be large (> 30 MB).
    with logging_redirect_tqdm(loggers=[l.LOGGER]):
        if stop == -1:
            stop = sset.get_nb_trace_ondisk()
        for i in tqdm(range(start, stop), desc="average"):
            dset.dirty_idx = i
            sset.load_trace(i)
            assert(sset.ff is not None)
            sset.ff, sset.template = analyze.average_aes(sset.ff, dset.samp_rate, nb_aes, template if sset.template is None else sset.template, plot)
            check, sset.ff = analyze.fill_zeros_if_bad(sset.template, sset.ff)
            if check is True:
                l.LOGGER.warning("error during averaging aes, trace {} filled with zeroes!".format(i))
                sset.bad_entries.append(i)
            if plot:
                libplot.plot_time_spec_share_nf_ff(sset.ff, None, dset.samp_rate)
            sset.save_trace(nf=False)
            dset.pickle_dump(unload=False)
    sset.prune_input(save=True)
    save_dataset_and_quit(dset)

if __name__ == "__main__":
    cli()
