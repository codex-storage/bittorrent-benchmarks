"""Queries the Argo Workflows API and collects inputs for failed nodes matching a given template name and group ID.
We need this because Argo will not respect parallelism in retries, so we spin the retry as a new workflow."""

import sys
from typing import Dict, Any

import requests
import json

from benchmarks.k8s.parameter_expander import normalize_argo_params


def collect_failed_inputs(group_id: str, template: str, workflows: Dict[str, Any]):
    def _belongs_to_group(pars):
        for parameter in pars:
            if (
                parameter.get("name") == "groupId"
                and parameter.get("value") == group_id
            ):
                return True
        return False

    for workflow in workflows["items"]:
        for key, node in workflow["status"].get("nodes", {}).items():
            if node.get("templateName") != template:
                continue

            if node.get("phase") != "Failed":
                continue

            parameters = node.get("inputs", {}).get("parameters", {})
            if not parameters:
                continue

            if not _belongs_to_group(parameters):
                continue

            yield normalize_argo_params(parameters)


if __name__ == "__main__":
    if len(sys.argv) != 5:
        print(
            "Usage: collect_failed_inputs.py <group_id> <template> <argo_api_host> <argo_api_port>"
        )
        sys.exit(1)

    group_id, template, argo_api_host, argo_api_port = sys.argv[1:]
    workflows = requests.get(
        f"https://{argo_api_host}:{argo_api_port}/api/v1/workflows/argo", verify=False
    ).json()
    print(json.dumps(list(collect_failed_inputs(group_id, template, workflows))))
