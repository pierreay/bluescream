# Core modules.
import enum
import dataclasses
import re
from time import sleep, time
import random
import os
import struct
import serial

# Local modules.
import lib.utils as utils
import lib.device as device
import lib.log as l

# External modules.
try:
    from scapy.all import BTLE_DATA, BTLE_ADV, ATT_Hdr, L2CAP_Hdr, ATT_Read_Request, BTLE_EMPTY_PDU, BTLE_CTRL, LL_ENC_REQ, LL_START_ENC_REQ, LL_REJECT_IND
    import whad
    from whad.ble import Central, ConnectionEventTrigger, ReceptionTrigger
    from whad.ble.profile import UUID
    from whad.ble.stack.llm import START_ENC_REQ, REJECT_IND
    from whad.device import WhadDevice
except ImportError as e: # Don't make these modules mandatory for running all the app.
    l.LOGGER.error("Can't import WHAD! Error: {}".format(e))

# * Globals

START_RADIO_CONN_EVENT = 1
LL_ENC_REQ_CONN_EVENT = 27
HOP_INTERVAL = 56
# Channel map of 0x300 => channels 8-9 => frequencies 2.420 GHz and 2.422 GHz.
CHANNEL_MAP = 0x00000300
PROCEDURE_INTERLEAVING = False

# * Classes

