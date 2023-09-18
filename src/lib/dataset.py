"""Classes representing dataset."""

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

    train_set = None
    attack_set = None

    def __init__(self, name, dir):
        self.name = name
        self.dir = dir

    def __str__(self):
        string = "dataset '{}':\n".format(self.name)
        string += "- dir: {}\n".format(self.dir)
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
            pickled.train_set.load_trace(pickled.dir)
        if pickled.attack_set is not None:
            pickled.attack_set.load_input(pickled.dir)
            pickled.attack_set.load_trace(pickled.dir)
        return pickled

    def pickle_dump(self, dir):
        if self.train_set is not None:
            self.train_set.dump_input(self.dir)
            self.train_set.dump_trace(self.dir)
        if self.attack_set is not None:
            self.attack_set.dump_input(self.dir)
            self.attack_set.dump_trace(self.dir)
        with open(Dataset.get_path(dir), "wb") as f:
             pickle.dump(self, f)

    def add_set(self, subset):
        assert(subset.subtype in SubsetType)
        if subset.subtype == SubsetType.TRAIN:
            self.train_set = subset
        elif subset.subtype == SubsetType.ATTACK:
            self.attack_set = subset
    
class Subset():
    """Train or attack subset."""
    nb_trace_current = 0
    nb_trace_wanted = 0

    def __init__(self, name, subtype, input_gen, nb_trace_wanted = 0):
        assert(subtype in SubsetType) 
        assert(input_gen in InputGeneration)
        self.name = name
        self.subtype = subtype
        self.input_gen = input_gen
        self.nb_trace_wanted = nb_trace_wanted
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

    def load_trace(self, dir):
        pass

    def dump_trace(self, dir):
        pass

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
        if self.ks is not None:
            assert(type(self.ks) == np.ndarray)
            string += "- keys shape is {}\n".format(self.ks.shape)
        if self.pt is not None:
            assert(type(self.pt) == np.ndarray)
            string += "- plaintexts shape is {}\n".format(self.pt.shape)
        return string
