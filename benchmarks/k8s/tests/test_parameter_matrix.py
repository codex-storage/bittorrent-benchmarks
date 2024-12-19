from benchmarks.k8s.parameter_matrix import ParameterMatrix


def test_should_expand_simple_parameter_lists():
    matrix = ParameterMatrix(
        {
            "a": [1, 2],
            "b": [3, 4],
            "c": "foo",
            "d": 5
        }
    )

    assert matrix.expand() == [
        {"a": 1, "b": 3, "c": "foo", "d": 5},
        {"a": 1, "b": 4, "c": "foo", "d": 5},
        {"a": 2, "b": 3, "c": "foo", "d": 5},
        {"a": 2, "b": 4, "c": "foo", "d": 5},
    ]

def test_should_add_run_id_when_requested():
    matrix = ParameterMatrix(
        {
            "a": [1, 2],
            "b": [3, 4],
            "c": "foo",
            "d": 5
        }
    )

    assert matrix.expand(run_id=True) == [
        {"a": 1, "b": 3, "c": "foo", "d": 5, "runId": 1},
        {"a": 1, "b": 4, "c": "foo", "d": 5, "runId": 2},
        {"a": 2, "b": 3, "c": "foo", "d": 5, "runId": 3},
        {"a": 2, "b": 4, "c": "foo", "d": 5, "runId": 4},
    ]