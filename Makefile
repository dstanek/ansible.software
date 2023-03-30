DOCKER_IMAGE=custom-ansible-test
PYTHON_VERSION=3.8
OUTPUT_PATH=builds/

test-image:
	docker build -t custom-ansible-test .

integration:
	# requires test-image to exist if using the default DOCKER_IMAGE
	ansible-test integration --color --docker $(DOCKER_IMAGE) --python $(PYTHON_VERSION)

integration-debug:
	# requires test-image to exist if using the default DOCKER_IMAGE
	ansible-test integration --color --docker $(DOCKER_IMAGE) --python $(PYTHON_VERSION) \
		--docker-terminate never

build:
	ansible-galaxy collection build --output-path $(OUTPUT_PATH)

docs:
	ansible-doc --type module --json \
		dstanek.software.generic_release \
		dstanek.software.github_release
