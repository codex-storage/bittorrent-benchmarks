from benchmarks.k8s.collect_failed_inputs import collect_failed_inputs

API_RESPONSE = {
    "items": [
        {"status": {"no-nodes": []}},
        {
            "status": {
                "nodes": {
                    "codex-benchmark-4pkjd-1084037939": {
                        "templateName": "wrapped-benchmark-experiment",
                        "phase": "Failed",
                        "inputs": {
                            "parameters": [
                                {"name": "groupId", "value": "g1"},
                                {"name": "seeders", "value": "1"},
                                {"name": "repetitions", "value": "5"},
                            ]
                        },
                    },
                    "codex-benchmark-4pkjd-1084037941": {
                        "templateName": "wrapped-benchmark-experiment",
                        "phase": "Failed",
                        "inputs": {
                            "parameters": [
                                {"name": "groupId", "value": "g3"},
                                {"name": "seeders", "value": "1"},
                                {"name": "repetitions", "value": "7"},
                            ]
                        },
                    },
                    "codex-benchmark-4pkjd-1084037940": {
                        "templateName": "some-other-node",
                        "phase": "Succeeded",
                        "inputs": {
                            "parameters": [
                                {"name": "groupId", "value": "g1"},
                                {"name": "seeders", "value": "1"},
                                {"name": "repetitions", "value": "6"},
                            ]
                        },
                    },
                    "codex-benchmark-4pkjd-1118304667": {
                        "templateName": "cleanup",
                        "phase": "Omitted",
                    },
                }
            }
        },
    ]
}


def test_should_extract_parameters_for_failed_nodes_matching_template():
    assert list(
        collect_failed_inputs(
            group_id="g1",
            template="wrapped-benchmark-experiment",
            workflows=API_RESPONSE,
        )
    ) == [{"groupId": "g1", "seeders": 1, "repetitions": 5}]

    assert list(
        collect_failed_inputs(
            group_id="g3",
            template="wrapped-benchmark-experiment",
            workflows=API_RESPONSE,
        )
    ) == [{"groupId": "g3", "seeders": 1, "repetitions": 7}]


def test_should_return_empty_if_no_failing_nodes():
    assert (
        list(
            collect_failed_inputs(
                group_id="g1", template="some-other-node", workflows=API_RESPONSE
            )
        )
        == []
    )


def test_should_return_empty_if_no_matching_group_id():
    assert (
        list(
            collect_failed_inputs(
                group_id="g5", template="some-other-node", workflows=API_RESPONSE
            )
        )
        == []
    )
