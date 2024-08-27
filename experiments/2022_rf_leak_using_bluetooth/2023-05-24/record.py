#!/usr/bin/python3

import os
from contextlib import nullcontext

import numpy as np

from screamingchannels import analyze
from screamingchannels import radio
from screamingchannels import config
from screamingchannels import device
from screamingchannels import log as l

RET_EXIT_AND_RESUME = 3

if __name__ == "__main__":
    cli_config = config.CliConfig(device_baudrate=115200,
                                  device_serial=os.getenv("TARGET_ADDR"),
                                  radio=radio.RadioType.USRP,
                                  radio_address="",
                                  radio_antenna="TX/RX",
                                  radio_frontend="",
                                  outfile="/tmp/gr_sink",
                                  loglevel="DEBUG",
                                  logfile="",
                                  ykush_port=0,
                                  ykush_serial="")

    collection_config = config.CollectionConfig(num_points=1,
                                                num_traces_per_point=3)

    radio_config = config.RadioConfig(target_freq=127e6,
                                      sampling_rate=30e6,
                                      usrp_gain=76)

    preprocess_config = config.PreprocessConfig(drop_start=3.05e-1,
                                                drop_end=3.8e-2)

    postprocess_config = config.PostprocessConfig(trigger_bandpass_lower=8.2e6,
                                                  trigger_bandpass_upper=9.2e6,
                                                  trigger_lowpass=1e4,
                                                  trigger_threshold=0.7,
                                                  trigger_length=1.4e-4,
                                                  trigger_skip=0,
                                                  trace_offset=-5.4e-5,
                                                  trace_length=3e-4,
                                                  template_autocorr_ratio=0.93,
                                                  template_name="template.npy")

    file_config = config.FileConfig(collection_config, radio_config, preprocess_config, postprocess_config)

    device_config = {"type": "NRF52_WHAD",
                     "fixed_plaintext": False,
                     "ltk_path": "/tmp/mirage_output_ltk",
                     "addr_path": "/tmp/mirage_output_addr",
                     "rand_path": "/tmp/mirage_output_rand",
                     "ediv_path": "/tmp/mirage_output_ediv"
                     }

    outpath = "/tmp"
    plot = True
    plot_out = ""
    template_out = "template.npy"
    explore = False
    resume = False
    resume_nb = 0

    l.init(cli_config.logfile, cli_config.loglevel)

    rad = radio.GNURadio(cli_config.outfile,                resume, resume_nb,
                         cli_config.radio,                  cli_config.radio_address,
                         cli_config.radio_antenna,          cli_config.radio_frontend,
                         file_config.radio.target_freq,     file_config.radio.sampling_rate,
                         file_config.radio.usrp_gain,       file_config.radio.hackrf_gain,
                         file_config.radio.hackrf_gain_if,  file_config.radio.hackrf_gain_bb,
                         file_config.radio.plutosdr_gain,   file_config)

    with device.Device.create(device_config, baud=cli_config.device_baudrate, ser=cli_config.device_serial) as dev:
        dev.generate(num=file_config.collection.num_points, path=outpath)
        dev.init(rep=file_config.collection.num_traces_per_point)
        dev.radio = rad

        for idx in list(range(file_config.collection.num_points)):
            dev.configure(idx)
            try:
                dev.execute()
            except OSError as e:
                l.log_n_exit(e, e.strerror, RET_EXIT_AND_RESUME, traceback=True)
            dev.reset()

            concat_fns = rad.concat(file_config.collection.num_traces_per_point)
            rad.reset()
