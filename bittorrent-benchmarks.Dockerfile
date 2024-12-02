FROM python:3.12-slim

ARG BUILD_TYPE="test"

RUN pip install poetry && poetry config virtualenvs.create false

RUN mkdir /opt/bittorrent-benchmarks
WORKDIR /opt/bittorrent-benchmarks

RUN echo "CU"

COPY pyproject.toml poetry.lock ./
RUN if [ "$BUILD_TYPE" = "production" ]; then \
      echo "Image is a production build"; \
      poetry install --only main --no-root; \
    else \
      echo "Image is a test build";  \
      poetry install --no-root;  \
    fi

COPY . .
RUN poetry install --only main

ENTRYPOINT ["/usr/local/bin/bittorrent-benchmarks", "/opt/bittorrent-benchmarks/experiments.yaml"]

