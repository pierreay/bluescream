"""Mini-Circuits' RCDAT Python Wrapper

The RCDAT is a single-channel programmable attenuator controllable using USB
interrupts.

Using it introduce 9 to 10 dB of insertion loss.

References:

- Datasheet:
  https://www.minicircuits.com/pdfs/RCDAT-6000-110.pdf

- Code example from "Programming Examples and Troubleshooting" at page 25 /
  2.1.2 (g) - Multi-Channel Programmable Attenuators:
  https://www.minicircuits.com/softwaredownload/Prog_Examples_Troubleshooting.pdf

- Interrupts description in "Programmer Manual of Programmable Attenuator" page
  207 / 5 - USB Control via Direct Programming (Linux):
  https://www.minicircuits.com/softwaredownload/Prog_Manual-6-Programmable_Attenuator.pdf

Add the following udev rules to allow running this module without root
permissions:

$ sudo cat << EOF > /etc/udev/rules.d/01-minicircuits.rules
SUBSYSTEMS=="usb", ATTRS{idVendor}=="20ce", ATTRS{idProduct}=="0023", GROUP="users", MODE="0666"
EOF

"""

import usb.core
import usb.util

# NOTE: Allows to import "log" module using rcdat.py as a library or as a
# standalone.
try:
    import lib.log as l
except ModuleNotFoundError as e:
    try:
        import log as l
    except Exception as e:
        print(e)

class RCDAT():
    """Mini-Circuits RCDAT."""

    # USB-based device.
    dev = None

    # Identification numbers.
    serial_number = ""
    model_number = ""
    firmware_name = ""

    def __init__(self):
        """Instantiate a RCDAT attenuator over the USB bus.

        On error, raise a ValueError exception.

        """
        # Find our device.
        self.dev = usb.core.find(idVendor=0x20ce, idProduct=0x0023)
        if self.dev is None:
            raise ValueError('Device not found!')

        # Detach any active kernel driver to enable I/O.
        for configuration in self.dev:
            for interface in configuration:
                ifnum = interface.bInterfaceNumber
            if not self.dev.is_kernel_driver_active(ifnum):
                continue
            try:
                self.dev.detach_kernel_driver(ifnum)
            except (usb.core.USBError, e):
                pass

        # Enable the first found configuration.
        self.dev.set_configuration()
        # Get informations about device.
        self.cmd_send("*:SN?")
        self.serial_number = self.cmd_recv()
        self.cmd_send("*:MN?")
        self.model_number = self.cmd_recv()
        self.cmd_send("*:FIRMWARE?")
        self.firmware_name = self.cmd_recv()

        # Safety-check.
        assert self.dev is not None

    def cmd_send(self, cmd):
        """Send the command CMD representing by a string to the device."""
        assert type(cmd) == str
        # Send the command CMD to endpoint address 1.
        l.LOGGER.debug("Send command: {}".format(cmd))
        self.dev.write(1, cmd)

    def cmd_recv(self):
        """Return the response to the previous command as a string."""
        # Read a buffer a 64 bytes.
        resp = ""
        buf = self.dev.read(0x81, 64)
        # Convert the response to a string.
        i = 1
        while (buf[i] < 255 and buf[i] > 0):
            resp = resp + chr(buf[i])
            i = i + 1
        return resp

    def attenuation_set(self, val):
        """Set the attenuation of the attenuator to VAL. VAL should be an
        integer or a float between 0 and 110.

        On succes, return 0. On error, return 1.

        """
        assert type(val) == int or type(val) == float
        assert val >= 0 and val <= 110
        l.LOGGER.debug("Set attenuation to {}".format(val))
        # Set attenuation of channel 1 (unique channel).
        self.cmd_send("*:CHAN:1:SETATT:{:.2f};".format(val))
        # Handle the return code.
        ret = int(self.cmd_recv())
        if ret == 1:
            return 0
        else:
            return 1

    def attenuation_get(self):
        """Return the attenuation value for the default channel."""
        self.cmd_send("*:ATT?")
        return self.cmd_recv()

    def __str__(self):
        """Print informations about current RCDAT instance."""
        str = "Model number: {}\n".format(self.model_number)
        str += "Serial number: {}\n".format(self.serial_number)
        str += "Firmware name: {}".format(self.firmware_name)
        return str

if __name__ == "__main__":
    # Instantiate a RCDAT attenuator.
    rcdat = RCDAT()
    # Print its informations.
    print(rcdat)
    # Set an attenuation value to unique channel.
    ret = rcdat.attenuation_set(5)
    # Print return code.
    print(ret)
    # Get all channels attenuation.
    print(rcdat.attenuation_get())
    # Exit.
    exit(0)
