from io import StringIO

from benchmarks.logging.sources.vector_flat_file import VectorFlatFileSource
from benchmarks.tests.utils import make_jsonl

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

    assert list(source.logs("e3", "g1736425800")) == []


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
