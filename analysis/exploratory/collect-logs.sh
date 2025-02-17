#!/usr/bin/env bash
set -e

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <test-group-id> <output-folder>"
    exit 1
fi

group_id="${1}"
output=${2}

# TODO build auto naming for experiment folders based on metadata
mkdir -p "${output}"

echo "Collect"
kubectl logs --prefix -n codex-benchmarks -l "app.kubernetes.io/part-of=${group_id}" --all-containers --tail=-1 > "${output}/raw-logs.log"

echo "Parse"
python -m benchmarks.cli logs single "${output}/raw-logs.log" "${output}/parsed"