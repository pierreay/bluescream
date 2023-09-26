"""Classes representing dataset."""

import os
from os import path
from enum import Enum
import numpy as np
import pickle

import lib.input_generators as input_generators
import lib.load as load
import lib.log as l
import lib.plot as libplot

SubsetType = Enum('SubsetType', ['TRAIN', 'ATTACK'])
InputType = Enum('InputType', ['FIXED', 'VARIABLE'])
InputGeneration = Enum('InputGeneration', ['REAL_TIME', 'INIT_TIME'])

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
    def pickle_load(dir, log=True):
        if not Dataset.is_pickable(dir):
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
            l.LOGGER.info("dataset loaded from {}".format(Dataset.get_path_static(dir)))
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
                 l.LOGGER.info("dataset saved in {}".format(self.get_path(save=True)))

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
        if input_gen == InputGeneration.INIT_TIME and nb_trace_wanted < 1:
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

    def load_trace(self, idx=-1, nf=True, ff=True, check=False):
        """IDX can be -1 for all traces, an INT for a specific trace index, or
        a RANGE for a range of traces. If using a RANGE, please use range(0, x)
        with x > 1. NF and FF can be set to False to not load them in an
        unpacked dataset.

        For scripting conveniance, return references to the loaded trace(s)
        pair (self.nf and self.ff).

        """
        assert(path.exists(self.get_path()))
        if isinstance(idx, int) and idx == -1:
            self.nf, self.ff = load.load_all_traces(self.get_path(), nf_wanted=nf, ff_wanted=ff)
        elif isinstance(idx, int):
            self.nf, self.ff = load.load_pair_trace(self.get_path(), idx, nf=nf, ff=ff)
        elif isinstance(idx, range):
            self.nf, self.ff = load.load_all_traces(self.get_path(), start=idx.start, stop=idx.stop, nf_wanted=nf, ff_wanted=ff)
        self.load_trace_idx = idx
        if check is True:
            if nf is True and self.nf is None:
                raise Exception("can't load nf trace")
            if ff is True and self.ff is None:
                raise Exception("can't load ff trace")
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
                                 self.nf if nf is True else None,
                                 self.ff if ff is True else None)
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
        if self.input_gen == InputGeneration.INIT_TIME:
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
        # Load inputs from already existing stored on-disk.
        elif load.is_key_fixed(self.get_path()) is not None:
            self.ks = np.array(load.load_raw_input(self.get_path(), load.DATASET_RAW_INPUT_KEY_PACK,       self.get_nb_trace_ondisk(), fixed = load.is_key_fixed(self.get_path()), hex=True))
            self.pt = np.array(load.load_raw_input(self.get_path(), load.DATASET_RAW_INPUT_PLAINTEXT_PACK, self.get_nb_trace_ondisk(), fixed = False,                              hex=False))

        self.pt = np.asarray(self.pt)
        self.ks = np.asarray(self.ks)

    def get_nb_trace_ondisk(self, save=False):
        return load.get_nb(self.get_path(save))

    def get_path(self, save=False):
        """Return the full path of the subset. Must be dynamic since the full
        path of the dataset can change since its creation when pickling it.

        """
        return path.join(self.dataset.dir if not save else self.dataset.dirsave, self.dir)

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

    def plot(self):
        libplot.plot_simple(self.MEAN_TRACE)
   
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
