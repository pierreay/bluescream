FROM ubuntu:22.04 AS ubuntu-screaming_channels_ble
# Automatically answer Yes for APT questions.
ENV DEBIAN_FRONTEND=noninteractive

# Update the system and install basic tools.
RUN apt-get update && apt-get install -yq git vim python3-pip sudo wget unzip
RUN pip3 install setuptools numpy==2.0.0

# Clone our project and create environment variables for it.
ENV SC=/screaming_channels_ble
ENV SC_SRC=/screaming_channels_ble/src
ENV SC_DOCKER=/screaming_channels_ble/docs/demo_20240828_acsac
RUN test -d screaming_channels_ble && : || git clone https://github.com/pierreay/screaming_channels_ble.git

# Get the datasets.
RUN --mount=type=bind,source=.,target=/host /bin/bash -c 'cd /host && cp -t $SC_DOCKER /host/240207_1-leak-pairing-10cm-anechoic-2.533e9-8e6_raw.tar.bz2'
RUN /bin/bash -c 'cd $SC_DOCKER && tar xvf 240207_1-leak-pairing-10cm-anechoic-2.533e9-8e6_raw.tar.bz2'
RUN --mount=type=bind,source=.,target=/host /bin/bash -c 'cd /host && cp -t $SC_DOCKER /host/240429_highdist_2lna_highgain_norep.tar.bz2'
RUN /bin/bash -c 'cd $SC_DOCKER && tar xvf 240429_highdist_2lna_highgain_norep.tar.bz2'

# Move into it.
# WORKDIR "${SC}"
