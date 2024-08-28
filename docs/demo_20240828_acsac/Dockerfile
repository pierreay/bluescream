FROM ubuntu:22.04 AS ubuntu-screaming_channels_ble
# Automatically answer Yes for APT questions.
ENV DEBIAN_FRONTEND noninteractive

# Update the system and install basic tools.
RUN apt-get update && apt-get install -yq git vim python3-pip sudo wget unzip
RUN pip3 install setuptools numpy==2.0.0

# Clone our project and create environment variables for it.
ENV SC=/screaming_channels_ble
ENV SC_SRC=/screaming_channels_ble/src
ENV SC_DOCKER=/screaming_channels_ble/docs/demo_20240828_acsac
RUN test -d screaming_channels_ble && : || git clone https://github.com/pierreay/screaming_channels_ble.git

# Move into it.
# WORKDIR "${SC}"
