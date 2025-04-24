import json
from collections.abc import Iterator
from datetime import datetime
from functools import total_ordering
from heapq import heapify, heappush, heappop
from json import JSONDecodeError
from typing import TextIO, Optional, Tuple, List, Callable
import logging
import re

from benchmarks.logging.sources.sources import LogSource, ExperimentId, NodeId, RawLine

logger = logging.getLogger(__name__)

_POD_NAME_REGEX = re.compile(r'"pod_name":"(?P<pod_name>[^"]+)"')
_TIMESTAMP_REGEX = re.compile(r'"timestamp":"(?P<timestamp>[^"]+)"')


@total_ordering
class PodLog(object):
    """:class:`PodLog` allows us to iterate separately over the logs of the various pods even when they
    are merged into the same file. This is useful when trying to sort the logs of a vector file dump as
    those are guaranteed to be sorted per-pod, but not across pods."""

    def __init__(self, pod_name: str, file: TextIO) -> None:
        self.pod_name = pod_name
        self.file = file
        self.pointer: int = 0

        self.next_line: Optional[Tuple[str, datetime]] = self._scan_next()

    @property
    def timestamp(self) -> datetime:
        if not self.next_line:
            raise ValueError("Cannot compare: log has run out of entries")
        return self.next_line[1]

    def has_next(self) -> bool:
        """Returns true if there are more logs to read for this pod."""
        return self.next_line is not None

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PodLog):
            return NotImplemented
        return self.timestamp == other.timestamp

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, PodLog):
            return NotImplemented
        return self.timestamp < other.timestamp

    def __next__(self) -> Tuple[str, datetime]:
        if self.next_line is None:
            raise StopIteration()
        value = self.next_line
        self.next_line = self._scan_next()
        return value

    def _iter_file(self) -> Iterator[str]:
        """Iterates over the file, yielding lines."""
        self.file.seek(self.pointer)
        for line in iter(self.file.readline, ""):
            self.pointer = self.file.tell()
            yield line

    def _scan_next(self) -> Optional[Tuple[str, datetime]]:
        pod_name = f'"pod_name":"{self.pod_name}"'
        for line in self._iter_file():
            self.pointer = self.file.tell()
            if pod_name not in line:
                continue

            timestamp = _TIMESTAMP_REGEX.search(line)
            if not timestamp:
                logger.error(f"Log line contains no timestamp {line}")
                continue

            return line, datetime.fromisoformat(timestamp.group("timestamp"))
        return None


class VectorFlatFileSource(LogSource):
    """Log source for flat JSONL files produced by [Vector](https://vector.dev/). This is typically used when running
    experiments locally within, say, Minikube or Kind."""

    def __init__(self, file: TextIO, app_name: str, sorted=False):
        self.file = file
        self.app_name = app_name
        self.sorted = sorted

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.file.close()

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

    def _sorted_logs(self, line_predicate: Callable[[str], bool]) -> Iterator[str]:
        sources = [
            source for source in self._pod_logs(line_predicate) if source.has_next()
        ]
        heapify(sources)
        while sources:
            log = heappop(sources)
            yield next(log)[0]
            if log.has_next():
                heappush(sources, log)

    def _unsorted_logs(self, line_predicate: Callable[[str], bool]) -> Iterator[str]:
        self.file.seek(0)
        for line in self.file:
            if not line_predicate(line):
                continue
            yield line

    def _pod_logs(self, line_predicate: Callable[[str], bool]) -> List[PodLog]:
        logger.info("Identifying pod logs.")
        self.file.seek(0)
        pod_logs = {}
        for line in self.file:
            if not line_predicate(line):
                continue
            match = _POD_NAME_REGEX.search(line)
            if not match:
                logger.error(f"Log line contains no pod name {line}")
                continue
            pod_name = match.group("pod_name")
            if pod_name not in pod_logs:
                logger.info(f"Pod found: {pod_name}")
                pod_logs[pod_name] = PodLog(pod_name, self.file)

        return list(pod_logs.values())

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

        def line_predicate(line: str) -> bool:
            return (
                app_label in line
                and group_label in line
                and (experiment_id is None or experiment_label in line)
            )

        logs = (
            self._sorted_logs(line_predicate)
            if self.sorted
            else self._unsorted_logs(line_predicate)
        )
        for line in logs:
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
