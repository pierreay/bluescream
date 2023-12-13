"""Mini-Circuits' RCDAT Python Wrapper

The RCDAT is a single-channel programmable attenuator controllable using USB
interrupts.

References:

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

# Find our device.
dev = usb.core.find(idVendor=0x20ce, idProduct=0x0023)
if dev is None:
    raise ValueError('Device not found!')

for configuration in dev:
    for interface in configuration:
        ifnum = interface.bInterfaceNumber
    if not dev.is_kernel_driver_active(ifnum):
        continue
    try:
        dev.detach_kernel_driver(ifnum)
    except (usb.core.USBError, e):
        pass

# Set the active configuration. With no args, we use the first config.
dev.set_configuration()
SerialN = ""
ModelN = ""
Fw = ""

# Get the serial number.
dev.write(1, "*:SN?") # Send "*:SN?" to endpoint address 1.
sn = dev.read(0x81, 64)
# Convert the serial number.
i = 1
while (sn[i] < 255 and sn[i] > 0):
    SerialN = SerialN + chr(sn[i])
    i = i + 1

# Get the model number.
dev.write(1, "*:MN?")
mn = dev.read(0x81, 64)
# Convert the model number.
i = 1
while (mn[i] < 255 and mn[i] > 0):
    ModelN = ModelN + chr(mn[i])
    i = i + 1

# Get the firmware version.
dev.write(1,"*:FIRMWARE?")
sn = dev.read(0x81, 64)
# Convert the firmware version.
i = 1
while (sn[i] < 255 and sn[i] > 0):
    Fw = Fw + chr(sn[i])
    i = i + 1

# Print information.
print(ModelN)
print(SerialN)
print(Fw)

# Set attenuation of channel 1 to 11.25 dB.
dev.write(1, "*:CHAN:1:SETATT:11.25;")
# Get the command response.
resp = dev.read(0x81, 64)
# Convert the command response.
i = 1
AttResp = ""
while (resp[i] < 255 and resp[i] > 0):
    AttResp = AttResp + chr(resp[i])
    i = i + 1
print(AttResp)

# Get all channels attenuation.
dev.write(1,"*:ATT?")
resp = dev.read(0x81,64)
i = 1
AttResp = ""
while (resp[i] < 255 and resp[i] > 0):
    AttResp = AttResp + chr(resp[i])
    i = i + 1
print(AttResp)
