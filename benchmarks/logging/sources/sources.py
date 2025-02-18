import logging
from abc import abstractmethod
from collections.abc import Iterator
from contextlib import AbstractContextManager
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Type, IO

from benchmarks.logging.logging import (
    LogParser,
    LogSplitter,
    LogSplitterFormats,
    LogEntry,
)

RawLine = str
ExperimentId = str
NodeId = str

logger = logging.getLogger(__name__)


class LogSource(AbstractContextManager):
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

    def open(self, relative_path: Path, mode: str = "w", encoding="utf-8") -> IO:
        """Opens a file for writing within a relative abstract path."""
        if relative_path.is_absolute():
            raise ValueError(f"Path {relative_path} must be relative.")
        return self._open(relative_path, mode, encoding)

    @abstractmethod
    def _open(self, relative_path: Path, mode: str, encoding: str) -> IO:
        pass


class ChainedLogSource(LogSource):
    """A :class:`LogSource` which chains multiple sources together."""

    def __init__(self, sources: List[LogSource]) -> None:
        self.sources = sources

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def experiments(self, group_id: str) -> Iterator[str]:
        for source in self.sources:
            with source:
                yield from source.experiments(group_id)

    def logs(
        self, group_id: str, experiment_id: Optional[str] = None
    ) -> Iterator[Tuple[ExperimentId, NodeId, RawLine]]:
        for source in self.sources:
            with source:
                yield from source.logs(group_id, experiment_id)


class FSOutputManager(OutputManager):
    """Simple :class:`OutputManager` which writes directly into the file system.

    The current implementation is very simple, and might end up keeping a lot of open files.
    Since there's locality in th logs, we can make this better without making it slower by just
    bounding the number of open files and juggling them as an LRU cache of sorts,
    but for now just make sure your limits are big enough.
    """

    def __init__(self, root: Path) -> None:
        self.root = root
        self.open_files: List[IO] = []

    def _open(self, relative_path: Path, mode: str, encoding: str) -> IO:
        fullpath = self.root / relative_path
        parent = fullpath.parent
        parent.mkdir(parents=True, exist_ok=True)
        f = fullpath.open(mode, encoding=encoding)
        self.open_files.append(f)
        return f

    def __exit__(self, exc_type, exc_val, exc_tb):
        for f in self.open_files:
            try:
                f.close()
            except IOError:
                pass


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

    logger.info(f'Processing logs for group "{group_id} from source "{log_source}"')

    for experiment_id, node_id, raw_line in log_source.logs(group_id):
        splitter = splitters.get(experiment_id)
        if splitter is None:
            logger.info(f"Found experiment {experiment_id}")
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

    logger.info("Finished processing logs.")