class Device():
    # Counters for interesting packets.
    cnt_send_hci_create_connection = 0
    cnt_recv_ll_start_enc_req      = 0
    cnt_total_time                 = 0
    # Number of fail limits.
    fail_lim = 4
    # Timeout for a connection [s].
    timeout = 4
    # The "self.bd_addr_spoof" value is hardcoded twice, here and in our
    # custom firmware inside input.c.
    bd_addr_spoof = "00:19:0E:19:79:D8"

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def __init__(self, ser_port, baud, bd_addr, radio, dataset, subset):
        self.ser_port = ser_port
        self.baud = baud
        self.bd_addr = bd_addr
        self.radio = radio
        self.dataset = dataset
        self.subset = subset
        l.LOGGER.info("instantiate whad's central with uart0's dongle")
        try:
            self.central = Central(WhadDevice.create('uart0'))
        except Exception as e:
             # Because WHAD exceptions doesn't have descriptions, only names
             # accessible through __repr__().
            raise Exception("{}".format(e.__repr__()))
        l.LOGGER.info("spoof bluetooth address: {}".format(self.bd_addr_spoof))
        self.central.set_bd_address(self.bd_addr_spoof)

    def configure(self, idx):
        l.LOGGER.info("configure device for recording index #{}".format(idx))
        self.configure_ser(k=self.subset.ks[idx], p=self.subset.pt[idx])
        # RAND and EDIV values are hardcoded twice, here and in our custom
        # firmware inside input.c.
        self.rand = 0xdeadbeefdeadbeef
        self.ediv = 0xdead
        # SKD_M can be kept set to 0 since we submitted a plaintext for our
        # custom firmware.
        self.skdm = 0x00000000
        # IVM can be kept set to 0 since it will only be used after the session
        # key derivation (hence, after our recording and our instrumentation).
        self.ivm  = 0x00000000

    def configure_ser(self, k, p):
        def sub_input_to_ser(ser):
            """Submit input to the Nimble security database of our custom firmware."""
            write_to_ser(ser, "input_sub")

        def write_input_to_ser(ser, input, input_type):
            """Write an input (a key or a plaintext) INPUT represented by a string
            containing an hexidecimal number to the serial port. INPUT_TYPE can be
            set to 'p' or 'k'.

            """
            assert(type(input) == str)
            assert(input_type == "k" or input_type == "p")
            l.LOGGER.info("send {}={}".format(input_type, input))
            write_to_ser(ser, "{}:{}".format(input_type, input))

        def write_to_ser(ser, cmd):
            """Write the command CMD to the serial port SER for our custom
            firmware.

            """
            # NOTE: Needs to convert the string to bytes using .encode().
            # NOTE: Needs "\n\n" at the end to actually sends the command.
            l.LOGGER.debug("ser <- {}".format(cmd))
            ser.write("{}\n\n".format(cmd).encode())

        l.LOGGER.info("send p and k on serial port")
        # Configure the input of our custom firmware using serial port.
        with serial.Serial(self.ser_port, self.baud) as ser:
            # Convert dataset to input for firmware over serial port and send it.
            write_input_to_ser(ser, utils.npy_int_to_str_hex(k), "k")
            write_input_to_ser(ser, utils.npy_int_to_str_hex(p), "p")
            sub_input_to_ser(ser)

    def execute(self):
        # Keep trace of number of failed connections.
        fail = 0
        while self.cnt_recv_ll_start_enc_req < 1:
            # Check that most consecutive connections are ok.
            if fail > self.fail_lim:
                raise OSError(3, "More than {} consecutive failed conection, quit the instrumentation!".format(self.fail_lim))
            l.LOGGER.debug("nRF52_WHAD.cnt_send_hci_create_connection={}".format(self.cnt_send_hci_create_connection))

            # At specified connection event, send an empty packet, used to
            # inform the radio to start recording at a precise connection
            # event.
            l.LOGGER.info("START_RADIO_CONN_EVENT = {}".format(START_RADIO_CONN_EVENT))
            trgr_start_radio = ConnectionEventTrigger(START_RADIO_CONN_EVENT)
            self.central.prepare(
                BTLE_DATA() / BTLE_EMPTY_PDU(),
                trigger=trgr_start_radio
            )

            # At specified connection event, send the ATT_Read_Requests and the
            # LL_ENC_REQ. (MD=1) force the ATT_Read_Response to be on the same
            # connection event as the ENC_RSP, excepting to have the
            # ATT_Read_Response during AES processing. If you set the MD bit
            # before, the connection events will be separated.
            l.LOGGER.info("LL_ENC_REQ_CONN_EVENT = {}".format(LL_ENC_REQ_CONN_EVENT))
            trgr_send_ll_enc_req = ConnectionEventTrigger(LL_ENC_REQ_CONN_EVENT)
            l.LOGGER.info("PROCEDURE_INTERLEAVING={}".format(PROCEDURE_INTERLEAVING))
            if PROCEDURE_INTERLEAVING:
                l.LOGGER.info("MD=1")
                self.central.prepare(
                    BTLE_DATA()     / L2CAP_Hdr() / ATT_Hdr() / ATT_Read_Request(gatt_handle=3),
                    BTLE_DATA(MD=1) / BTLE_CTRL() / LL_ENC_REQ(rand=self.rand, ediv=self.ediv, skdm=self.skdm, ivm=self.ivm),
                    trigger=trgr_send_ll_enc_req
                )
                l.LOGGER.debug("nRF52_WHAD.central.prepare(ATT_Read_Request[gatt_handle=3]")
            else:
                l.LOGGER.info("MD=0")
                self.central.prepare(
                    BTLE_DATA() / BTLE_CTRL() / LL_ENC_REQ(rand=self.rand, ediv=self.ediv, skdm=self.skdm, ivm=self.ivm),
                    trigger=trgr_send_ll_enc_req
                )
            l.LOGGER.debug("nRF52_WHAD.central.prepare(LL_ENC_REQ[rand=0x{:x}, ediv=0x{:x}, skdm=0x{:x}, ivm=0x{:x}])".format(self.rand, self.ediv, self.skdm, self.ivm))

            # When receiveing a LL_START_ENC_REQ packet, send an empty packet,
            # used to count the number of successful link encryption to know
            # how many trace we should have captured.
            trgr_recv_ll_start_enc_req = ReceptionTrigger(
                packet=BTLE_DATA() / BTLE_CTRL() / LL_START_ENC_REQ(),
                selected_fields=("opcode")
            )
            self.central.prepare(
                BTLE_DATA() / BTLE_EMPTY_PDU(),
                trigger=trgr_recv_ll_start_enc_req
            )

            # If receiveing a LL_REJECT_IND packet, send an empty packet. The
            # goal here is just to know that we have to raise an error, meaning
            # that EDIV/RAND/BD_ADDR aren't correct and that legitimate
            # connection sniffing needs to be redone.
            trgr_recv_ll_reject_ind = ReceptionTrigger(
                packet=BTLE_DATA() / BTLE_CTRL() / LL_REJECT_IND(),
                selected_fields=("opcode")
            )
            self.central.prepare(
                BTLE_DATA() / BTLE_EMPTY_PDU(),
                trigger=trgr_recv_ll_reject_ind
            )

            # Connect to the peripheral. The parameters are:
            # 1. Use increased hop interval. Decreasing it speed-up the connection.
            # 2. Set channel map to 0x300 which corresponds to channel 8-9.
            l.LOGGER.debug("nRF52_WHAD.central.connect(address={}, random=False, hop_interval={}, channel_map=0x{:x})".format(self.bd_addr, HOP_INTERVAL, CHANNEL_MAP))
            device = self.central.connect(self.bd_addr, random=False, hop_interval=HOP_INTERVAL, channel_map=CHANNEL_MAP)

            # Connection can be lost because of firmware bugs, interferances, or because
            # our packets are not legitimate. If so, just retry a connect.
            time_start = time()
            time_elapsed = 0
            if self.central.is_connected():
                while not trgr_recv_ll_start_enc_req.triggered and time_elapsed < self.timeout:
                    time_elapsed = time() - time_start
                    while not trgr_start_radio.triggered:
                        pass
                    if trgr_recv_ll_start_enc_req.triggered:
                        l.LOGGER.error("Not executed `nRF52_WHAD.radio.record()` with `nRF52_WHAD.trgr_recv_ll_start_enc_req.triggered` to True")
                    self.radio.record()
                    if not trgr_recv_ll_start_enc_req.triggered:
                        l.LOGGER.error("Returned `nRF52_WHAD.radio.record()` without `nRF52_WHAD.trgr_recv_ll_start_enc_req.triggered` to True")
                    else:
                        self.cnt_recv_ll_start_enc_req += 1
                        self.radio.accept()
            else:
                l.LOGGER.warning("nRF52_WHAD.central.is_connected()=False")
            if trgr_recv_ll_reject_ind.triggered:
                raise Exception("LL_REJECT_IND received! Encryption request's parameters needs to be updated!")

            l.LOGGER.debug("nRF52_WHAD.device.disconnect()")
            device.disconnect()

            success = trgr_recv_ll_start_enc_req.triggered and time_elapsed < self.timeout
            if not success:
                l.LOGGER.warning("not nRF52_WHAD.trgr_recv_ll_start_enc_req.triggered and time_elapsed < nRF52_WHAD.timeout")
                fail += 1
                if time_elapsed >= self.timeout:
                    l.LOGGER.warning("time_elapsed >= nRF52_WHAD.timeout")
            if success:
                fail = 0

            self.cnt_send_hci_create_connection += 1
            self.cnt_total_time += time_elapsed

            # Manually delete every previsouly created sequences. It fix a bug
            # in WHAD where sequences should be deleted automatically, but they
            # are not.
            self.central.delete_sequence(trgr_start_radio)
            self.central.delete_sequence(trgr_send_ll_enc_req)
            self.central.delete_sequence(trgr_recv_ll_start_enc_req)
            self.central.delete_sequence(trgr_recv_ll_reject_ind)
            sleep(0.2) # Insert a small delay between two subsequent connections.

    def reset(self):
        if self.central is not None:
            l.LOGGER.debug("destroy whad's central")
            self.central.stop()
            self.central.close()
            self.central = None

    def close(self):
        self.reset()
