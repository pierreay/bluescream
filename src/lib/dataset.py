"""Classes representing dataset."""

import path
import pickle

DatasetType = Enum('DatasetType', ['TRAINING', 'ATTACK'])
InputType = Enum('InputType', ['FIXED', 'VARIABLE'])
InputGeneration = Enum('InputGeneration', ['REAL_TIME', 'INIT_TIME'])

class Dataset():
    """Top-level class representing a dataset."""
    file         = "dataset.pyc"

    name         = None

    training_set = None
    attack_set   = None

    def __init__(self, name):
        self.name = name

    def __str__(self):
        string = "name={}".format(self.name)
        if self.training_set is not None:
            string = "{}\ntraining_set:\n{}".format(string, str(self.training_set))
        if self.attack_set is not None:
            string = "{}\nattack_set:\n{}".format(string, str(self.attack_set))
        return string

    @staticmethod
    def is_pickable(path):
        return path.exists(path.join(path, Dataset.file))

    @staticmethod
    def pickle_load(path):
        with open(path.join(path, Dataset.file), "rb") as f:
            return pickle.load(f)

    def pickle_dump(self, path):
        with open(path.join(path, Dataset.file), "wb") as f:
            pickle.dump(self, f)

    def add_set(self, set, type):
        assert(type in DatasetType)
        if type == DatasetType.TRAINING:
            self.training_set = set
        elif type == DatasetType.ATTACK:
            self.training_set = set
    
class TrainingSet():
    """Training dataset."""
    dir = "train"
    pt_type = InputType.VARIABLE
    ks_type = InputType.VARIABLE

    name = None
    pt_gen = None
    ks_gen = None

    nb_trace = 0

    def __init__(self, name, pt_gen, ks_gen):
        assert(pt_gen in InputGeneration and ks_gen in InputGeneration)
        self.name = name
        self.pt_gen = pt_gen
        self.ks_gen = ks_gen

    def __str__(self):
        return "name={}".format(self.name)

class AttackSet():
    """Attack dataset."""
    dir = "attack"
    pt_type = InputType.FIXED
    ks_type = InputType.VARIABLE

    name = None
    pt_gen = None
    ks_gen = None

    nb_trace = 0

    def __init__(self, name, nb_trace, pt_gen, ks_gen):
        assert(pt_gen in InputGeneration and ks_gen in InputGeneration)
        self.name = name
        self.pt_gen = pt_gen
        self.ks_gen = ks_gen

    def __str__(self):
        return "name={}".format(self.name)
