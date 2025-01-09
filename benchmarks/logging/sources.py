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
    """:class:`LogSource` knows how to retrieve logs for :class:`Identifiable` experiments, and can answer queries
    about which experiments are present within it."""

    @abstractmethod
    def experiments(self, group_id: str) -> Iterator[str]:
        pass

    @abstractmethod
    def logs(
        self, group_id: str, experiment_id: Optional[str] = None
    ) -> Iterator[Tuple[ExperimentId, NodeId, RawLine]]:
        pass


class OutputManager(AbstractContextManager):
    def open(self, relative_path: Path) -> TextIO:
        if relative_path.is_absolute():
            raise ValueError(f"Path {relative_path} must be relative.")
        return self._open(relative_path)

    @abstractmethod
    def _open(self, relative_path: Path) -> TextIO:
        pass


class FSOutputManager(OutputManager):
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
    def __init__(self, file: TextIO, app_name: str):
        self.file = file
        self.app_name = app_name

    def experiments(self, group_id: str) -> Iterator[str]:
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
            splitter.process_single(parsed)
