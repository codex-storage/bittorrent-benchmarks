import datetime
from io import StringIO

from benchmarks.logging.logging import LogEntry, LogParser
from benchmarks.logging.sources import (
    VectorFlatFileSource,
    split_logs_in_source,
)
from benchmarks.logging.tests.utils import InMemoryOutputManager
from benchmarks.tests.utils import make_jsonl, compact

EXPERIMENT_LOG = [
    {
        "kubernetes": {
            "container_name": "deluge-experiment-runner",
            "pod_labels": {
                "app.kubernetes.io/instance": "e1",
                "app.kubernetes.io/name": "codex-benchmarks",
                "app.kubernetes.io/part-of": "g1736425800",
            },
            "pod_name": "p1",
        },
        "message": 'INFO >>{"name":"download","timestamp":"2021-01-01T00:00:00Z","value":0.246,'
        '"node":"node2","entry_type":"metrics_event"}',
    },
    {
        "kubernetes": {
            "container_name": "deluge-experiment-runner",
            "pod_labels": {
                "app.kubernetes.io/instance": "e1",
                "app.kubernetes.io/name": "codex-benchmarks",
                "app.kubernetes.io/part-of": "g1736425800",
            },
            "pod_name": "p1",
        },
        "message": '>>{"name":"John","surname":"Doe","timestamp":"2021-01-01T00:00:00Z","entry_type":"person"}',
    },
    {
        "kubernetes": {
            "container_name": "deluge-experiment-runner",
            "pod_labels": {
                "app.kubernetes.io/instance": "e1",
                "app.kubernetes.io/name": "codex-benchmarks",
                "app.kubernetes.io/part-of": "g1736425800",
            },
            "pod_name": "p1",
        },
        "message": "Useless line",
    },
    {
        "kubernetes": {
            "container_name": "deluge-experiment-runner",
            "pod_labels": {
                "app.kubernetes.io/instance": "e2",
                "app.kubernetes.io/name": "codex-benchmarks",
                "app.kubernetes.io/part-of": "g1736425800",
            },
            "pod_name": "p2",
        },
        "message": 'INFO >>{"name":"download","timestamp":"2021-01-01T00:00:00Z",'
        '"value":0.246,"node":"node3","entry_type":"metrics_event"}',
    },
]


class MetricsEvent(LogEntry):
    name: str
    timestamp: datetime.datetime
    value: float
    node: str


class Person(LogEntry):
    name: str
    surname: str


def test_should_produce_logs_for_multiple_experiments():
    parser = LogParser()
    parser.register(MetricsEvent)
    parser.register(Person)

    outputs = InMemoryOutputManager()

    split_logs_in_source(
        log_source=VectorFlatFileSource(
            app_name="codex-benchmarks",
            file=StringIO(make_jsonl(EXPERIMENT_LOG)),
        ),
        log_parser=parser,
        output_manager=outputs,
        group_id="g1736425800",
    )

    assert set(outputs.fs.keys()) == {"e1", "e2"}
    assert compact(outputs.fs["e1"]["metrics_event.csv"].getvalue()) == (
        compact("""
        name,timestamp,value,node
        download,2021-01-01 00:00:00+00:00,0.246,node2
        """)
    )

    assert compact(outputs.fs["e1"]["person.csv"].getvalue()) == (
        compact("""
        name,surname
        John,Doe
        """)
    )

    assert compact(outputs.fs["e2"]["metrics_event.csv"].getvalue()) == (
        compact("""
        name,timestamp,value,node
        download,2021-01-01 00:00:00+00:00,0.246,node3
    """)
    )
