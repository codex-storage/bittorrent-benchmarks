#!/usr/bin/env bash
set -e

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <output-folder>"
    exit 1
fi

# TODO build auto naming for experiment folders based on metadata
mkdir -p "${1}"

echo "Collect"
kubectl logs --prefix -n codex-benchmarks -l "app in (deluge-nodes,testrunner)" --tail=-1 > "${1}/raw-logs.log"

echo "Parse"
python -m benchmarks.cli logs "${1}/raw-logs.log" "${1}/parsed"