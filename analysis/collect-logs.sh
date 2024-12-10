#!/usr/bin/env bash
set -e

kubectl logs --prefix -n codex-benchmarks -l app=deluge-nodes --tail=-1 > "${1}.log"
grep '\[M' "${1}.log" | tr -s ' ' | cut -d ' ' -f1,7 | sed 's/ /,/' | grep -v 'metric' > "${1}.csv"