"""Classes representing dataset."""

from multiprocessing import Process, Queue
import os
from os import path
from enum import Enum
import numpy as np
import pickle
import signal
import sys
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm

import lib.input_generators as input_generators
import lib.load as load
import lib.log as l
import lib.plot as libplot
import lib.complex as complex
import lib.analyze as analyze
import lib.utils as utils

TraceType = Enum('TraceType', ['NF', 'FF'])
SubsetType = Enum('SubsetType', ['TRAIN', 'ATTACK'])
InputType = Enum('InputType', ['FIXED', 'VARIABLE'])
InputGeneration = Enum('InputGeneration', ['RUN_TIME', 'INIT_TIME'])

# Global reference to a DatasetProcessing object used for the signal handler.
DPROC = None

class Dataset():
    """Top-level class representing a dataset."""
    FILENAME = "dataset.pyc"

    def __init__(self, name, dir, samp_rate):
        self.name = name
        self.dir = dir
        self.dirsave = dir
        self.samp_rate = samp_rate
        self.train_set = None
        self.attack_set = None
        self.profile = None
        self.dirty = False
        self.dirty_idx = 0
        self.run_resumed = False

    def __str__(self):
        string = "dataset '{}':\n".format(self.name)
        string += "- dir: {}\n".format(self.dir)
        string += "- dirsave: {}\n".format(self.dirsave)
        string += "- samp_rate: {:.2e}\n".format(self.samp_rate)
        string += "- dirty: {}\n".format(self.dirty)
        string += "- dirty_idx: {}\n".format(self.dirty_idx)
        string += "- dirty_savedir: {}\n".format(self.get_savedir_dirty())
        string += "- run_resumed: {}\n".format(self.run_resumed)
        if self.train_set is not None:
            string += str(self.train_set)
        if self.attack_set is not None:
            string += str(self.attack_set)
        if self.profile is not None:
            string += str(self.profile)
        return string

    @staticmethod
    def get_path_static(dir):
        return path.join(dir, Dataset.FILENAME)

    @staticmethod
    def is_pickable(dir):
        return path.exists(Dataset.get_path_static(dir))

    @staticmethod
    def pickle_load(dir, log=True, quit_on_error=False):
        if not Dataset.is_pickable(dir):
            if quit_on_error is True:
                l.LOGGER.error("dataset doesn't exists!")
                exit(-1)
            else:
                return None
        with open(Dataset.get_path_static(dir), "rb") as f:
            pickled = pickle.load(f)
            assert(type(pickled) == Dataset)
            pickled.dir = dir     # Update Dataset.dir (self.dir) when pickling.
            pickled.dirsave = dir # Update Dataset.dirsave (self.dirsave) when pickling.
        if pickled.train_set is not None:
            pickled.train_set.load_input()
        if pickled.attack_set is not None:
            pickled.attack_set.load_input()
        pickled.run_resumed = False
        if log is True:
            l.LOGGER.info("Dataset loaded from '{}'".format(Dataset.get_path_static(dir)))
        return pickled

    def get_path(self, save=False):
        return Dataset.get_path_static(self.dir if save is False else self.dirsave)

    def set_dirsave(self, dirsave):
        """Set saving directory of current Dataset and create subdirectories. for
        registered Subset accordingly."""
        assert(path.exists(dirsave))
        self.dirsave = dirsave
        self.create_dirsave()

    def create_dirsave(self):
        """Create directories for registered Subset accordingly in the saving
        directory."""
        assert(path.exists(self.dirsave))
        if self.train_set is not None:
            os.makedirs(path.join(self.dirsave, self.train_set.dir), exist_ok=True)
        if self.attack_set is not None:
            os.makedirs(path.join(self.dirsave, self.attack_set.dir), exist_ok=True)

    def get_savedir_dirty(self):
        if path.exists(path.join(self.dirsave, Dataset.FILENAME)):
            dset = Dataset.pickle_load(self.dirsave, log=False)
            return dset.dirty
        return False

    def resume_from_savedir(self, subset=None):
        assert(Dataset.is_pickable(self.dirsave))
        dset_dirsave = Dataset.pickle_load(self.dirsave)
        self.run_resumed = True
        self.dirty = dset_dirsave.dirty
        self.dirty_idx = dset_dirsave.dirty_idx
        if subset is not None:
            sset = self.get_subset(subset)
            sset_dirsave = dset_dirsave.get_subset(subset)
            sset.template = sset_dirsave.template
            sset.bad_entries = sset_dirsave.bad_entries

    def pickle_dump(self, force=False, unload=True, log=True):
        if force == False and self.dir == self.dirsave:
            l.LOGGER.warning("save dataset to loaded directory")
            confirm = input("press [enter] to continue")
        self.create_dirsave()
        if self.train_set is not None:
            self.train_set.dump_input(unload=unload)
            if unload is True:
                self.train_set.unload_trace()
        if self.attack_set is not None:
            self.attack_set.dump_input(unload=unload)
            if unload is True:
                self.attack_set.unload_trace()
        with open(self.get_path(save=True), "wb") as f:
             pickle.dump(self, f)
             if log is True:
                 l.LOGGER.info("Dataset saved to '{}'".format(self.get_path(save=True)))

    def add_subset(self, name, subtype, input_gen, nb_trace_wanted=0):
        assert(subtype in SubsetType)
        subset = Subset(self, name, subtype, input_gen, nb_trace_wanted)
        if subtype == SubsetType.TRAIN:
            self.train_set = subset
        elif subtype == SubsetType.ATTACK:
            self.attack_set = subset

    def add_profile(self):
        self.profile = Profile(self)

    def get_subset(self, id):
        """Return a subset. ID can be a string representing the name of the
        subset, or a SubsetType representing the type of the subset.

        """
        if isinstance(id, str):
            if id == self.train_set.name:
                return self.train_set
            elif id == self.attack_set.name:
                return self.attack_set
        elif id in SubsetType:
            if id == SubsetType.TRAIN:
                return self.train_set
            elif id == SubsetType.ATTACK:
                return self.attack_set

    def get_profile(self):
        # Can be None.
        return self.profile

