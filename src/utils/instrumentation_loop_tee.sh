#!/bin/bash

while 1; do radio_instrument INFO attack 0 && radio_extract INFO --no-plot 2>&1 | tee -a /tmp/radio_extract_output ; done
