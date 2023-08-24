"""Generalize target devices into abstract classes and load specific classes for known targets.

Each class is a combination of a target device (e.g. nRF52, nRF24) and the
instrumentation method (e.g. custom firmware, external tool like WHAD).

Classes:

        DeviceType: Enumeration of all supported target devices.
        Device: General target device.

Functions:

        ykush_reset: Reset a device through Ykush USB hub.

"""
# Core modules.
import enum
import dataclasses
import subprocess as sp
import time

# Local modules.
import lib.log as l

# WARNING: Numbers must match with "classes" variable in "Device.get()".
DeviceType = enum.Enum("DeviceType", {"GENERIC": 0, "NRF52_WHAD": 1})

class Device():
    """Abstract class of a target device.

    Specialized classes for known target devices should inherit of this one.

    Methods:

        create: Given a DeviceType, initialize a target device with the given
                configuration, ready to connect to it.
        connect: Connect to the device ready to configure it.
        init: Initialize the device ready to record traces.
        configure: Configure the target device for current recording.
        execute: Perform encryption and communication.
        close: Disconnect from the device.

    """
    @dataclasses.dataclass
    class DeviceConfig:
        """General class of device's configuration.

        The structure of this DataClass should correspond to the "device"
        section of the JSON configuration file. It can be overrode in each
        specialized class, or let it empty if no additional configuration field
        is needed.

        Parameters
        ----------
        ```conf
        type: Identifier of target device.
        ```

        """
        type: DeviceType

    @classmethod
    def create(cls, devconfig, **kwargs):
        """Create the requested target device.

        Class-method that will return an instantiated target device based on
        the type.

        :param type: DeviceType enumeration of type of target device.
        :param devconfig: Dictionnary of the "device" section in configuration file.
        :param **kwargs: Dictionnary of additionnal device parameters used by specialized classes.
        :returns: Object inherited from Device.

        """
        try:
            # Get class DeviceConfig parameters out of devconfig because they
            # are not included in per-device DeviceConfig dataclasses.
            l.LOGGER.debug("Initialize device of type='{}'".format(devconfig["type"]))
            cls_devconfig = cls.DeviceConfig(devconfig.pop("type"))
            dev = cls.get(cls_devconfig.type)
        except KeyError as e:
            l.LOGGER.critical("Can't find 'type' key in 'device' section of configuration file")
        else:
            return dev(devconfig, type=cls_devconfig.type, **kwargs)
        exit(1) # If critical exception occurs.

    @classmethod
    def get(cls, type):
        """Get the class corresponding to the type of target device.

        :param type: DeviceType enumeration of type of target device.
        :returns: Class inherited from Device.
        :raises Exception: If type is not supported.

        """
        # Defered imports to avoid circular dependencies.
        import lib.nrf52_whad as nrf52_whad
        classes = [Device, nrf52_whad.nRF52_WHAD]
        try:
            return classes[DeviceType[type].value]
        except KeyError as e:
            raise Exception("Unsupported device type: {}".format(type))

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args):
        self.close()

    def __init__(self, devconfig, type, **kwargs):
        """Initialize variables of the target device.

        For all devices, the type of device and the configuration file is
        loaded into the object with the appropriate DataClass. Other needed
        actions are set per-classes.

        :param devconfig: Dictionnary of the "device" section in configuration file.
        :param **kwargs: Dictionnary of additionnal device parameters used by specialized classes.

        """
        try:
            self.type = DeviceType[type]
            self.config = self.DeviceConfig(**devconfig)
        except TypeError as e:
            l.LOGGER.critical("{}. Bad configuration file format for 'device' section".format(e))
            exit(1)

    def connect(self):
        """Connect to the target device.

        Establish communication (e.g. serial, socket, network) with the target
        device.

        """
        raise NotImplementedError("Please, override this function in a specialized class")

    def generate(self, num, path):
        """Generate needed data (plaintexts, keys) and save them.

        Generate all data that the device needs to perform encryptions (keys
        and plaintext) and communication (protocol-specific). Save those data
        into files under the specified directory.

        :param num: Number of final traces that we want, i.e. number of trigger commands to send.
        :type num: int
        :param path: Path to the directory where to save generated data
        :type path: str

        """
        raise NotImplementedError("Please, override this function in a specialized class")

    def init(self, rep):
        """Initialize the target device.

        Configure the target device once with requested parameters and put it
        in a mode ready to perform encryption and transmisson at the same time.

        :param rep: [Integer] Number of encryption that should be performed at each trigger command.

        """
        raise NotImplementedError("Please, override this function in a specialized class")

    def configure(self, idx):
        """Configure the target device for current recording.

        Configure the target device with the requested parameters before each
        radio recording.

        :param idx: Index of current execution (used for index plaintexts and keys).
        :type idx: int

        """
        raise NotImplementedError("Please, override this function in a specialized class")

    def execute(self):
        """Perform encryption and communication.

        Execute the required commands to perform encryption with targeted
        secret key and communication at the same time.

        """
        raise NotImplementedError("Please, override this function in a specialized class")

    def reset(self):
        """"Executed between a collect and a trace post-processing."""
        raise NotImplementedError("Please, override this function in a specialized class")

    def close(self):
        """Disconnect to the target device.

        Close communication (e.g. serial, socket, network) with the target
        device and clean up acquired ressources.

        """
        raise NotImplementedError("Please, override this function in a specialized class")
