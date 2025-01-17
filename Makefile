SHELL := bash

.SHELLFLAGS := -eu -o pipefail -c

.PHONY: unit \
		harness-start \
		harness-stop \
		integration \
		tests \
		unit-docker \
		integration-docker \
		image-test \
		image-release \
		clean

# Runs the unit tests locally.
unit:
	poetry run pytest -m "not integration"

# Starts the local integration harness. This is required for running pytest with the "integration" marker.
harness-start:
	rm -rf ${PWD}/volume/deluge-{1,2,3}
	docker compose -f docker-compose.local.yaml up

# Stops the local integration harness.
harness-stop:
	docker compose -f docker-compose.local.yaml down --volumes --remove-orphans

# Runs the integration tests locally. This requires the integration harness to be running.
integration:
	echo "NOTE: Make sure to have started the integration harness or this will not work"
	poetry run pytest -m "integration"

tests: unit integration

# Builds the test image required for local dockerized integration tests.
image-test:
	docker build -t bittorrent-benchmarks:test -f ./docker/bittorrent-benchmarks.Dockerfile .

image-release:
	docker build -t bittorrent-benchmarks:test --build-arg BUILD_TYPE="release" \
		-f ./docker/bittorrent-benchmarks.Dockerfile .

# Runs the unit tests in a docker container.
unit-docker: image-test
	docker run --entrypoint poetry --rm bittorrent-benchmarks:test run pytest -m "not integration"

# Runs the integration tests in a docker container.
integration-docker: image-test
	docker compose -f docker-compose.local.yaml -f docker-compose.ci.yaml down --volumes --remove-orphans
	docker compose -f docker-compose.local.yaml -f docker-compose.ci.yaml up \
		--abort-on-container-exit --exit-code-from test-runner

tests-docker: unit-docker integration-docker

clean:
	rm -rf docker/.lastbuilt*
	rm -rf volume/deluge-{1,2,3}
	docker compose -f docker-compose.local.yaml -f docker-compose.ci.yaml down --volumes --rmi all --remove-orphans
