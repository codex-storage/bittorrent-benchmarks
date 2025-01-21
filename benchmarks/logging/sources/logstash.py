import logging
from collections.abc import Iterator
from typing import Optional, Tuple, Any, Dict

from elasticsearch import Elasticsearch

from benchmarks.logging.sources.sources import LogSource, ExperimentId, NodeId, RawLine

GROUP_LABEL = "app.kubernetes.io/part-of"
EXPERIMENT_LABEL = "app.kubernetes.io/instance"

logger = logging.getLogger(__name__)


class LogstashSource(LogSource):
    """Log source for logs stored in Elasticsearch by Logstash. This is typically used when running experiments
    in a Kubernetes cluster."""

    def __init__(
        self,
        client: Elasticsearch,
        structured_only: bool = False,
        chronological: bool = False,
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

        # Scrolls are much cheaper than queries.
        scroll_response = self.client.search(
            index="benchmarks-*", body=query, scroll="2m"
        )
        scroll_id = scroll_response["_scroll_id"]

        try:
            while True:
                hits = scroll_response["hits"]["hits"]
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
