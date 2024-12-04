FROM python:3.12-slim

ARG UID=1000
ARG GID=1000
ARG BUILD_TYPE="test"

RUN groupadd -g ${GID} runner \
    && useradd -u ${UID} -g ${GID} -s /bin/bash -m runner
RUN mkdir /opt/bittorrent-benchmarks && chown -R runner:runner /opt/bittorrent-benchmarks
RUN pip install poetry

USER runner
WORKDIR /opt/bittorrent-benchmarks

COPY --chown=runner:runner pyproject.toml poetry.lock ./
RUN if [ "$BUILD_TYPE" = "production" ]; then \
      echo "Image is a production build"; \
      poetry install --only main --no-root; \
    else \
      echo "Image is a test build";  \
      poetry install --no-root;  \
    fi

COPY --chown=runner:runner . .
RUN poetry install --only main

ENTRYPOINT ["poetry", "run", "bittorrent-benchmarks", "/opt/bittorrent-benchmarks/experiments.yaml"]
