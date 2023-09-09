"""Classes representing dataset."""

from os import path
from enum import Enum
import pickle

import lib.input_generators as input_generators
import lib.load as load
import lib.log as l

SubsetType = Enum('SubsetType', ['TRAIN', 'ATTACK'])
InputType = Enum('InputType', ['FIXED', 'VARIABLE'])
InputGeneration = Enum('InputGeneration', ['REAL_TIME', 'INIT_TIME'])

class Dataset():
    """Top-level class representing a dataset."""
    file = "dataset.pyc"

    train_set = None
    attack_set = None

    def __init__(self, name):
        self.name = name

    def __str__(self):
        string = "name={}".format(self.name)
        if self.train_set is not None:
            string = "{}\ntrain_set:\n{}".format(string, str(self.train_set))
        if self.attack_set is not None:
            string = "{}\nattack_set:\n{}".format(string, str(self.attack_set))
        return string

    @staticmethod
    def get_path(dir):
        return path.join(dir, Dataset.file)

    @staticmethod
    def is_pickable(dir):
        return path.exists(Dataset.get_path(dir))

    @staticmethod
    def pickle_load(dir):
        if not path.exists(Dataset.get_path(dir)):
            return None
        with open(Dataset.get_path(dir), "rb") as f:
            return pickle.load(f)

    def pickle_dump(self, dir):
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
    nb_trace = 0

    def __init__(self, name, subtype, pt_gen, ks_gen):
        assert(subtype in SubsetType) 
        assert(pt_gen in InputGeneration and ks_gen in InputGeneration)
        self.name = name
        self.subtype = subtype
        self.pt_gen = pt_gen
        self.ks_gen = ks_gen
        if self.subtype == SubsetType.TRAIN:
            self.dir = "train"
            self.pt_type = InputType.VARIABLE
            self.ks_type = InputType.VARIABLE
        elif self.subtype == SubsetType.ATTACK:
            self.dir = "attack"
            self.pt_type = InputType.FIXED
            self.ks_type = InputType.VARIABLE

    def __str__(self):
        return "name={}".format(self.name)