class Subset():
    """Train or attack subset."""
    def __init__(self, dataset, name, subtype, input_gen, nb_trace_wanted = 0):
        assert(subtype in SubsetType)
        assert(input_gen in InputGeneration)
        self.dataset = dataset
        self.name = name
        self.subtype = subtype
        self.input_gen = input_gen
        self.nb_trace_wanted = nb_trace_wanted
        self.load_trace_idx = None
        self.nf = None
        self.ff = None
        self.template = None
        self.bad_entries = []
        if self.input_gen == InputGeneration.INIT_TIME and nb_trace_wanted < 1:
            l.LOGGER.error("initialization of plaintexts and keys at init time using {} traces is not possible!".format(nb_trace_wanted))
            raise Exception("initilization of subset failed!")
        self.init_subset_type()
        self.init_input()

    def init_subset_type(self):
        assert(self.subtype in SubsetType)
        if self.subtype == SubsetType.TRAIN:
            self.dir = "train"
            self.pt_type = InputType.VARIABLE
            self.ks_type = InputType.VARIABLE
        elif self.subtype == SubsetType.ATTACK:
            self.dir = "attack"
            self.pt_type = InputType.VARIABLE
            self.ks_type = InputType.FIXED

    def load_trace(self, idx=-1, nf=True, ff=True, check=False, start_point=0, end_point=0):
        """Load the on-disk traces into memory.

        The loading will put the traces in the self.nf and self.ff
        variables. For scripting conveniance, the functions also returns
        references to the loaded trace(s). The trace(s) are loaded into a 2D
        np.ndarray.

        IDX can be -1 for all traces, an INT for a specific trace index, or
        a RANGE for a range of traces. If using a RANGE, please use range(0, x)
        with x > 1. NF and FF can be set to False to not load them in an
        unpacked dataset.

        Traces truncation during loading can be achieved using START_POINT and
        END_POINT. If START_POINT is set to different from 0, use it as start index
        during loading the traces. If END_POINT is set to different from 0, use it
        as end index during loading the traces.

        """
        assert(path.exists(self.get_path()))
        if isinstance(idx, int) and idx == -1:
            self.nf, self.ff = load.load_all_traces(self.get_path(), nf_wanted=nf, ff_wanted=ff, start_point=start_point, end_point=end_point)
        elif isinstance(idx, int):
            self.nf, self.ff = load.load_pair_trace(self.get_path(), idx, nf=nf, ff=ff)
            self.nf = None if self.nf is None else load.truncate(self.nf, start_point, end_point)
            self.ff = None if self.ff is None else load.truncate(self.ff, start_point, end_point)
        elif isinstance(idx, range):
            self.nf, self.ff = load.load_all_traces(self.get_path(), start=idx.start, stop=idx.stop, nf_wanted=nf, ff_wanted=ff, start_point=start_point, end_point=end_point)
        # NOTE: Always return 2D np.ndarray.
        self.nf = utils.list_array_to_2d_array(self.nf)
        self.ff = utils.list_array_to_2d_array(self.ff)
        self.load_trace_idx = idx
        if check is True:
            if nf is True and self.nf is None:
                raise Exception("Can't load NF trace!")
            if ff is True and self.ff is None:
                raise Exception("Can't load FF trace!")
        # Check dimensions.
        assert self.nf is None or self.nf.ndim == 2
        assert self.ff is None or self.ff.ndim == 2
        return self.nf, self.ff

    def unload_trace(self):
        """Delete and forget references about any loaded trace(s) from disk."""
        self.load_trace_idx = None
        del self.nf
        self.nf = None
        del self.ff
        self.ff = None

    def save_trace(self, nf=True, ff=True):
        if isinstance(self.load_trace_idx, int) and self.load_trace_idx == -1:
            load.save_all_traces(self.get_path(save=True),
                                 self.nf if nf is True else None,
                                 self.ff if ff is True else None,
                                 packed=False)
        elif isinstance(self.load_trace_idx, int) and self.load_trace_idx > -1:
            load.save_pair_trace(self.get_path(save=True), self.load_trace_idx,
                                 self.nf[0] if nf is True else None,
                                 self.ff[0] if ff is True else None)
        elif isinstance(self.load_trace_idx, range):
            load.save_all_traces(self.get_path(save=True),
                                 self.nf if nf is True else None,
                                 self.ff if ff is True else None,
                                 packed=False, start=self.load_trace_idx.start, stop=self.load_trace_idx.stop)
        self.unload_trace()

    def get_save_trace_exist(self, idx=-1):
        idx = idx if idx > -1 else self.load_trace_idx
        return load.is_dataset_unpacked(self.get_path(save=True), idx)

    def load_input(self):
        if path.exists(self.get_path()):
            self.pt = load.load_plaintexts(self.get_path())
            self.ks = load.load_keys(self.get_path())

    def dump_input(self, unload=True):
        assert(path.exists(self.get_path()))
        if self.pt is not None:
            load.save_plaintexts(self.get_path(save=True), self.pt)
            if unload is True:
                del self.pt
                self.pt = None
        if self.ks is not None:
            load.save_keys(self.get_path(save=True), self.ks)
            if unload is True:
                del self.ks
                self.ks = None

    def prune_input(self, save=False):
        self.ks = load.prune_entry(self.ks, range(self.get_nb_trace_ondisk(save=save), len(self.ks)))
        self.pt = load.prune_entry(self.pt, range(self.get_nb_trace_ondisk(save=save), len(self.pt)))

    def init_input(self):
        assert(self.input_gen in InputGeneration)
        assert(self.pt_type in InputType and self.ks_type in InputType)
        self.pt = []
        self.ks = []
        # Handle generation at initialization time.
        if self.input_gen == InputGeneration.INIT_TIME:
            self.init_input_init_time()

        # NOTE: np.uint8 is important to specify here because of the
        # ".tobytes()" function used in "lib/utils.py". It is the size of each
        # array element which is 1 byte.
        self.pt = np.asarray(self.pt, dtype=np.uint8)
        self.ks = np.asarray(self.ks, dtype=np.uint8)

    def init_input_init_time(self):
        """Generate the input when InputGeneration has been set to INIT_TIME."""
        assert(self.input_gen == InputGeneration.INIT_TIME)
        if self.subtype == SubsetType.TRAIN:
            generator = input_generators.balanced_generator
        elif self.subtype == SubsetType.ATTACK:
            generator = input_generators.unrestricted_generator
        if self.pt_type == InputType.VARIABLE and self.ks_type == InputType.FIXED:
            self.ks = [generator(length=16).__next__()]
            for plaintext in generator(length=16, bunches=256):
                if len(self.pt) == self.nb_trace_wanted:
                    break
                self.pt.append(plaintext)
            assert(len(self.pt) == self.nb_trace_wanted)
            assert(len(self.ks) == 1)
        elif self.pt_type == InputType.VARIABLE and self.ks_type == InputType.VARIABLE:
            for key in generator(length=16):
                for plaintext in generator(length=16):
                    if len(self.pt) == self.nb_trace_wanted:
                        break
                    self.ks.append(key)
                    self.pt.append(plaintext)
                if len(self.pt) == self.nb_trace_wanted:
                    break
            assert(len(self.pt) == len(self.ks))
            assert(len(self.pt) == self.nb_trace_wanted)

    def get_nb_trace_ondisk(self, save=False):
        return load.get_nb(self.get_path(save))

    def get_path(self, save=False):
        """Return the full path of the subset. Must be dynamic since the full
        path of the dataset can change since its creation when pickling it.

        """
        return path.join(self.dataset.dir if not save else self.dataset.dirsave, self.dir)

    def replace_trace(self, sig, typ):
        """Replace traces with new one(s).

        This function has to be used when we want to register new trace(s) in a
        subset which doesn't have the same shape, for example after a
        processing (e.g. extraction). Hence, all previously contained traces
        will be replaced by the new one(s).

        SIG is a ND np.ndarray containing trace(s), TYP is a TraceType.[NF|FF]
        to choose between near-field trace or far-field trace.

        """
        if typ == TraceType.NF:
            del self.nf
            self.nf = np.array(sig, ndmin=2)
        elif typ == TraceType.FF:
            del self.ff
            self.ff = np.array(sig, ndmin=2)

    def __str__(self):
        string = "subset '{}':\n".format(self.name)
        string += "- dir: {}\n".format(self.dir)
        string += "- get_path(save=False): {}\n".format(self.get_path(save=False))
        string += "- get_path(save=True): {}\n".format(self.get_path(save=True))
        if self.nf is not None:
            assert(type(self.nf) == np.ndarray)
            string += "- loaded near-field trace shape is {}\n".format(self.nf.shape)
        if self.ff is not None:
            assert(type(self.ff) == np.ndarray)
            string += "- loaded far-field trace shape is {}\n".format(self.ff.shape)
        if self.ks is not None:
            assert(type(self.ks) == np.ndarray)
            string += "- loaded keys shape is {}\n".format(self.ks.shape)
        if self.pt is not None:
            assert(type(self.pt) == np.ndarray)
            string += "- loaded plaintexts shape is {}\n".format(self.pt.shape)
        if self.load_trace_idx is not None:
            string += "- loaded trace idx: {}\n".format(self.load_trace_idx)
        if self.template is not None:
            string += "- template shape: {}\n".format(self.template.shape)
        string += "- on-disk number of traces is {}\n".format(self.get_nb_trace_ondisk())
        string += "- bad entries are {}\n".format(self.bad_entries)
        return string

    def get_current_ks(self, idx):
        """Get the current key based on an recording index.

        Assert for correct index bounds.

        """
        assert idx >= 0 and (self.ks_type == InputType.FIXED or idx < len(self.ks))
        return self.ks[0 if self.ks_type == InputType.FIXED else idx]

    def get_current_pt(self, idx):
        """Get the current plaintext based on an recording index.

        Assert for correct index bounds.

        """
        assert idx >= 0 and idx < len(self.pt)
        return self.pt[idx]

