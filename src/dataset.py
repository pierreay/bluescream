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

def load_dataset_or_quit(indir, subset=None, outdir=None):
    dset = dataset.Dataset.pickle_load(indir)
    sset = None
    if dset is None:
        l.LOGGER.error("dataset doesn't exists!")
        exit(-1)
    if outdir is not None:
        dset.set_dirsave(outdir)
    if subset is not None:
        sset = dset.get_subset(subset)
    dset.dirty = True
    return dset, sset

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

@cli.command()
@click.argument("indir", type=click.Path())
@click.argument("outdir", type=click.Path())
@click.argument("subset", type=str)
@click.option("--plot/--no-plot", default=True, help="Plot a summary of the processing.")
@click.option("--offset", default=0, help="Number of samples to addition to the detected AES.")
@click.option("--length", default=10000, help="Number of samples of the window to extract.")
@click.option("--stop", default=1, help="Range of traces to process in the subset of the dataset. Set to -1 for maximum.")
@click.option("--force/--no-force", default=False, help="Force a restart of the processing even if resuming is detected.")
def extralign(indir, outdir, subset, plot, offset, length, stop, force):
    """Extract roughly the AES from RAW FF traces and align them.

    INDIR corresponds to the input dataset directory.
    OUTDIR corresponds to the output dataset directory.
    SUBSET corresponds to the subset's name that will be proceed.

    """
    # SPECIFICIATIONS:
    # test for resuming template
    # resume from dirty idx
    # for each trace:
    #     load trace i
    #     extract aes
    #     if trace 0:
    #       interactively valid it as a template
    #     else:
    #       align against template
    #     save dataest    
    start = 0
    # * Load input dataset and selected subset.
    dset, sset = load_dataset_or_quit(indir, subset, outdir=outdir)
    # * Resume from previously saved dataset if needed.
    if force is False and dset.get_savedir_dirty():
        dset.resume_from_savedir(subset)
        start = dset.dirty_idx
        l.LOGGER.info("resume at trace {} using template from previous processing".format(start))
        l.LOGGER.debug("template shape={}".format(sset.template.shape))
    if stop == -1:
        stop = sset.get_nb_trace_ondisk()
    with logging_redirect_tqdm(loggers=[l.LOGGER]):
        for i in tqdm(range(start, stop), desc="extralign"):
            # * Load trace and save current processing step in dataset.
            dset.dirty_idx = i
            sset.load_trace(i, nf=False, ff=True, check=True)
            # * Extract the AES.
            # * If trace 0, interactively valid it as a template.
            # * Else, align it against the template.
            import ipdb; ipdb.set_trace()
            sset.ff, sset.template = analyze.extralign_aes(sset.ff, dset.samp_rate, sset.template, length, plot)
            # * Check the trace is valid.
            check, sset.ff = analyze.fill_zeros_if_bad(sset.template, sset.ff)
            if check is True:
                l.LOGGER.warning("error during averaging aes, trace {} filled with zeroes!".format(i))
                sset.bad_entries.append(i)
            # * Plot if needed for debugging or configuration.
            if plot:
                libplot.plot_time_spec_share_nf_ff(sset.ff, None, dset.samp_rate)
            # * Save dataset for resuming if not finishing the loop.
            sset.save_trace(nf=False)
            dset.pickle_dump(unload=False)
    sset.prune_input(save=True)
    save_dataset_and_quit(dset)
    
