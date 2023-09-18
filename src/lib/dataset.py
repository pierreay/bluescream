"""Classes representing dataset."""

import os
from os import path
from enum import Enum
import numpy as np
import pickle

import lib.input_generators as input_generators
import lib.load as load
import lib.log as l

SubsetType = Enum('SubsetType', ['TRAIN', 'ATTACK'])
InputType = Enum('InputType', ['FIXED', 'VARIABLE'])
InputGeneration = Enum('InputGeneration', ['REAL_TIME', 'INIT_TIME'])

class Dataset():
    """Top-level class representing a dataset."""
    FILENAME = "dataset.pyc"

    def __init__(self, name, dir, samp_rate):
        self.name = name
        self.dir = dir
        self.samp_rate = samp_rate
        self.train_set = None
        self.attack_set = None

    def __str__(self):
        string = "dataset '{}':\n".format(self.name)
        string += "- dir: {}\n".format(self.dir)
        string += "- samp_rate: {:.2e}\n".format(self.samp_rate)
        if self.train_set is not None:
            string += str(self.train_set)
        if self.attack_set is not None:
            string += str(self.attack_set)
        return string

    @staticmethod
    def get_path(dir):
        return path.join(dir, Dataset.FILENAME)

    @staticmethod
    def is_pickable(dir):
        return path.exists(Dataset.get_path(dir))

    @staticmethod
    def pickle_load(dir):
        if not path.exists(Dataset.get_path(dir)):
            return None
        with open(Dataset.get_path(dir), "rb") as f:
            pickled = pickle.load(f)
            assert(type(pickled) == Dataset)
            pickled.dir = dir # self.dir
        if pickled.train_set is not None:
            pickled.train_set.load_input(pickled.dir)
        if pickled.attack_set is not None:
            pickled.attack_set.load_input(pickled.dir)
        return pickled

    def pickle_dump(self):
        if self.train_set is not None:
            os.makedirs(path.join(self.dir, self.train_set.dir), exist_ok=True)
            self.train_set.dump_input(self.dir)
        if self.attack_set is not None:
            os.makedirs(path.join(self.dir, self.attack_set.dir), exist_ok=True)
            self.attack_set.dump_input(self.dir)
        with open(Dataset.get_path(self.dir), "wb") as f:
             pickle.dump(self, f)

    def add_subset(self, name, subtype, input_gen, nb_trace_wanted=0):
        assert(subtype in SubsetType)
        subset = Subset(self, name, subtype, input_gen, nb_trace_wanted)
        if subtype == SubsetType.TRAIN:
            self.train_set = subset
        elif subtype == SubsetType.ATTACK:
            self.attack_set = subset

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
    
class Subset():
    """Train or attack subset."""
    def __init__(self, dataset, name, subtype, input_gen, nb_trace_wanted = 0):
        assert(subtype in SubsetType) 
        assert(input_gen in InputGeneration)
        self.dataset = dataset
        self.name = name
        self.subtype = subtype
        self.input_gen = input_gen
        self.nb_trace_current = 0
        self.nb_trace_wanted = nb_trace_wanted
        self.trace_dirty = False
        self.nf = None
        self.ff = None
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

    def load_trace(self, idx=0):
        """IDX can be 0 for all traces, an INT for a specific trace index, or a
        RANGE for a range of traces. If using a RANGE, please use range(0, x)
        with x > 1.

        """
        fp = path.join(self.dataset.dir, self.dir)
        assert(path.exists(fp))
        if idx == 0:
            self.nf, self.ff = load.load_all_traces(fp)
        elif isinstance(idx, int):
            self.nf, self.ff = load.load_pair_trace(fp, idx)
        elif isinstance(idx, range):
            self.nf, self.ff = load.load_all_traces(fp, idx.stop)

    def load_input(self, dir):
        fp = path.join(dir, self.dir)
        if path.exists(fp):
            self.pt = load.load_plaintexts(fp)
            self.ks = load.load_keys(fp)

    def dump_input(self, dir):
        fp = path.join(dir, self.dir)
        assert(path.exists(fp))
        if self.pt is not None:
            load.save_plaintexts(fp, self.pt)
            self.pt = None
        if self.ks is not None:
            load.save_keys(fp, self.ks)
            self.ks = None

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
        self.pt = np.asarray(self.pt)
        self.ks = np.asarray(self.ks)

    def __str__(self):
        string = "subset '{}':\n".format(self.name)
        if self.nf is not None:
            assert(type(self.nf) == np.ndarray)
            string += "- near-field trace shape is {}\n".format(self.nf.shape)
        if self.ff is not None:
            assert(type(self.ff) == np.ndarray)
            string += "- far-field trace shape is {}\n".format(self.ff.shape)
        if self.ks is not None:
            assert(type(self.ks) == np.ndarray)
            string += "- keys shape is {}\n".format(self.ks.shape)
        if self.pt is not None:
            assert(type(self.pt) == np.ndarray)
            string += "- plaintexts shape is {}\n".format(self.pt.shape)
        return string