class Profile():
    POIS_FN       = "POIS.npy"
    RS_FN         = "PROFILE_RS.npy"
    RZS_FN        = "PROFILE_RZS.npy"
    MEANS_FN      = "PROFILE_MEANS.npy"
    STDS_FN       = "PROFILE_STDS.npy"
    COVS_FN       = "PROFILE_COVS.npy"
    MEAN_TRACE_FN = "PROFILE_MEAN_TRACE.npy"
    
    def __init__(self, dataset):
        self.dir = "profile"   # Fixed subdirectory.
        self.dataset = dataset # Parent. Don't need to save the subset as the
                               # subset is always train for a profile.
        # Profile data.
        self.POIS = None
        self.RS = None
        self.RZS = None
        self.MEANS = None
        self.STDS = None
        self.COVS = None
        self.MEAN_TRACE = None
        self.POINT_START = None # Starting point used in original trace.
        self.POINT_END   = None # Ending point used in original trace.

    def get_path(self, save=False):
        return path.join(self.dataset.dir, self.dir)

    # Store useful information about the profile, to be used for comparing profiles,
    # or for profiled correlation and template attacks.
    def save(self):
        assert(path.exists(self.dataset.dir))
        os.makedirs(self.get_path(), exist_ok=True)
        np.save(path.join(self.get_path(), Profile.POIS_FN), self.POIS)
        np.save(path.join(self.get_path(), Profile.RS_FN), self.RS)
        np.save(path.join(self.get_path(), Profile.RZS_FN), self.RZS)
        np.save(path.join(self.get_path(), Profile.MEANS_FN), self.MEANS)
        np.save(path.join(self.get_path(), Profile.STDS_FN), self.STDS)
        np.save(path.join(self.get_path(), Profile.COVS_FN), self.COVS)
        np.save(path.join(self.get_path(), Profile.MEAN_TRACE_FN), self.MEAN_TRACE)

    # Load the profile, for comparison or for attacks.
    def load(self):
        self.POIS       = np.load(path.join(self.get_path(), Profile.POIS_FN))
        self.RS         = np.load(path.join(self.get_path(), Profile.RS_FN))
        self.RZS        = np.load(path.join(self.get_path(), Profile.RZS_FN))
        self.MEANS      = np.load(path.join(self.get_path(), Profile.MEANS_FN))
        self.COVS       = np.load(path.join(self.get_path(), Profile.COVS_FN))
        self.STDS       = np.load(path.join(self.get_path(), Profile.STDS_FN))
        self.MEAN_TRACE = np.load(path.join(self.get_path(), Profile.MEAN_TRACE_FN))

    def plot(self, delim=False):
        # Simple plot of the profile.
        if delim is False:
            libplot.plot_simple(self.MEAN_TRACE)
        # Advanced plot. Print the delimiters using the FF trace #0.
        # NOTE: This part imply that profile has been built with FF and not NF.
        else:
            if self.dataset.train_set.ff is None:
                self.dataset.train_set.load_trace(0, nf=False, ff=True, check=True)
            libplot.plot_time_spec_sync_axis(self.dataset.train_set.ff[0:1], samp_rate=self.dataset.samp_rate, peaks=[self.POINT_START, self.POINT_END])
   
    def __str__(self):
        string = "profile:\n"
        string += "- dir: {}\n".format(self.dir)
        string += "- get_path(): {}\n".format(self.get_path())
        if self.POIS is not None:
            string += "- pois shape: {}\n".format(self.POIS.shape)
        if self.MEAN_TRACE is not None:
            string += "- profile trace shape: {}\n".format(self.MEAN_TRACE.shape)
        if self.POINT_START:
            string += "- profile start point: {}\n".format(self.POINT_START)
        if self.POINT_END:
            string += "- profile end point: {}\n".format(self.POINT_END)
        return string

