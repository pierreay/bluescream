# Create the Docker container from the image.
build:
	docker build -t ubuntu .

# Execute a command in the Docker container and stop the container.
run:
	docker run --rm ubuntu /bin/bash -c "cd /examples && ls"

# Get a shell into the Docker container.
shell:
	docker run -it ubuntu /bin/bash

# Clean our Docker images and containers.
clean:
	docker rmi -f ubuntu:latest
