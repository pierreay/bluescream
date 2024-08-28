# Create the Docker container from the image.
build: .dockerinit

.dockerinit:
	docker build -t ubuntu-screaming_channels_ble .
	docker run -v ${PWD}:/host ubuntu-screaming_channels_ble /bin/bash -c 'cd /host && cp -t $$SC_DOCKER /host/240207_1-leak-pairing-10cm-anechoic-2.533e9-8e6_raw.tar.bz2'
	docker run -v ${PWD}:/host ubuntu-screaming_channels_ble /bin/bash -c 'cd /host && cp -t $$SC_DOCKER /host/240429_highdist_2lna_highgain_norep.tar.bz2'
	touch .dockerinit

# Get a shell into the Docker container.
shell:
	docker run -it ubuntu-screaming_channels_ble /bin/bash

# Clean our Docker images and containers.
clean:
	docker rmi -f ubuntu-screaming_channels_ble:latest
	rm .dockerinit