class DatasetProcessing():
    """Processing workflow using a Dataset.

    Allows to use friendly interface functions for scripting and advanced
    processing functions (e.g. parallelization).

    Functions:
    - resume: Resume from previous processing.
    - create: Create a new processing.
    - process: Execute the previously created processing.
    - disable_plot: Disable the plot(s) for next processing.
    - disable_parallel: Disable the processing parallelization.
    - restore_parallel: Restore the previous processing parallelization.
    - is_parallel: To know if parallelization is enabled.

    """

    # * List all public variables.
    # Dataset of the processing.
    # NOTE: Mandatory to not be None.
    dset = None
    # Subset of the processing.
    # NOTE: Mandatory to not be None.
    sset = None
    # Index of start trace for the processing.
    start = 0
    # Index of stop trace for the processing (-1 means infinite).
    stop = -1
    # Processing title.
    process_title = None
    # Processing function. Must have this signature:
    # FUNC_NAME(dset, sset, plot, args)
    # Where the FUNC_NAME can get supplementary arguments from the ARGS list/tuple.
    process_fn = None
    # Processing plotting switch (a PlotOnce class).
    process_plot = None
    # Processing function arguments.
    process_args = None
    # Processing number of workers.
    # < 0 = maximum available processes.
    # > 0 = specified number of processes.
    # 0 = no process, run sequentially.
    process_nb = None
    _process_nb = None # Backup.

    def __init__(self, indir, subset, outdir=None, stop=-1):
        """Initialize a dataset processing.

        Load a dataset from INDIR and load the SUBSET subset. If OUTDIR is not
        None, set it as the savedir of the dataset. On error during the dataset
        loading, quit the programm.

        """
        # Install the signal handler.
        self.__signal_install()
        # Get dataset and subset.
        self.dset = Dataset.pickle_load(indir, quit_on_error=True)
        self.sset = self.dset.get_subset(subset)
        assert self.dset is not None and self.sset is not None
        # Set the outdir directory for saving.
        if outdir is not None:
            self.dset.set_dirsave(outdir)
        # Set stop trace.
        if stop == -1:
            self.stop = self.sset.get_nb_trace_ondisk()
        else:
            self.stop = stop
        # Set the dirty flag to True after loading.
        self.dset.dirty = True

    def resume(self, from_zero=False):
        """Resume the processing of a dataset...

        If:
        - The FROM_ZERO parameter is set to False.
        - The DIRTY flag of the previsouly saved dataset is set to True.

        By:
        1. Fetching the template previously saved.
        2. Fetching the bad entries previously saved.
        3. Using the dirty idx previously saved as start index.

        """
        if from_zero is False and self.dset.get_savedir_dirty():
            self.dset.resume_from_savedir(self.sset.subtype)
            self.start = self.dset.dirty_idx
            l.LOGGER.info("Resume at trace {} using template from previous processing".format(self.start))
            l.LOGGER.debug("Template: shape={}".format(self.sset.template.shape))

    def create(self, title, fn, plot, args, nb = -1):
        """Create a processing.

        The processing will be titled TITLE, running the function FN using the
        plot switch PLOT and custom arguments ARGS.

        If NB is set to negative number, use the maximum number of workers. If
        set to a positive number, use this as number of workers. If set to 0,
        disable multi-process processing and use a single-process processing.

        """
        assert isinstance(plot, libplot.PlotOnce), "plot parameter must be a PlotOnce class!"
        self.process_title = title
        self.process_fn = fn
        self.process_plot = plot
        self.process_args = args
        if nb < 0:
            self.process_nb = os.cpu_count() - 1
            l.LOGGER.info("Automatically select {} processes for parallelization".format(self.process_nb))
        else:
            self.process_nb = nb
        self._process_nb = self.process_nb

    def process(self):
        """Run the (parallelized) processing.

        The processing must be configured using DatasetProcessing.create()
        before to use this function.

        """
        # Check that self.create() function has been called.
        assert self.process_title is not None
        assert self.process_fn is not None
        assert self.process_plot is not None
        assert self.process_args is not None
        assert self.process_nb >= 0
        
        def _init(i, stop):
            """Initialize the processing starting at trace index I.

            Return a tuple composed of the Queue for result transfer and a list
            of processes.

            """
            # NOTE: The first processing needs to be executed in the main
            # process to modify the dataset object. Remaning processings could
            # rely on this one to get some parameters (e.g. the template
            # signal).
            self.disable_parallel(i == 0)
            # Queue for transferring results from processing function (parallelized or not).
            q = Queue()
            # List of processes. Only create necessary processes.
            ps_len = self.process_nb
            if i + self.process_nb >= stop:
                ps_len -= i + self.process_nb - stop
            ps = [None] * ps_len
            # Initialize the processes if needed (but do not run them).
            for idx, _ in enumerate(ps):
                l.LOGGER.debug("Create process index #{} for trace index #{}".format(idx, i + idx))
                ps[idx] = Process(target=self.__process_fn, args=(q, self.dset, self.sset, i + idx, self.process_plot.pop(), self.process_args,))
            return q, ps

        def _run(i, q, ps):
            """Run the processing starting at trace index I using the Queue Q
            and the processes of list PS.

            """
            # Create the processes and perform the parallelized processing...
            if self.is_parallel():
                for idx, proc in enumerate(ps):
                    proc.start()
                    l.LOGGER.debug("Started process: idx={}".format(idx))
            # ...or perform process sequentially.
            else:
                self.__process_fn(q, self.dset, self.sset, i, self.process_plot.pop(), self.process_args)

        def _get(q, ps):
            """Get the processing results using the Queue Q and the processes of list PS."""
            # Check the result.
            for _, __ in enumerate(ps):
                l.LOGGER.debug("Wait result from queue...")
                check, i_processed = q.get()
                if check is True:
                    self.sset.bad_entries.append(i_processed)

        def _end(i_done, ps, pbar=None):
            """Terminate the processing for trace index I_DONE.

            1. Update the processing loop information to prepare the next
               processing.
            2. Save the processing state in the dataset for further
               resuming.
            3. If parallelized, terminated the processing contained in
               the PS list.
            4. If specified, update TQDM's PBAR just like index I_DONE.

            Return the new index I for next processing.

            """
            # Terminate the processes.
            for idx, proc in enumerate(ps):
                l.LOGGER.debug("Join process... idx={}".format(idx))
                proc.join()
            # Update the progress index and bar.
            # NOTE: Handle case where process_nb == 0 for single-process processing.
            i_step = len(ps) if self.process_nb > 0 else 1
            i = i_done + i_step
            pbar.update(i_step)
            # Save dataset for resuming if not finishing the loop.
            self.dset.dirty_idx = i
            self.dset.pickle_dump(unload=False, log=False)
            # Restore parallelization after first trace processing if needed.
            # NOTE: Should be at the end since it will modify self.process_nb.
            self.restore_parallel(i_done == 0)
            l.LOGGER.debug("Finished processing: trace #{} -> #{}".format(i_done, i - 1))
            return i
            
        # Setup progress bar.
        with (logging_redirect_tqdm(loggers=[l.LOGGER]),
              tqdm(initial=self.start, total=self.stop, desc=self.process_title) as pbar,):
            i = self.start
            while i < self.stop:
                # Initialize processing for trace(s) starting at index i.
                q, ps = _init(i, self.stop)
                # Run the processing.
                _run(i, q, ps)
                # Get and check the results.
                _get(q, ps)
                # Terminate the processing.
                i = _end(i, ps, pbar=pbar)

    def disable_plot(self, cond=True):
        """Disable the plotting parameter if COND is True."""
        if cond is True and self.process_plot is True:
            l.LOGGER.debug("Disable plotting for next processings")
            self.process_plot = False

    def disable_parallel(self, cond=True):
        """Disable the parallel processing if COND is True.

        One can call restore_parallel() to restore the previous parallelization
        value.

        """
        if cond is True and self.is_parallel() is True:
            l.LOGGER.debug("Disable parallelization for next processings")
            self._process_nb = self.process_nb
            self.process_nb = 0

    def restore_parallel(self, cond=True):
        """Restore the process parallelization as before disable_parallel()
        call if COND is True.

        """
        if cond is True and self.is_parallel(was=True):
            l.LOGGER.debug("Restore previous parallelization value for next processings")
            self.process_nb = self._process_nb

    def is_parallel(self, was=False):
        """Return True if parallelization is enabled, False otherwise.

        Set WAS to True to test against the value before the disable_parallel()
        call.

        """
        return self.process_nb > 0 if was is False else self._process_nb > 0

    def __signal_install(self):
        """Install the signal handler.

        Catch the SIGINT signal.

        """
        global DPROC
        DPROC = self
        signal.signal(signal.SIGINT, self.__signal_handler)

    def __process_fn(self, q, dset, sset, i, plot, args):
        """Main function for processes.

        It is usually ran by a caller process from the self.process/_run()
        function. It may be run in the main proces too. It will load a trace,
        execute the processing based on the self.process_fn function pointer,
        may check and plot the result, and save the resulting trace.

        Q is a Queue to transmit the results, DSET a Dataset, SSET a Subset, I
        the trace index to load and process, PLOT a flag indicating to plot the
        result, and ARGS additionnal arguments transmitted to the
        self.process_fn function.

        """
        l.LOGGER.debug("Start __process_fn() for trace #{}...".format(i))
        # * Load the trace to process.
        # NOTE: We choose to always load traces one by one since raw traces can
        # be large (> 30 MB).
        sset.load_trace(i, nf=False, ff=True, check=True)
        # * Apply the processing and get the resulting trace.
        # NOTE: ff can be None if the processing fails.
        ff = self.process_fn(dset, sset, plot, args)
        # * Check the trace is valid.
        check = False
        if i > 0:
            check, ff_checked = analyze.fill_zeros_if_bad(sset.template, ff, log=True, log_idx=i)
        elif i == 0 and ff is not None:
            l.LOGGER.info("Trace #0 processing (e.g. creating a template) is assumed to be valid!")
            ff_checked = ff
        else:
            raise Exception("Trace #0 processing encountered an error!")
        sset.replace_trace(ff_checked, TraceType.FF)
        # * Plot the averaged trace if wanted and processing succeed.
        if sset.ff[0] is not None:
            libplot.plot_time_spec_sync_axis(sset.ff[0:1], samp_rate=dset.samp_rate, cond=plot, comp=complex.CompType.AMPLITUDE)
        # * Save the processed trace and transmit result to caller process.
        sset.save_trace(nf=False)
        q.put((check, i))
        l.LOGGER.debug("End __process_fn() for trace #{}".format(i))

    @staticmethod
    def __signal_handler(sig, frame):
        """Catch signal properly exiting process.

        Signal handler supposed to catch SIGINT to properly quit the processing
        by setting the stop index to 0.

        """
        global DPROC
        DPROC.stop = 0

    def __str__(self):
        """Return the __str__ from the dataset."""
        string = "dataset_processing:\n"
        string += "- start: {}\n".format(self.start)
        string += "- stop: {}\n".format(self.stop)
        return string + self.dset.__str__()