@cli.command()
@click.argument("indir", type=click.Path())
@click.argument("outdir", type=click.Path())
@click.option("--plot/--no-plot", default=True, help="Plot a summary of the processing.")
@click.option("--stop", default=1, help="Range of traces to process in the subset of the dataset. Set to -1 for maximum.")
def fitoprofile(indir, outdir, plot, stop):
    """TODO: Write a desc or delete command.

    Process dataset source attack subset and align them against dataset dest
    training subset.

    """
    start = 0
    dset_src, sset_src = load_dataset_or_quit(indir,  dataset.SubsetType.ATTACK, outdir=outdir)
    dset_dst, sset_dst = load_dataset_or_quit(outdir, dataset.SubsetType.TRAIN)
    # * Check prerequisites.
    assert(dset_src.attack_set.get_nb_trace_ondisk() > 1)
    assert(dset_dst.train_set.template is not None)
    assert(dset_dst.profile is not None)
    # Profile should be computed.
    # * Fetch template from previously saved dataset in case of resuming.
    # if dset.get_savedir_dirty():
    #     dset.resume_from_savedir(subset)
    #     start = dset.dirty_idx
    #     l.LOGGER.info("resume at trace {} using template from previous processing".format(start))
    #     l.LOGGER.debug("template shape={}".format(sset.template.shape))
    # * Search for 2nd round of AES' stop in template.
    nsamp_aes_template = 2000
    # if plot is True:
    #     libplot.plot_time_spec_share_nf_ff(dset_dst.train_set.template, None, dset_dst.samp_rate, peaks=[nsamp_aes_template]) # Check that nsamp_aes_template is correct.
    with logging_redirect_tqdm(loggers=[l.LOGGER]):
        if stop == -1:
            stop = sset_src.get_nb_trace_ondisk()
        for i in tqdm(range(start, stop), desc="fitoprofile"):
            # dset.dirty_idx = i
            # * Get working trace.
            sset_src.load_trace(i)
            assert(sset_src.ff is not None)
            ff = analyze.get_amplitude(sset_src.ff)
            #libplot.plot_spec_simple(ff)
            assert(ff.dtype == dset_dst.train_set.template.dtype)
            # * Cut working trace according to nsamp_aes_template.
            triggerl = triggers.Triggers()
            triggerl.add(triggers.Trigger(ff, 1e6, 13e6, 1e4, dset_src.samp_rate))
            trigger = triggerl.get(0).signal
            peaks = signal.find_peaks(trigger, distance=len(trigger) / 2, prominence=0.25)
            #libplot.plot_time_spec_share_nf_ff(ff, None, dset_dst.samp_rate, peaks=peaks[0], triggers=triggerl)
            end_of_aes = int(peaks[0][0])
            ff = ff[peaks[0][0] - nsamp_aes_template:peaks[0][0]]
            libplot.plot_simple(ff)
            # TODO: The idea from here was to use:
            # https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.peak_widths.html#scipy.signal.peak_widths
            # https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.peak_prominences.html
            # To find precesily where the AES stopped. Surely better way. But
            # move on bruteforce the alignement after manual selection in
            # attack.py
            continue
            starts, trigger = analyze.find_aes(ff, dset_src.samp_rate, 8.8e6, 9.5e6, 1, 1e4, -0.5e-4, flip=False, plot=False)
            template = dset_dst.train_set.template[0:2000]
            starts = starts
            # libplot.plot_time_spec_share_nf_ff(ff, None, dset_dst.samp_rate, peaks=[starts, starts + len(template)])
            extracted  = analyze.extract(ff, starts, len(template))
            # libplot.plot_simple(extracted)
            # libplot.plot_simple(dset_dst.train_set.template)
            
            aligned = analyze.align(template, extracted[0], dset_src.samp_rate, log=True)
            # libplot.plot_spec_simple([template, aligned])
            # check, sset.ff = analyze.fill_zeros_if_bad(sset.template, sset.ff)
            # if check is True:
            #     l.LOGGER.warning("error during averaging aes, trace {} filled with zeroes!".format(i))
            #     sset.bad_entries.append(i)
            # if plot:
            #     libplot.plot_time_spec_share_nf_ff(sset.ff, None, dset_src.samp_rate)
            # sset.save_trace(nf=False)
            # dset.pickle_dump(unload=False)
    # sset.prune_input(save=True)
    # save_dataset_and_quit(dset)
    pass

if __name__ == "__main__":
    cli()
