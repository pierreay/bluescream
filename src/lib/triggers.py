"""Classes representing trigger signals."""

class Triggers():
    def __init__(self):
        self.triggers = []
        self.bandpass_low = []
        self.bandpass_high = []
        pass

    def add(self, t):
        self.triggers.append(t)
        self.bandpass_low.append(t.bandpass_low)
        self.bandpass_high.append(t.bandpass_high)

    def get(self, idx):
        return self.triggers[idx]

    def nb(self):
        return len(self.triggers)

    def nb_composed(self):
        return len(self.bandpass_low)

    def reduce_add(self):
        while self.nb() > 1:
            print("Triggers.reduce_add().nb()={}".format(self.nb()))
            trigger = self.triggers.pop()
            self.triggers[0].signal += trigger.signal
        self.triggers[0].signal = analyze.normalize(self.triggers[0].signal)
        print("Triggers.reduce_add().nb()={}".format(self.nb()))

class Trigger():
    def __init__(self, s, bpl, bph, lp):
        self.bandpass_low = bpl
        self.bandpass_high = bph
        self.lowpass = lp
        signal = filters.butter_bandpass_filter(s, bpl, bph, SAMP_RATE)
        signal = np.abs(signal)
        signal = filters.butter_lowpass_filter(signal, lp, SAMP_RATE, TRG_LP_ORDER)
        signal = analyze.normalize(signal)
        self.signal = signal
