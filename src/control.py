#!/usr/bin/python3

import click

import lib.utils as utils
import lib.log as l
import lib.rcdat as rcdat

@click.group(context_settings={'show_default': True})
@click.option("--log/--no-log", default=True, help="Enable or disable logging.")
@click.option("--loglevel", default="DEBUG", help="Set the logging level.")
def cli(log, loglevel):
    """Setup control utility."""
    l.configure(log, loglevel)

@cli.command()
@click.argument("att", type=int)
def set_att(att):
    """Set the RCDAT atenuation to ATT in dB."""
    l.LOGGER.info("Set the programmable attenuation to {} dB".format(att))
    rcdat_ctrl = rcdat.RCDAT()
    ret = rcdat_ctrl.attenuation_set(att)
    if ret != 0:
        l.LOGGER.error("An error has occured during attenuation configuration!")
        exit(ret)

@cli.command()
def get_att():
    """Get the RCDAT atenuation."""
    rcdat_ctrl = rcdat.RCDAT()
    att = rcdat_ctrl.attenuation_get()
    l.LOGGER.info("Programmable attenuation is set to {} dB".format(att))

if __name__ == "__main__":
    cli()
