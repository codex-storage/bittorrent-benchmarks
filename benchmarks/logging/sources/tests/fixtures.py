import json
import os
from pathlib import Path
from typing import Dict, Any

import pytest
from elasticsearch import Elasticsearch

from benchmarks.core.utils import await_predicate


def _json_data(data: str) -> Dict[str, Any]:
    with (Path(__file__).parent / data).open(encoding="utf-8") as json_file:
        return json.load(json_file)


@pytest.fixture(scope="module")
def benchmark_logs_client() -> Elasticsearch:
    client = Elasticsearch(os.environ.get("ELASTICSEARCH_URL", "http://localhost:9200"))

    if client.indices.exists(index="benchmarks-2025.01.21"):
        client.indices.delete(index="benchmarks-2025.01.21")

    client.indices.create(
        index="benchmarks-2025.01.21",
        body=_json_data("benchmarks-2025.01.21-mapping.json"),
    )

    documents = _json_data("benchmarks-2025.01.21-documents.json")["documents"]
    for document in documents:
        client.index(index="benchmarks-2025.01.21", body=document)

    def _is_indexed() -> bool:
        return client.count(index="benchmarks-2025.01.21")["count"] == len(documents)

    assert await_predicate(
        _is_indexed, timeout=10, polling_interval=0.5
    ), "Indexing failed"

    return client
