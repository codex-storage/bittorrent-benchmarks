FROM python:3.12-slim

RUN pip install poetry && poetry config virtualenvs.create false

RUN mkdir /opt/bittorrent-benchmarks
WORKDIR /opt/bittorrent-benchmarks

COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root

COPY . .
RUN poetry install

ENTRYPOINT ["/usr/local/bin/bittorrent-benchmarks", "/opt/bittorrent-benchmarks/experiments.yaml"]

