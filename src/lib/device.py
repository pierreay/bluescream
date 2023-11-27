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
import lib.dataset as dataset
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
LL_ENC_REQ_CONN_EVENT = 3
HOP_INTERVAL = 56
# Channel map of 0x300 => channels 8-9 => frequencies 2.420 GHz and 2.422 GHz.
CHANNEL_MAP = 0x00000300
PROCEDURE_INTERLEAVING = False

# * Classes

class Device():
    # Timeout limit used for the loops of this module [s].
    TIMEOUT = 30

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def __init__(self, ser_port, baud, bd_addr_src, bd_addr_dest, radio, dataset, subset):
        self.ser_port = ser_port
        self.baud = baud
        self.bd_addr_src = bd_addr_src
        self.bd_addr_dest = bd_addr_dest
        self.radio = radio
        self.dataset = dataset
        self.subset = subset
        l.LOGGER.info("Instantiate WHAD's central with uart0's dongle")
        try:
            self.central = Central(WhadDevice.create('uart0'))
        except Exception as e:
             # Because WHAD exceptions doesn't have descriptions, only names
             # accessible through __repr__().
            raise Exception("{}".format(e.__repr__()))
        l.LOGGER.info("Spoof bluetooth address: {}".format(self.bd_addr_src))
        self.central.set_bd_address(self.bd_addr_src)
        self.time_start = time()
        self.time_elapsed = 0

    def timeouted(self, raise_exc=False):
        """Return True if timeout is exceeded with RAISE_EXC set to False, or
        raise an Exception with RAISE_EXC set to True.

        """
        self.time_elapsed = time() - self.time_start
        timeouted = self.time_elapsed >= Device.TIMEOUT
        if timeouted is True and raise_exc is True:
            raise Exception("timeout of {}s is exceeded!".format(Device.TIMEOUT))
        else:
            return timeouted

    def configure(self, idx):
        l.LOGGER.info("Configure device for recording index #{}".format(idx))
        # Choose index for key.
        # RAND and EDIV values are hardcoded twice, here and in our custom
        # firmware inside input.c.
        self.configure_ser(k=self.subset.get_current_ks(idx), p=self.subset.get_current_pt(idx))
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
            l.LOGGER.info("Send {}={}".format(input_type, input))
            write_to_ser(ser, "{}:{}".format(input_type, input))

        def write_to_ser(ser, cmd):
            """Write the command CMD to the serial port SER for our custom
            firmware.

            """
            # NOTE: Needs to convert the string to bytes using .encode().
            # NOTE: Needs "\n\n" at the end to actually sends the command.
            l.LOGGER.debug("ser <- {}".format(cmd))
            ser.write("{}\n\n".format(cmd).encode())
            sleep(0.1)

        l.LOGGER.info("Send p and k on serial port...")
        # Configure the input of our custom firmware using serial port.
        with serial.Serial(self.ser_port, self.baud) as ser:
            # Convert dataset to input for firmware over serial port and send it.
            write_input_to_ser(ser, utils.npy_int_to_str_hex(k), "k")
            write_input_to_ser(ser, utils.npy_int_to_str_hex(p), "p")
            sub_input_to_ser(ser)
            write_to_ser(ser, "input_dump") # NOTE: Keep it here because otherwise sub_input is not sent properly.

    def execute(self):
        l.LOGGER.debug("Start preparing WHAD's sequences...")
        # At specified connection event, send an empty packet, used to
        # inform the radio to start recording at a precise connection
        # event.
        l.LOGGER.info("Connection event for starting the recording: {}".format(START_RADIO_CONN_EVENT))
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
        l.LOGGER.info("Connection event for sending the LL_ENC_REQ request: {}".format(LL_ENC_REQ_CONN_EVENT))
        trgr_send_ll_enc_req = ConnectionEventTrigger(LL_ENC_REQ_CONN_EVENT)
        l.LOGGER.info("Procedure interleaving enabled: {}".format(PROCEDURE_INTERLEAVING))
        if PROCEDURE_INTERLEAVING:
            l.LOGGER.debug("More Data Bit=1")
            self.central.prepare(
                BTLE_DATA()     / L2CAP_Hdr() / ATT_Hdr() / ATT_Read_Request(gatt_handle=3),
                BTLE_DATA(MD=1) / BTLE_CTRL() / LL_ENC_REQ(rand=self.rand, ediv=self.ediv, skdm=self.skdm, ivm=self.ivm),
                trigger=trgr_send_ll_enc_req
            )
            l.LOGGER.debug("nRF52_WHAD.central.prepare(ATT_Read_Request[gatt_handle=3]")
        else:
            l.LOGGER.debug("More Data Bit=0")
            self.central.prepare(
                BTLE_DATA() / BTLE_CTRL() / LL_ENC_REQ(rand=self.rand, ediv=self.ediv, skdm=self.skdm, ivm=self.ivm),
                trigger=trgr_send_ll_enc_req
            )
        l.LOGGER.debug("central.prepare(LL_ENC_REQ[rand=0x{:x}, ediv=0x{:x}, skdm=0x{:x}, ivm=0x{:x}])".format(self.rand, self.ediv, self.skdm, self.ivm))

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
        l.LOGGER.info("Connect to target device...")
        l.LOGGER.debug("Connection parameters: address={}, random=False, hop_interval={}, channel_map=0x{:x}, timeout={}".format(self.bd_addr_dest, HOP_INTERVAL, CHANNEL_MAP, self.TIMEOUT))
        device = self.central.connect(self.bd_addr_dest, random=False, hop_interval=HOP_INTERVAL, channel_map=CHANNEL_MAP, timeout=self.TIMEOUT)

        if self.central.is_connected():
            l.LOGGER.debug("WHAD's central is connected to target device!")
            # Wait until the connection event we should start the radio.
            while not self.timeouted(raise_exc=True) and not trgr_start_radio.triggered:
                pass
            # The radio has been started too late if LL_START_ENC_REQ is
            # already received.
            if trgr_recv_ll_start_enc_req.triggered:
                raise Exception("The recording hasn't been started while we received the encryption confirmation!")
            # Start the recording and wait for it to complete.
            self.radio.record()
            # The recording isn't likely to contain the AES since we didn't
            # received an LL_START_ENC_REQ. The recording is maybe happening
            # too soon.
            if not trgr_recv_ll_start_enc_req.triggered:
                raise Exception("The recording is already finished while we didn't received the encryption confirmation!")
            else:
                self.radio.accept()
                
            l.LOGGER.info("Disconnect from the target device")
            device.disconnect()
        else:
            raise Exception("Cannot connect to target device!")
        if trgr_recv_ll_reject_ind.triggered:
            raise Exception("LL_REJECT_IND packet received, LL_ENC_REQ request's parameters were not accepted!")

        # Manually delete every previsouly created sequences. It fix a bug
        # in WHAD where sequences should be deleted automatically, but they
        # are not.
        # NOTE: As of [2023-11-07 mar.], deprecate this code snippet as it was
        #       generating a hang from WHAD infinitely waiting a message from
        #       Butterfly, and it seems it is not necessary anymore since WHAD
        #       is only used once per trace.
        # l.LOGGER.debug("delete prepared sequence of whad's central")
        # self.central.delete_sequence(trgr_start_radio)
        # self.central.delete_sequence(trgr_send_ll_enc_req)
        # self.central.delete_sequence(trgr_recv_ll_start_enc_req)
        # self.central.delete_sequence(trgr_recv_ll_reject_ind)

    def close(self):
        if self.central is not None:
            l.LOGGER.debug("Stop and close WHAD's central")
            self.central.stop()
            self.central.close()
            self.central = None
