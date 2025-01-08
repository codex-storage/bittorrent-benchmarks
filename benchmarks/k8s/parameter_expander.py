"""Simple, self-contained utility for expanding Argo Workflows parameter matrices."""

import itertools
import json
import sys
from json import JSONDecodeError
from typing import Dict, Any, List, Tuple


def expand(parameters: Dict[str, Any], run_id: bool = False) -> List[Dict[str, Any]]:
    simple = {}
    constrained = {}
    fixed = {}

    for k, v in parameters.items():
        if not isinstance(v, list):
            fixed[k] = v
            continue
        if k.startswith("constrained__"):
            constrained[k] = v
        else:
            simple[k] = v

    if not constrained:
        expanded_items = _expand_simple(simple)
    else:
        expanded_items = [
            simple + constrained
            for simple, constrained in itertools.product(
                _expand_simple(simple), _expand_constrained(constrained)
            )
        ]

    final_expansion = [dict(item, **fixed) for item in expanded_items]

    if run_id:
        for i, item in enumerate(final_expansion, start=1):
            item["runId"] = i

    return final_expansion


def _expand_simple(
    expandable: Dict[str, List[Any]],
) -> List[List[Tuple[str, List[Any]]]]:
    keys = expandable.keys()
    return [
        list(zip(keys, list(value_set)))
        for value_set in itertools.product(*expandable.values())
    ]


def _expand_constrained(
    constrained: Dict[str, List[Any]],
) -> List[List[Tuple[str, List[Any]]]]:
    return [
        expansion
        for k, v in constrained.items()
        for expansion in _expand_single_constraint(k, v)
    ]


def _expand_single_constraint(
    combined_key: str, values: List[List[Any]]
) -> List[List[Tuple[str, List[Any]]]]:
    keys = combined_key[len("constrained__") :].split("_")
    if len(keys) < 2:
        raise ValueError(f"Invalid combined key {combined_key}")

    normalized_values = [_normalize_values(value_set) for value_set in values]

    return [
        expansion
        for value_sets in normalized_values
        for expansion in _expand_simple(dict(zip(keys, value_sets)))
    ]


def _normalize_values(values: List[Any | List[Any]]) -> List[List[Any]]:
    return [value if isinstance(value, list) else [value] for value in values]


def normalize_argo_params(argo_params: List[Dict[str, Any]]) -> Dict[str, Any]:
    for param in argo_params:
        try:
            param["value"] = json.loads(param["value"])
        except JSONDecodeError:
            pass

    return {param["name"]: param["value"] for param in argo_params}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} '<json_string>'")
        sys.exit(1)

    try:
        params = normalize_argo_params(json.loads(sys.argv[1]))
        print(json.dumps(expand(params, run_id=True)))
    except JSONDecodeError as err:
        print("Error decoding JSON: ", err)
        print("Input:", sys.argv[1])
        sys.exit(1)
