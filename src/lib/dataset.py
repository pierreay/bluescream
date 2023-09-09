"""Classes representing dataset."""

DatasetType   = Enum('DatasetType'  , ['TRAINING', 'ATTACK'])
InputType     = Enum('InputType'    , ['FIXED',    'VARIABLE'])

class Dataset():
    """Top-level class representing a dataset."""

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

    def add_set(self, set, type):
        assert(type in DatasetType)
        if type == DatasetType.TRAINING:
            self.training_set = set
        elif type == DatasetType.ATTACK:
            self.training_set = set

class TrainingSet():
    """Training dataset."""

    name = None
    nb_trace = 0
    pt_type = InputType.VARIABLE
    ks_type = InputType.VARIABLE

    def __init__(self, name):
        self.name = name

    def __str__(self):
        return "name={}".format(self.name)

class AttackSet():
    """Attack dataset."""

    name = None
    nb_trace = 0
    pt_type = InputType.FIXED
    ks_type = InputType.VARIABLE

    def __init__(self, name):
        self.name = name

    def __str__(self):
        return "name={}".format(self.name)
