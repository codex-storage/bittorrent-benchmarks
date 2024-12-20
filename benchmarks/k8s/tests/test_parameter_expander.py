import json

from benchmarks.k8s import parameter_expander as expander
from benchmarks.k8s.parameter_expander import normalize_argo_params


def test_should_expand_simple_parameter_lists():
    matrix = {"a": [1, 2], "b": [3, 4], "c": "foo", "d": 5}

    assert expander.expand(matrix) == [
        {"a": 1, "b": 3, "c": "foo", "d": 5},
        {"a": 1, "b": 4, "c": "foo", "d": 5},
        {"a": 2, "b": 3, "c": "foo", "d": 5},
        {"a": 2, "b": 4, "c": "foo", "d": 5},
    ]


def test_should_add_run_id_when_requested():
    matrix = {"a": [1, 2], "b": [3, 4], "c": "foo", "d": 5}

    assert expander.expand(matrix, run_id=True) == [
        {"a": 1, "b": 3, "c": "foo", "d": 5, "runId": 1},
        {"a": 1, "b": 4, "c": "foo", "d": 5, "runId": 2},
        {"a": 2, "b": 3, "c": "foo", "d": 5, "runId": 3},
        {"a": 2, "b": 4, "c": "foo", "d": 5, "runId": 4},
    ]


def test_should_expand_constrained_parameter_pairs():
    matrix = {"constrained__att1_att2": [[1, [2, 3]], [[4, 5], 6]], "b": [1, 2]}

    assert expander.expand(matrix) == [
        {"att1": 1, "att2": 2, "b": 1},
        {"att1": 1, "att2": 3, "b": 1},
        {"att1": 4, "att2": 6, "b": 1},
        {"att1": 5, "att2": 6, "b": 1},
        {"att1": 1, "att2": 2, "b": 2},
        {"att1": 1, "att2": 3, "b": 2},
        {"att1": 4, "att2": 6, "b": 2},
        {"att1": 5, "att2": 6, "b": 2},
    ]


def test_should_normalize_simple_argo_parameter_list():
    argo_params = json.loads(
        '[{"name":"repetitions","value":"1"},{"name":"fileSize","value":"100MB"},'
        '{"name":"networkSize","value":"5"},{"name":"seeders","value":"1"},'
        '{"name":"seederSets","value":"1"},{"name":"maxExperimentDuration","value":"72h"}]'
    )

    assert normalize_argo_params(argo_params) == {
        "repetitions": 1,
        "fileSize": "100MB",
        "networkSize": 5,
        "seeders": 1,
        "seederSets": 1,
        "maxExperimentDuration": "72h",
    }


def test_should_find_and_pre_expand_lists_encoded_as_strings():
    argo_params = [
        {"name": "a", "value": "[1, 2]"},
        {"name": "b", "value": "[1, [2, 3]]"},
        {"name": "c", "value": "foo"},
    ]

    assert normalize_argo_params(argo_params) == {
        "a": [1, 2],
        "b": [1, [2, 3]],
        "c": "foo",
    }
