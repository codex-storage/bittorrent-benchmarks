import datetime
from collections import defaultdict
from io import StringIO

from benchmarks.core.logging import LogEntry, LogParser, LogSplitter
from benchmarks.tests.utils import compact


class MetricsEvent(LogEntry):
    name: str
    timestamp: datetime.datetime
    value: float
    node: str


def test_log_entry_should_serialize_to_expected_format():
    event = MetricsEvent(
        name='download',
        timestamp=datetime.datetime(
            2021, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc
        ),
        value=0.245,
        node='node1',
    )

    assert str(
        event) == ('>>{"name":"download","timestamp":"2021-01-01T00:00:00Z","value":0.245,'
                   '"node":"node1","entry_type":"metrics_event"}')


def test_should_parse_logs():
    log = StringIO("""
    >>{"name":"download","timestamp":"2021-01-01T00:00:00Z","value":0.245,"node":"node1","entry_type":"metrics_event"}
    [some garbage introduced by the log formatter: bla bla bla] -:>>{"name":"download","timestamp":"2021-01-01T00:00:00Z","value":0.246,"node":"node2","entry_type":"metrics_event"}
    """)

    parser = LogParser()
    parser.register(MetricsEvent)

    assert list(parser.parse(log)) == [
        MetricsEvent(
            name='download',
            timestamp=datetime.datetime(
                2021, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc
            ),
            value=0.245,
            node='node1',
        ),
        MetricsEvent(
            name='download',
            timestamp=datetime.datetime(
                2021, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc
            ),
            value=0.246,
            node='node2',
        ),
    ]


def test_should_skip_unparseable_lines():
    log = StringIO("""
    >>{"name":"download","timestamp":"2021-01-01T00:00:00Z","value":0.245,"node":"node0","entry_type":"metrics_event"
    >>{"name":"download","timestamp":"2021-01-01T00:00:00Z","value":0.246,"node":"node2","entry_type":"metrics_event"}
    >>{"name":"download","timestamp":"2021-01-01T00:00:00Z","value":0.246,"node":"node5","entry_type":"metcs_event"}
    some random gibberish
    >>{"name":"download","timestamp":"2021-01-01T00:00:00Z","value":0.246,"node":"node3","entry_type":"metrics_event"}
    """)

    parser = LogParser()
    parser.register(MetricsEvent)

    assert list(parser.parse(log)) == [
        MetricsEvent(
            name='download',
            timestamp=datetime.datetime(
                2021, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc
            ),
            value=0.246,
            node='node2',
        ),
        MetricsEvent(
            name='download',
            timestamp=datetime.datetime(
                2021, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc
            ),
            value=0.246,
            node='node3',
        ),
    ]


class StateChangeEvent(LogEntry):
    old: str
    new: str


def test_should_log_events_correctly(mock_logger):
    logger, output = mock_logger

    events = [
        StateChangeEvent(old='stopped', new='started'),
        MetricsEvent(
            name='download',
            timestamp=datetime.datetime(
                2021, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc
            ),
            value=0.246,
            node='node3',
        ),
        StateChangeEvent(old='started', new='stopped'),
    ]

    for event in events:
        logger.info(event)

    parser = LogParser()
    parser.register(MetricsEvent)
    parser.register(StateChangeEvent)

    assert list(parser.parse(StringIO(output.getvalue()))) == events


class SimpleEvent(LogEntry):
    name: str
    timestamp: datetime.datetime


class Person(LogEntry):
    name: str
    surname: str


def test_should_split_intertwined_logs_by_entry_type():
    log = StringIO("""
    >>{"name":"download","timestamp":"2021-01-01T00:00:00Z","value":0.246,"node":"node2","entry_type":"metrics_event"}
    >>{"name":"start","timestamp":"2021-01-01T00:00:00Z","entry_type":"simple_event"}
    >>{"name":"John","surname":"Doe","timestamp":"2021-01-01T00:00:00Z","entry_type":"person"}
    >>{"name":"start2","timestamp":"2021-01-01T00:00:00Z","entry_type":"simple_event"}
    """)

    parser = LogParser()
    parser.register(MetricsEvent)
    parser.register(SimpleEvent)
    parser.register(Person)

    outputs = defaultdict(StringIO)

    splitter = LogSplitter(
            output_factory=lambda entry_type: outputs[entry_type],
    )

    splitter.split(parser.parse(log))

    assert compact(outputs['metrics_event'].getvalue()) == (compact("""
        name,timestamp,value,node
        download,2021-01-01 00:00:00+00:00,0.246,node2
    """))

    assert compact(outputs['simple_event'].getvalue()) == (compact("""
        name,timestamp
        start,2021-01-01 00:00:00+00:00
        start2,2021-01-01 00:00:00+00:00
    """))

    assert compact(outputs['person'].getvalue()) == (compact("""
        name,surname
        John,Doe
    """))