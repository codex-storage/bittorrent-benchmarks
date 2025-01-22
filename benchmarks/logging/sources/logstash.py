import datetime
import logging
from collections.abc import Iterator
from typing import Optional, Tuple, Any, Dict, List

from elasticsearch import Elasticsearch

from benchmarks.core.concurrency import pflatmap
from benchmarks.logging.sources.sources import LogSource, ExperimentId, NodeId, RawLine

GROUP_LABEL = "app.kubernetes.io/part-of"
EXPERIMENT_LABEL = "app.kubernetes.io/instance"
DEFAULT_HORIZON = 5
ES_MAX_BATCH_SIZE = 10_000

logger = logging.getLogger(__name__)


class LogstashSource(LogSource):
    """Log source for logs stored in Elasticsearch by Logstash. This is typically used when running experiments
    in a Kubernetes cluster."""

    def __init__(
        self,
        client: Elasticsearch,
        structured_only: bool = False,
        chronological: bool = False,
        slices: int = 1,
        horizon: int = DEFAULT_HORIZON,
        today: Optional[datetime.date] = None,
    ):
        """
        @:param client: Elasticsearch client to use for retrieving logs
        @:param structured_only: If True, only return structured log lines (those starting with '>>').
        @:param chronological: If True, return logs in chronological order. This is mostly meant for use
            in testing, and can get quite slow/expensive for large queries.
        """
        self.client = client
        self.structured_only = structured_only
        self.chronological = chronological
        self.slices = slices
        self._indexes = self._generate_indexes(today, horizon)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.client.close()

    @property
    def indexes(self) -> List[str]:
        return list(self._indexes)

    def experiments(self, group_id: str) -> Iterator[str]:
        """Retrieves all experiment IDs within an experiment group."""
        query = {
            "size": 0,
            "query": {
                "constant_score": {
                    "filter": {"term": {f"pod_labels.{GROUP_LABEL}.keyword": group_id}}
                }
            },
            "aggs": {
                "experiments": {
                    "terms": {
                        "field": f"pod_labels.{EXPERIMENT_LABEL}.keyword",
                        "size": 1000,
                    }
                }
            },
        }

        response = self.client.search(index="benchmarks-*", body=query)
        for bucket in response["aggregations"]["experiments"]["buckets"]:
            yield bucket["key"]

    def logs(
        self, group_id: str, experiment_id: Optional[str] = None
    ) -> Iterator[Tuple[ExperimentId, NodeId, RawLine]]:
        """Retrieves logs for either all experiments within a group, or a specific experiment."""
        filters = [{"term": {f"pod_labels.{GROUP_LABEL}.keyword": group_id}}]

        if experiment_id:
            filters.append(
                {"term": {f"pod_labels.{EXPERIMENT_LABEL}.keyword": experiment_id}}
            )

        if self.structured_only:
            filters.append({"match_phrase": {"message": "entry_type"}})

        query: Dict[str, Any] = {"query": {"bool": {"filter": filters}}}

        if self.chronological:
            query["sort"] = [{"@timestamp": {"order": "asc"}}]
        else:
            # More efficient, as per https://www.elastic.co/guide/en/elasticsearch/reference/current/paginate-search-results.html#scroll-search-results
            query["sort"] = ["_doc"]

        # We can probably cache this, but for now OK.
        actual_indexes = [
            index for index in self.indexes if self.client.indices.exists(index=index)
        ]

        if self.slices > 1:
            yield from pflatmap(
                [
                    self._run_scroll(sliced_query, actual_indexes)
                    for sliced_query in self._sliced_queries(query)
                ],
                workers=self.slices,
                max_queue_size=100_000,
            )
        else:
            yield from self._run_scroll(query, actual_indexes)

    def _sliced_queries(self, query: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
        for i in range(self.slices):
            query_slice = query.copy()
            query_slice["slice"] = {"id": i, "max": self.slices}
            yield query_slice

    def _run_scroll(self, query: Dict[str, Any], actual_indexes: List[str]):
        scroll_response = self.client.search(
            index=actual_indexes, body=query, scroll="2m", size=ES_MAX_BATCH_SIZE
        )
        scroll_id = scroll_response["_scroll_id"]

        try:
            while True:
                hits = scroll_response["hits"]["hits"]
                logger.info(f"Retrieved {len(hits)} log entries.")
                if not hits:
                    break

                for hit in hits:
                    source = hit["_source"]
                    message = source["message"]

                    experiment_id = source["pod_labels"][EXPERIMENT_LABEL]
                    node_id = source["pod_name"]

                    if (
                        not isinstance(experiment_id, str)
                        or not isinstance(node_id, str)
                        or not isinstance(message, str)
                    ):
                        logger.warning(
                            "Skipping log entry with invalid data: %s", source
                        )
                        continue

                    yield experiment_id, node_id, message

                # Get next batch of results
                scroll_response = self.client.scroll(scroll_id=scroll_id, scroll="2m")
        finally:
            # Clean up scroll context
            self.client.clear_scroll(scroll_id=scroll_id)

    def __str__(self):
        return (
            f"LogstashSource(client={self.client}, structured_only={self.structured_only}, "
            f"chronological={self.chronological}, indexes={self.indexes})"
        )

    def _generate_indexes(self, today: Optional[datetime.date], horizon: int):
        if today is None:
            today = datetime.date.today()

        return [
            f"benchmarks-{(today - datetime.timedelta(days=i)).strftime('%Y.%m.%d')}"
            for i in range(horizon)
        ]
