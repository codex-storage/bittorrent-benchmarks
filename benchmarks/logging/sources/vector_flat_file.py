import json
from collections.abc import Iterator
from json import JSONDecodeError
from typing import TextIO, Optional, Tuple
import logging

from benchmarks.logging.sources.sources import LogSource, ExperimentId, NodeId, RawLine

logger = logging.getLogger(__name__)


class VectorFlatFileSource(LogSource):
    """Log source for flat JSONL files produced by [Vector](https://vector.dev/). This is typically used when running
    experiments locally within, say, Minikube or Kind."""

    def __init__(self, file: TextIO, app_name: str):
        self.file = file
        self.app_name = app_name

    def experiments(self, group_id: str) -> Iterator[str]:
        """
        Retrieves all experiment IDs within an experiment group. Can be quite slow as this source supports
        no indexing or aggregation.

        See also: :meth:`LogSource.experiments`.
        """
        app_label = f'"app.kubernetes.io/name":"{self.app_name}"'
        group_label = f'"app.kubernetes.io/part-of":"{group_id}"'
        seen = set()

        self.file.seek(0)
        for line in self.file:
            if app_label not in line or group_label not in line:
                continue

            parsed = json.loads(line)
            experiment_id = parsed["kubernetes"]["pod_labels"][
                "app.kubernetes.io/instance"
            ]
            if experiment_id in seen:
                continue
            seen.add(experiment_id)
            yield experiment_id

    def logs(
        self, group_id: str, experiment_id: Optional[str] = None
    ) -> Iterator[Tuple[ExperimentId, NodeId, RawLine]]:
        """Retrieves logs for either all experiments within a group, or a specific experiments. Again, since this
        source supports no indexing this can be quite slow, as each query represents a full pass on the file.
        I strongly encourage not attempting to retrieve logs for experiments individually.
        """
        app_label = f'"app.kubernetes.io/name":"{self.app_name}"'
        group_label = f'"app.kubernetes.io/part-of":"{group_id}"'
        experiment_label = f'"app.kubernetes.io/instance":"{experiment_id}"'

        self.file.seek(0)
        for line in self.file:
            # Does a cheaper match to avoid parsing every line.
            if app_label in line and group_label in line:
                if experiment_id is not None and experiment_label not in line:
                    continue
                try:
                    parsed = json.loads(line)
                except JSONDecodeError as err:
                    logger.error(
                        f"Failed to parse line from vector from source {line}", err
                    )
                    continue

                k8s = parsed["kubernetes"]
                yield (
                    k8s["pod_labels"]["app.kubernetes.io/instance"],
                    k8s["pod_name"],
                    parsed["message"],
                )

    def __str__(self):
        return f"VectorFlatFileSource({self.app_name})"
