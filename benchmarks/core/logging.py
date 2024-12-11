import datetime
import json
import logging
from csv import DictWriter
from enum import Enum
from json import JSONDecodeError
from typing import Type, TextIO, Iterable, Callable, Dict, Tuple

from pydantic import ValidationError, computed_field, Field

from benchmarks.core.pydantic import SnakeCaseModel

MARKER = '>>'

logger = logging.getLogger(__name__)


class LogEntry(SnakeCaseModel):
    def __str__(self):
        return f"{MARKER}{self.model_dump_json()}"

    @computed_field # type: ignore
    @property
    def entry_type(self) -> str:
        return self.alias()


class LogParser:
    def __init__(self):
        self.entry_types = {}
        self.warn_counts = 10

    def register(self, entry_type: Type[SnakeCaseModel]):
        self.entry_types[entry_type.alias()] = entry_type

    def parse(self, log: TextIO) -> Iterable[LogEntry]:
        marker_len = len(MARKER)
        for line in log:
            index = line.find(MARKER)
            if index == -1:
                continue

            type_tag = ''  # just to calm down mypy
            try:
                # Should probably test this against a regex for the type tag to see which is faster.
                json_line = json.loads(line[index + marker_len:])
                type_tag = json_line.get('entry_type')
                if not type_tag or (type_tag not in self.entry_types):
                    continue
                yield self.entry_types[type_tag].model_validate(json_line)
            except JSONDecodeError:
                pass
            except ValidationError as err:
                # This is usually something we want to know about, as if the message has a type_tag
                # that we know, then we should probably be able to parse it.
                self.warn_counts -= 1  # avoid flooding everything with warnings
                if self.warn_counts > 0:
                    logger.warning(f"Schema failed for line with known type tag {type_tag}: {err}")
                elif self.warn_counts == 0:
                    logger.warning("Too many errors: suppressing further schema warnings.")


class LogSplitter:
    def __init__(self, output_factory=Callable[[str], TextIO], output_entry_type=False) -> None:
        self.output_factory = output_factory
        self.dump = (
            (lambda model: model.model_dump())
            if output_entry_type
            else (lambda model: model.model_dump(exclude={'entry_type'}))
        )

        self.outputs: Dict[str, Tuple[DictWriter, TextIO]] = {}

    def split(self, log: Iterable[LogEntry]):
        for entry in log:
            writer, _ = self.outputs.get(entry.entry_type, (None, None))
            entry_dict = self.dump(entry)

            if writer is None:
                output = self.output_factory(entry.entry_type)
                writer = DictWriter(output, fieldnames=entry_dict.keys())
                self.outputs[entry.entry_type] = writer, output
                writer.writeheader()

            writer.writerow(entry_dict)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        for _, output in self.outputs.values():
            output.close()


type NodeId = str


class Event(LogEntry):
    node: NodeId
    name: str  # XXX this ends up being redundant for custom event schemas... need to think of a better solution.
    timestamp: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.UTC))


class Metric(Event):
    value: int | float


class RequestEventType(Enum):
    start = 'start'
    end = 'end'


class RequestEvent(Event):
    destination: NodeId
    request_id: str
    type: RequestEventType


def basic_log_parser() -> LogParser:
    parser = LogParser()
    parser.register(Event)
    parser.register(Metric)
    parser.register(RequestEvent)
    return parser
