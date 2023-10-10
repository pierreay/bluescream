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
    # Define counters for interesting packets.
    cnt_send_hci_create_connection = 0
    cnt_recv_ll_start_enc_req      = 0
    cnt_total_time                 = 0

    # Define limits.
    fail_lim = 4

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def __init__(self, ser_port, baud, bd_addr,
                 ltk_path, addr_path, rand_path, ediv_path, radio):
        self.central = None # Will be set in `self.configure()`.
        # We need Bluetooth communication, register the BD_ADDR.
        self.ser_port = ser_port
        self.baud = baud
        self.bd_addr = bd_addr
        # The "self.bd_addr_spoof" value is hardcoded twice, here and in our
        # custom firmware inside input.c.
        self.bd_addr_spoof = "00:19:0E:19:79:D8"
        self.ltk_path = ltk_path
        self.addr_path = addr_path
        self.rand_path = rand_path
        self.ediv_path = ediv_path
        self.radio = radio
        # Timeout for a connection [s].
        self.timeout = 4
        l.LOGGER.debug("Register nRF52 with BD_ADDR='{}'".format(self.bd_addr))

    def configure_input(self):
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

        l.LOGGER.info("send p and k on serial port...")
        # TODO: The input values sould be provided by dataset.
        k = utils.str_hex_to_npy_int("deadbeefdeadbeefbeefdeadbeefdead")
        p = utils.str_hex_to_npy_int("beefdeadbeefdeaddeadbeefdeadbeef")
        # Convert dataset to input for firmware over serial port.
        k = utils.npy_int_to_str_hex(k)
        p = utils.npy_int_to_str_hex(p)
        # TODO: Register EDIV and RAND to use them during connection.
        ediv = 0xdead
        rand = 0xdeadbeefdeadbeef
        # Configure the input of our custom firmware using serial port.
        # TODO: Set the serial port from the command line.
        with serial.Serial('/dev/ttyACM1', 115200) as ser:
            write_input_to_ser(ser, k, "k")
            write_input_to_ser(ser, p, "p")
            sub_input_to_ser(ser)
        l.LOGGER.info("done!")

    def generate(self, num, path):
        # Generate or read needed parameters.
        bt_addr_path = self.addr_path
        bt_ltk_path  = self.ltk_path
        bt_rand_path = self.rand_path
        bt_ediv_path = self.ediv_path
        l.LOGGER.debug("Open BT_ADDR/LTK/RAND/EDIV files for reading: {} {} {} {}".format(bt_addr_path, bt_ltk_path, bt_rand_path, bt_ediv_path))
        try:
            with open(bt_addr_path, mode="r") as f:
                self.bd_addr_spoof = f.readline()[:-1]  # [:-1] to remove the \n character at the end.
            with open(bt_ltk_path,  mode="r") as f:
                self.ltk           = f.readline()[:-1]  # [:-1] to remove the \n character at the end.
            with open(bt_rand_path, mode="r") as f:
                self.rand          = f.readline()[:-1]  # [:-1] to remove the \n character at the end.
            with open(bt_ediv_path, mode="r") as f:
                self.ediv          = f.readline()[:-1]  # [:-1] to remove the \n character at the end.
        except Exception as e:
            l.log_n_exit(e, "Can't load the BD_ADDR|LTK|RAND|EDIV parameters from the pairing", 1)
        l.LOGGER.debug("Read BD_ADDR for spoofing: {}".format(self.bd_addr_spoof))
        l.LOGGER.debug("Read LTK for side-channel verification: {}".format(self.ltk))
        l.LOGGER.debug("Read RAND for LTK identification: {}".format(self.rand))
        l.LOGGER.debug("Read EDIV for LTK identification: {}".format(self.ediv))
        assert self.bd_addr_spoof, "Read BD_ADDR should not be None!"
        assert self.ltk,           "Read LTK should not be None!"
        assert self.rand,          "Read RAND should not be None!"
        assert self.ediv,          "Read EDIV should not be None!"
        if not re.match("^[A-Z0-9][A-Z0-9]:[A-Z0-9][A-Z0-9]:[A-Z0-9][A-Z0-9]:[A-Z0-9][A-Z0-9]:[A-Z0-9][A-Z0-9]:[A-Z0-9][A-Z0-9]$", self.bd_addr_spoof):
            raise Exception("Spoofing address is not correctly formatted! Expected format: XX:XX:XX:XX:XX:XX with X an uppercase hexadecimal digit")
        if not re.match("^[a-z0-9][a-z0-9][a-z0-9][a-z0-9][a-z0-9][a-z0-9][a-z0-9][a-z0-9][a-z0-9][a-z0-9][a-z0-9][a-z0-9][a-z0-9][a-z0-9][a-z0-9][a-z0-9][a-z0-9][a-z0-9][a-z0-9][a-z0-9][a-z0-9][a-z0-9][a-z0-9][a-z0-9][a-z0-9][a-z0-9][a-z0-9][a-z0-9][a-z0-9][a-z0-9][a-z0-9][a-z0-9]$", self.ltk):
            raise Exception("LTK is not correctly formatted! Expected format: XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX with X a lowercase hexadecimal digit")
        # Half part of the Known Plaintext (KP).
        npts = 1 if self.fixed_plaintext else num
        if npts == 1:
            # l.LOGGER.debug("Use fixed 0xdeadbeefdeadbeef SKD_M")
            # self.skdm = [0xdeadbeefdeadbeef]
            l.LOGGER.debug("Generate {} SKD_M (plaintext)".format(npts))
            self.skdm = [random.getrandbits(64) for _it in range(npts)]
        else:
            l.LOGGER.debug("Generate {} SKD_M (plaintext)".format(npts))
            self.skdm = [random.getrandbits(64) for _it in range(npts)]
        # Can be set to random value.
        self.ivm  = 0xdeadbeef

        # Save parameters inside output directory.
        try:
            l.LOGGER.debug("Open BT_ADDR/LTK/RAND/EDIV files for saving: {} {} {} {}".format("{}/bt_addr".format(path), "{}/bt_ltk".format(path), "{}/bt_rand".format(path), "{}/bt_ediv".format(path)))
            with open("{}/bt_addr".format(path), mode="w") as f:
                f.write("{}\n".format(self.bd_addr_spoof))
            with open("{}/bt_ltk".format(path),  mode="w") as f:
                f.write("{}\n".format(self.ltk))
            with open("{}/bt_rand".format(path), mode="w") as f:
                f.write("{}\n".format(self.rand))
            with open("{}/bt_ediv".format(path), mode="w") as f:
                f.write("{}\n".format(self.ediv))
        except Exception as e:
            l.log_n_exit(e, "Can't save the BD_ADDR|LTK|RAND|EDIV parameters from the pairing", 1)
        # Save path for saving only effectively used SKD while saving radio trace later.
        self.outpath = path

    def init(self, rep):
        l.LOGGER.info("Initialization")
        self.rep = rep

        # Check for address here and not in __init__ to correctly handle raised excpetion.
        if not re.match("^[A-Z0-9][A-Z0-9]:[A-Z0-9][A-Z0-9]:[A-Z0-9][A-Z0-9]:[A-Z0-9][A-Z0-9]:[A-Z0-9][A-Z0-9]:[A-Z0-9][A-Z0-9]$", self.bd_addr):
            raise Exception("Target address is not correctly formatted! Expected format: XX:XX:XX:XX:XX:XX with X an hexadecimal number")

        # Convert read EDIV and RAND to usable values. They have to be converted after the saving part.
        self.ediv = int(self.ediv, base=16)                                           # Convert from hex string (right-order) to integer.
        self.rand = struct.unpack('<Q',struct.pack('>Q', int(self.rand, base=16)))[0] # Convert from hex string (reverse-order) to integer.

        l.LOGGER.info("LTK         = 0x{}".format(self.ltk))
        l.LOGGER.info("RAND        = 0x{:x}".format(self.rand))
        l.LOGGER.info("EDIV        = 0x{:x}".format(self.ediv))
        l.LOGGER.info("SKD_M[0]    = 0x{:x}".format(self.skdm[0]))
        l.LOGGER.info("len(SKD_M)  = {}".format(len(self.skdm)))
        l.LOGGER.info("IV_M        = 0x{:x}".format(self.ivm))

    def configure(self, idx):
        l.LOGGER.debug("Create WHAD's Central with UART0's dongle")
        # Create central device.
        try:
            self.central = Central(WhadDevice.create('uart0'))
        except Exception as e:
            raise Exception("{}".format(e.__repr__())) # Because WHAD exceptions doesn't have descriptions, only names accessible through __repr__().
        # This has to be set to the Bluetooth adress of the HCI device used to
        # establish the pairing, since the tuple used for LTK identification is
        # (BD_ADDR, EDIV).
        l.LOGGER.info("BD_ADDR to spoof with the nRF52 dongle: {} ".format(self.bd_addr_spoof))
        self.central.set_bd_address(self.bd_addr_spoof)

        # Choose which SKDM has to be sent for this batch of recordings.
        self.skdm_choosen = self.skdm[0 if self.fixed_plaintext else idx]

        # Current final trace number used for saving the SKD.
        self.idx = idx

    def execute(self):
        assert hasattr(self, "rep") and self.rep > 0, "Bad repetition configuration"
        assert hasattr(self, "radio"), "Can't access to radio object"
        assert hasattr(self, "central"), "No initialized WHAD Central"
        assert hasattr(self, "ltk"), "No LTK found!"
        assert hasattr(self, "rand"), "No RAND found!"
        assert hasattr(self, "ediv"), "No EDIV found!"
        assert hasattr(self, "skdm"), "No SKDM found!"
        assert hasattr(self, "ivm"), "No IVM found!"

        # Keep trace of number of failed connections.
        fail = 0

        l.LOGGER.debug("while nRF52_WHAD.cnt_recv_ll_start_enc_req < nRF52_WHAD.rep={}".format(self.rep))
        while self.cnt_recv_ll_start_enc_req < self.rep:
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
                    BTLE_DATA(MD=1) / BTLE_CTRL() / LL_ENC_REQ(rand=self.rand, ediv=self.ediv, skdm=self.skdm_choosen, ivm=self.ivm),
                    trigger=trgr_send_ll_enc_req
                )
                l.LOGGER.debug("nRF52_WHAD.central.prepare(ATT_Read_Request[gatt_handle=3]")
            else:
                l.LOGGER.info("MD=0")
                self.central.prepare(
                    BTLE_DATA() / BTLE_CTRL() / LL_ENC_REQ(rand=self.rand, ediv=self.ediv, skdm=self.skdm_choosen, ivm=self.ivm),
                    trigger=trgr_send_ll_enc_req
                )
            l.LOGGER.debug("nRF52_WHAD.central.prepare(LL_ENC_REQ[rand=0x{:x}, ediv=0x{:x}, skdm=0x{:x}, ivm=0x{:x}])".format(self.rand, self.ediv, self.skdm_choosen, self.ivm))

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
                skds_path   = "/tmp/whad_skds"                                    # Read
                skd_path    = "{}/bt_skd_{}".format(self.outpath, str(self.idx))  # Write
                skds = 0
                with open(skds_path, mode="r") as f:
                    skds = int(f.readline()[:-1])
                skd = (skds << 64) | self.skdm_choosen
                l.LOGGER.debug("skdm: base10={} base16=0x{:x}".format(self.skdm_choosen, self.skdm_choosen))
                l.LOGGER.debug("skds: base10={} base16=0x{:x}".format(skds, skds))
                l.LOGGER.debug("skd: base10={} base16=0x{:x}".format(skd, skd))
                with open(skd_path, mode="w") as f:
                    l.LOGGER.info("Save SKD into {}".format(skd_path))
                    f.write("{}\n".format(skd))
            
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
        if self.central:
            l.LOGGER.debug("Destroy WHAD's Central")
            self.central.stop()
            self.central.close()
            self.central = None
            l.LOGGER.debug("self.cnt_send_hci_create_connection={}".format(self.cnt_send_hci_create_connection))
            l.LOGGER.debug("self.cnt_recv_ll_start_enc_req={}".format(self.cnt_recv_ll_start_enc_req))
            l.LOGGER.debug("self.cnt_total_time={:.2f}s".format(self.cnt_total_time))
        else:
            l.LOGGER.debug("WHAD central is not initialized, ignore reset command")

    def close(self):
        self.reset()
