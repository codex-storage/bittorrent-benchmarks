FROM python:3.12-slim

ARG BUILD_TYPE="test"

RUN pip install poetry

RUN mkdir /opt/bittorrent-benchmarks
WORKDIR /opt/bittorrent-benchmarks

COPY pyproject.toml poetry.lock ./
RUN if [ "$BUILD_TYPE" = "release" ]; then \
      echo "Image is a release build"; \
      poetry install --without dev --no-root; \
    else \
      echo "Image is a test build";  \
      poetry install --no-root;  \
    fi

COPY . .
RUN poetry install --only main

ENTRYPOINT ["poetry", "run", "bittorrent-benchmarks", "experiments"]
