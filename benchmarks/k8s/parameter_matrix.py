import itertools
import json
import sys
from json import JSONDecodeError
from typing import Dict, Any, List


class ParameterMatrix:
    def __init__(self, parameters: Dict[str, Any]):
        self.parameters = parameters

    def expand(self, run_id: bool = False) -> List[Dict[str, Any]]:
        expandable = {k: v for k, v in self.parameters.items() if isinstance(v, list)}
        fixed = {k: v for k, v in self.parameters.items() if k not in expandable}
        expansion = [
            dict(zip(expandable.keys(), values), **fixed)
            for values in itertools.product(*expandable.values())
        ]

        if run_id:
            for i, item in enumerate(expansion, start=1):
                item["runId"] = i

        return expansion


if __name__ == "__main__":

    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} '<json_string>'")
        sys.exit(1)

    try:
        matrix_str = json.loads(sys.argv[1])
    except JSONDecodeError as err:
        print(f"Error decoding JSON: ", err)
        print("Input:", sys.argv[1])
        sys.exit(1)

    print(json.dumps(ParameterMatrix(matrix_str).expand()))
