#!/usr/bin/env python3

import sys
from os import path
import numpy as np
import matplotlib.pyplot as plt

import lib.plot as libplot

PLOT = False
SAVE_IMAGES = True

TEMPLATE_DIR_1 = sys.argv[1]
TEMPLATE_DIR_2 = sys.argv[2]
SAVE_IMAGES_PATH = sys.argv[3]

class Profile:
    NUM_KEY_BYTES = 16
    def __init__(self, template_dir):
        self.POIS = np.load(path.join(template_dir, "POIS.npy"))
        self.PROFILE_RS = np.load(path.join(template_dir, "PROFILE_RS.npy"))
        self.PROFILE_RZS = np.load(path.join(template_dir, "PROFILE_RZS.npy"))
        self.PROFILE_MEANS = np.load(path.join(template_dir, "PROFILE_MEANS.npy"))
        self.PROFILE_COVS = np.load(path.join(template_dir, "PROFILE_COVS.npy"))
        self.PROFILE_STDS = np.load(path.join(template_dir, "PROFILE_STDS.npy"))
        self.PROFILE_MEAN_TRACE = np.load(path.join(template_dir, "PROFILE_MEAN_TRACE.npy"))

    def plot(self):
        global SAVE_IMAGES, PLOT
        informative = self.PROFILE_RS
        num_plots = 2
        plt.subplots_adjust(hspace = 1) 
        plt.subplot(num_plots, 1, 1)
        plt.xlabel("samples")
        plt.ylabel("normalized\namplitude")
        plt.plot(self.PROFILE_MEAN_TRACE)

        plt.subplot(num_plots, 1, 2)
        plt.xlabel("samples")
        plt.ylabel("r")
        for i, snr in enumerate(informative):
            plt.plot(snr, label="subkey %d"%i)
        for bnum in range(Profile.NUM_KEY_BYTES):
            plt.plot(self.POIS[bnum], informative[bnum][self.POIS[bnum]], '*')

        plt.legend()
        if SAVE_IMAGES:
            # NOTE: Fix savefig() layout.
            figure = plt.gcf() # Get current figure
            figure.set_size_inches(32, 18) # Set figure's size manually to your full screen (32x18).
            plt.savefig(path.join(template_dir,'pois.pdf'), bbox_inches='tight', dpi=100)
        if PLOT:
            plt.show()
        plt.clf()

class ProfileComparator():
    def __init__(self, profile1, profile2):
        self.profile_list = [profile1, profile2]

    def plot(self):
        global SAVE_IMAGES, PLOT
        libplot.enable_latex_fonts()
        num_plots = 4
        plt.subplots_adjust(hspace = 1)
        for idx, profile in enumerate(self.profile_list):
            informative = profile.PROFILE_RS
            plt.subplot(num_plots, 1, 1 + idx * 2)
            plt.xlabel("Samples")
            plt.ylabel("Normalized\namplitude")
            plt.plot(profile.PROFILE_MEAN_TRACE)

            plt.subplot(num_plots, 1, 2 + idx * 2)
            plt.xlabel("Samples")
            plt.ylabel("$\\rho$")
            for i, snr in enumerate(informative):
                plt.plot(snr, label="subkey %d"%i)
            # for bnum in range(Profile.NUM_KEY_BYTES):
            #     plt.plot(profile.POIS[bnum], informative[bnum][profile.POIS[bnum]], '*')

        if SAVE_IMAGES:
            # NOTE: Fix savefig() layout.
            figure = plt.gcf() # Get current figure
            figure.set_size_inches(12, 9) # Set figure's size manually to your full screen (32x18).
            plt.savefig(path.join(SAVE_IMAGES_PATH,'pois.pdf'), bbox_inches='tight', dpi=100)
        if PLOT:
            plt.show()
        plt.clf()        

if __name__ == "__main__":
    comparator = ProfileComparator(Profile(TEMPLATE_DIR_1), Profile(TEMPLATE_DIR_2))
    comparator.plot()
