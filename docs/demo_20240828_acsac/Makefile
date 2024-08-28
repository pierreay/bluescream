# Create the Docker container from the image.
build:
	docker build -t ubuntu .

# Get a shell into the Docker container.
shell:
	docker run -it ubuntu /bin/bash

# Clean our Docker images and containers.
clean:
	docker rmi -f ubuntu:latest
