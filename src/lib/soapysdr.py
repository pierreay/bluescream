"""Implement SDR classes using SoapySDR. Allows to use a single or multiple
SDRs in parallel using threads."""

import time
import numpy as np
from threading import Thread
import SoapySDR

import lib.log as l
import lib.load as load

class MySoapySDRs():
    def __init__(self):
        l.LOGGER.debug("MySoapySDRs.__init__()")
        self.sdrs = []

    def register(self, sdr):
        l.LOGGER.debug("MySoapySDRs.register(idx={})".format(sdr.idx))
        self.sdrs.append(sdr)
        # Temporary hack to be compatible with nrf52_whad.py who access
        # self.radio.fs variable. This imply to have the same sampling rate
        # accross two SDRs.
        self.fs = sdr.fs

    def open(self):
        l.LOGGER.debug("MySoapySDRs.open()")
        for sdr in self.sdrs:
            sdr.open()

    def close(self):
        l.LOGGER.debug("MySoapySDRs.close()")
        for sdr in self.sdrs:
            sdr.close()

    def record(self, N):
        l.LOGGER.debug("MySoapySDRs.record(N={}).enter".format(N))
        thr = [None] * len(self.sdrs)
        for sdr in self.sdrs:
            thr[sdr.idx] = Thread(target=sdr.record, args=(N,))
            thr[sdr.idx].start()
        for sdr in self.sdrs:
            thr[sdr.idx].join()
        l.LOGGER.debug("MySoapySDRs.record(N={}).exit".format(N))

    def accept(self):
        l.LOGGER.debug("MySoapySDRs.accept()")
        for sdr in self.sdrs:
            sdr.accept()

    def save(self, dir):
        l.LOGGER.debug("MySoapySDRs.save(dir={})".format(dir))
        for sdr in self.sdrs:
            sdr.save(dir)

class MySoapySDR():
    def __init__(self, fs, freq, idx = 0, enabled = True):
        l.LOGGER.debug("MySoapySDR.__init__(fs={},freq={},idx={})".format(fs, freq, idx))
        self.fs = fs
        self.freq = freq
        self.idx = idx
        self.enabled = enabled
        if self.enabled:
            results = SoapySDR.Device.enumerate()
            self.sdr = SoapySDR.Device(results[idx])
            self.sdr.setSampleRate(SoapySDR.SOAPY_SDR_RX, 0, fs)
            self.sdr.setFrequency(SoapySDR.SOAPY_SDR_RX, 0, freq)
            self.sdr.setGain(SoapySDR.SOAPY_SDR_RX, 0, 76)
            self.sdr.setAntenna(SoapySDR.SOAPY_SDR_RX, 0, "TX/RX")

    def open(self):
        if self.enabled:
            l.LOGGER.debug("MySoapySDR(idx={}).open()".format(self.idx))
            self.rx_stream = self.sdr.setupStream(SoapySDR.SOAPY_SDR_RX, SoapySDR.SOAPY_SDR_CF32)
            self.sdr.activateStream(self.rx_stream)
            self.rx_signal = np.array([0], np.complex64)

    def close(self):
        if self.enabled:
            l.LOGGER.debug("MySoapySDR(idx={}).close().enter".format(self.idx))
            self.sdr.deactivateStream(self.rx_stream)
            self.sdr.closeStream(self.rx_stream)
            l.LOGGER.debug("MySoapySDR(idx={}).close().leave".format(self.idx))

    def record(self, N):
        if self.enabled:
            l.LOGGER.debug("MySoapySDR(idx={}).record(N={:e}).enter".format(self.idx, N))
            N = int(N) # Required when N is specified using scientific notation.
            rx_buff_len = pow(2, 24)
            rx_buff = np.array([0] * rx_buff_len, np.complex64)
            self.rx_signal_candidate = np.array([0], np.complex64)
            while len(self.rx_signal_candidate) < N:
                sr = self.sdr.readStream(self.rx_stream, [rx_buff], rx_buff_len, timeoutUs=10000000)
                if sr.ret == rx_buff_len and sr.flags == 1 << 2:
                    self.rx_signal_candidate = np.concatenate((self.rx_signal_candidate, rx_buff))
            l.LOGGER.debug("MySoapySDR(idx={}).record().leave".format(self.idx))
        else:
            time.sleep(N/1e7)

    def accept(self):
        if self.enabled:
             l.LOGGER.debug("MySoapySDR(idx={}).accept()".format(self.idx))
             self.rx_signal = np.concatenate((self.rx_signal, self.rx_signal_candidate))

    def save(self, dir, abs = False):
        if self.enabled:
            l.LOGGER.debug("MySoapySDR(idx={}).save(dir={},abs={})".format(self.idx, dir, abs))
            load.save_raw_trace(self.rx_signal if not abs else np.abs(self.rx_signal), dir, self.idx, 0)
