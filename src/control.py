#!/usr/bin/python3

import math

import click

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
def set_attenuation(att):
    """Set the RCDAT atenuation to ATT in dB."""
    l.LOGGER.info("Set the attenuation to {} dB".format(att))
    att_total = att + 10
    l.LOGGER.info("Total attenuation is {} dB equivalent to {:.3f} meters of distance".format(att_total, 10 ** ((att_total - 20 * math.log10(2.4e9) + 147.55) / 20)))
    rcdat_ctrl = rcdat.RCDAT()
    ret = rcdat_ctrl.attenuation_set(att)
    if ret != 0:
        l.LOGGER.error("An error has occured during attenuation configuration!")
        exit(ret)

if __name__ == "__main__":
    cli()
