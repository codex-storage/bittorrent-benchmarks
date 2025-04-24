import json
from io import StringIO
from typing import Tuple

from benchmarks.logging.sources.vector_flat_file import VectorFlatFileSource, PodLog
from benchmarks.tests.utils import make_jsonl
from datetime import datetime

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
        "message": "m1",
        "timestamp": "2025-04-22T13:37:43.001886404Z",
    },
    {
        "kubernetes": {
            "container_name": "deluge-experiment-runner",
            "pod_labels": {
                "app.kubernetes.io/instance": "e1",
                "app.kubernetes.io/name": "codex-benchmarks",
                "app.kubernetes.io/part-of": "g1736425800",
            },
            "pod_name": "p2",
        },
        "message": "m2",
        "timestamp": "2025-04-22T12:37:43.001886404Z",
    },
    {
        "kubernetes": {
            "container_name": "deluge-experiment-runner",
            "pod_labels": {
                "app.kubernetes.io/instance": "e2",
                "app.kubernetes.io/name": "codex-benchmarks",
                "app.kubernetes.io/part-of": "g1736425800",
            },
            "pod_name": "p1",
        },
        "message": "m3",
        "timestamp": "2025-04-22T13:38:43.001886404Z",
    },
]


def test_should_retrieve_events_for_specific_experiments():
    source = VectorFlatFileSource(
        StringIO(make_jsonl(EXPERIMENT_LOG)),
        app_name="codex-benchmarks",
    )

    assert list(source.logs(group_id="g1736425800", experiment_id="e1")) == [
        ("e1", "p1", "m1"),
        ("e1", "p2", "m2"),
    ]

    assert list(source.logs(group_id="g1736425800", experiment_id="e2")) == [
        ("e2", "p1", "m3"),
    ]


def test_should_return_empty_when_no_matching_experiment_exists():
    source = VectorFlatFileSource(
        StringIO(make_jsonl(EXPERIMENT_LOG)),
        app_name="codex-benchmarks",
    )

    assert list(source.logs("g1736425800", "e3")) == []


def test_should_retrieve_events_for_an_entire_group():
    source = VectorFlatFileSource(
        StringIO(make_jsonl(EXPERIMENT_LOG)),
        app_name="codex-benchmarks",
    )

    assert list(source.logs(group_id="g1736425800")) == [
        ("e1", "p1", "m1"),
        ("e1", "p2", "m2"),
        ("e2", "p1", "m3"),
    ]


def test_should_return_all_existing_experiments_in_group():
    extractor = VectorFlatFileSource(
        StringIO(make_jsonl(EXPERIMENT_LOG)),
        app_name="codex-benchmarks",
    )

    assert list(extractor.experiments("g1736425800")) == ["e1", "e2"]


def test_should_read_pod_logs_in_order():
    log_file = StringIO(make_jsonl(EXPERIMENT_LOG))
    log1 = PodLog("p1", log_file)
    log2 = PodLog("p2", log_file)

    def check(
        value: Tuple[str, datetime], expected_message: str, expected_timestamp: str
    ):
        assert json.loads(value[0])["message"] == expected_message
        assert value[1] == datetime.fromisoformat(expected_timestamp)

    assert log1.has_next()
    check(next(log1), "m1", "2025-04-22T13:37:43.001886404Z")
    check(next(log1), "m3", "2025-04-22T13:38:43.001886404Z")
    assert not log1.has_next()

    assert log2.has_next()
    check(next(log2), "m2", "2025-04-22T12:37:43.001886404Z")
    assert not log2.has_next()


def test_should_merge_pod_logs_by_timestamp_when_requested():
    source = VectorFlatFileSource(
        StringIO(make_jsonl(EXPERIMENT_LOG)),
        app_name="codex-benchmarks",
        sorted=True,
    )

    assert list(source.logs("g1736425800")) == [
        ("e1", "p2", "m2"),
        ("e1", "p1", "m1"),
        ("e2", "p1", "m3"),
    ]
