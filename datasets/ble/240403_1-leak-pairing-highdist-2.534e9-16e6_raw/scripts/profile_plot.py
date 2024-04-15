#!/usr/bin/env python3

import sys
import matplotlib.pyplot as plt
import lib.dataset as dataset
import lib.plot as libplot

PROFILE_PATH=sys.argv[1]
OUTFILE_PDF=sys.argv[2]

prof = dataset.Profile(fp=PROFILE_PATH)
prof.load()
# TODO: Temporary disable until LaTeX is installed on the current host.
#libplot.enable_latex_fonts()
prof.plot(save=OUTFILE_PDF, plt_param_dict={"lw": "0.5"})
