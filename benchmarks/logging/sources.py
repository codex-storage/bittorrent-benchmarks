"""This module standardizes interfaces for consuming logs from external log sources; i.e. infrastructure
that stores logs. Such infrastructure might be a simple file system, a service like Logstash, or a database."""

import json
from abc import ABC, abstractmethod
from collections.abc import Iterator
from contextlib import AbstractContextManager
from pathlib import Path
from typing import TextIO, Optional, Tuple, List, Dict, Type

from benchmarks.logging.logging import (
    LogParser,
    LogSplitter,
    LogSplitterFormats,
    LogEntry,
)

RawLine = str
ExperimentId = str
NodeId = str


class LogSource(ABC):
    """:class:`LogSource` knows how to retrieve logs for experiments within experiment groups. A key assumption is that
    group ids are known, and those can usually be recovered from, say, a workflow run."""

    @abstractmethod
    def experiments(self, group_id: str) -> Iterator[str]:
        """Retrieves all experiment IDs within an experiment group."""
        pass

    @abstractmethod
    def logs(
        self, group_id: str, experiment_id: Optional[str] = None
    ) -> Iterator[Tuple[ExperimentId, NodeId, RawLine]]:
        """Retrieves logs for either all experiments within a group, or a specific experiments.

        @param group_id: The group ID to retrieve logs for.
        @param experiment_id: The experiment ID to retrieve logs for. If None, logs for all experiments in the group.

        @return: An iterator of tuples, where each tuple contains the experiment ID, the node ID, and a raw (unparsed)
            log line."""
        pass


class OutputManager(AbstractContextManager):
    """An :class:`OutputManager` is responsible for managing output locations for log splitting operations.
    :class:`OutputManager`s must be closed after use, and implements the context manager interface to that end."""

    def open(self, relative_path: Path) -> TextIO:
        """Opens a file for writing within a relative abstract path."""
        if relative_path.is_absolute():
            raise ValueError(f"Path {relative_path} must be relative.")
        return self._open(relative_path)

    @abstractmethod
    def _open(self, relative_path: Path) -> TextIO:
        pass


class FSOutputManager(OutputManager):
    """Simple :class:`OutputManager` which writes directly into the file system."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.open_files: List[TextIO] = []

    def _open(self, relative_path: Path) -> TextIO:
        fullpath = self.root / relative_path
        parent = fullpath.parent
        parent.mkdir(parents=True, exist_ok=True)
        f = fullpath.open("w", encoding="utf-8")
        self.open_files.append(f)
        return f

    def __exit__(self, exc_type, exc_val, exc_tb):
        for f in self.open_files:
            try:
                f.close()
            except IOError:
                pass


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
                parsed = json.loads(line)
                k8s = parsed["kubernetes"]
                yield (
                    k8s["pod_labels"]["app.kubernetes.io/instance"],
                    k8s["pod_name"],
                    parsed["message"],
                )


def split_logs_in_source(
    log_source: LogSource,
    log_parser: LogParser,
    output_manager: OutputManager,
    group_id: str,
    formats: Optional[List[Tuple[Type[LogEntry], LogSplitterFormats]]] = None,
) -> None:
    """
    Parses logs for an entire experiment group and splits them onto separate folders per experiment, as well
    as separate files for each log type. This makes it suitable for consumption by an analysis environment.

    :param log_source: The :class:`LogSource` to retrieve logs from.
    :param log_parser: A suitably configured :class:`LogParser` which can understand the logs.
    :param output_manager: An :class:`OutputManager` to manage where output content gets placed.
    :param group_id: The group ID to retrieve logs for.
    :param formats: An additional format configuration to be fed onto :class:`LogSplitter`.
    """
    splitters: Dict[str, LogSplitter] = {}
    formats = formats if formats else []

    for experiment_id, node_id, raw_line in log_source.logs(group_id):
        splitter = splitters.get(experiment_id)
        if splitter is None:
            splitter = LogSplitter(
                lambda event_type, ext: output_manager.open(
                    Path(experiment_id) / f"{event_type}.{ext.value}"
                )
            )
            for entry_type, output_format in formats:
                splitter.set_format(entry_type, output_format)

            splitters[experiment_id] = splitter

        parsed = log_parser.parse_single(raw_line)
        if parsed:
            splitter.split_single(parsed)
