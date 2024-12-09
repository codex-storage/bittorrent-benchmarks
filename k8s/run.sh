#!/usr/bin/env bash
#
# Simple script for running benchmark experiments on a Kubernetes cluster.
set -e

function on_interrupt () {
  read -p "CTRL+C pressed. Do you want to stop the test runner as well? [y/N] " -n 1 -r
  echo ""
  if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Deleting experiment namespace..."
    kubectl delete namespace codex-benchmarks
  fi
}

trap on_interrupt INT

echo " * Clearing previous deployments"
kubectl delete namespace codex-benchmarks || true

echo " * Deploying manifests"
while read -r resource; do
   kubectl apply -f "${resource}"
done < deploy-order.txt

echo " * Awaiting for test runner to start"
kubectl wait --for=condition=Ready --selector=app=testrunner pod -n codex-benchmarks --timeout=300s

echo " * Attaching to test runner logs"
TESTRUNNER_POD=$(kubectl get pods -n codex-benchmarks -l app=testrunner -o jsonpath="{.items[0].metadata.name}")
if [ -z "${TESTRUNNER_POD}" ]; then
  echo "Testrunner pod not found"
  exit 1
fi

kubectl logs -f "${TESTRUNNER_POD}" -n codex-benchmarks

echo " * Test runner has finished."