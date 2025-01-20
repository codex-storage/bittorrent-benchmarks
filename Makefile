SHELL := bash

.SHELLFLAGS := -eu -o pipefail -c

.PHONY: unit \
		harness-start \
		harness-stop \
		integration \
		tests \
		integration-docker \
		image-test \
		image-minikube \
		clean

# Runs the unit tests locally.
unit:
	poetry run pytest -m "not integration"

# Starts the local integration harness. This is required for running pytest with the "integration" marker.
harness-start:
	docker compose -f docker-compose.local.yaml up

# Stops the local integration harness.
harness-stop:
	docker compose -f docker-compose.local.yaml down --volumes --remove-orphans

# Runs the integration tests locally. This requires the integration harness to be running.
integration:
	echo "NOTE: Make sure to have started the integration harness or this will not work"
	poetry run pytest -m "integration"

tests: unit integration

image-test:
	docker build -t bittorrent-benchmarks:test -f ./docker/bittorrent-benchmarks.Dockerfile .

image-minikube:
	eval $$(minikube docker-env) && \
	docker build -t bittorrent-benchmarks:minikube \
		--build-arg BUILD_TYPE="release" \
		-f ./docker/bittorrent-benchmarks.Dockerfile .

# Runs the integration tests in a docker container.
integration-docker:
	docker compose -f docker-compose.local.yaml -f docker-compose.ci.yaml down --volumes --remove-orphans
	docker compose -f docker-compose.local.yaml -f docker-compose.ci.yaml up \
		--abort-on-container-exit --exit-code-from test-runner

clean:
	docker compose -f docker-compose.local.yaml -f docker-compose.ci.yaml down --volumes --rmi all --remove-orphans
