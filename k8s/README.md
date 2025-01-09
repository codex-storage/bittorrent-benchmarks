This folder contains the required Kubernetes and Argo Workflow resources required to run experiments in Kubernetes
both in local (e.g. Minikube, Kind) and remote clusters.

## Prerequisites

### Argo Workflows

Whatever cluster you choose must be running [Argo Workflows](https://argo-workflows.readthedocs.io/).

**Local clusters.** For local clusters, you can follow the instructions in
the [Argo Workflows Quickstart Guide](https://argo-workflows.readthedocs.io/en/latest/quick-start/) to get Argo
Workflows running.

For remote clusters, it's best to consult the Argo
Workflows [Operator Manual](https://argo-workflows.readthedocs.io/en/latest/installation/).

**Argo CLI Tool.** You will also need to install the
[Argo CLI tool](https://argo-workflows.readthedocs.io/en/latest/walk-through/argo-cli/) to submit workflows.

**Permissions.** Codex workflows assume that they are running in a namespace called `codex-benchmarks`. We
have a sample manifest which creates the namespace as well as the proper service account with RBAC
permissions [here](./argo-workflows/codex-workflows-rbac.yaml). For local clusters, you can apply this manifest
as it is. For remote clusters, you might need to customize it to your needs.

### Logs

Experiments require logs to be stored for later parsing during analysis. For local clusters, this can be achieved
by running [Vector](https://vector.dev/) and outputting pods logs to a persistent volume. The manifests for setting the
persistent volume, as well as vector,
can be found [here](./local).

### Submitting Workflows

Once everything is set up, workflows can be submitted with:

```bash
argo submit -n argo ./deluge-benchmark-workflow.yaml
```

for local clusters, you should add:

```bash
argo submit -n argo ./deluge-benchmark-workflow.yaml --insecure-skip-verify
```

To observe progress, you can use the Argo Wokflows UI which can be accessed by port-forwarding the Argo Workflows 
server.

