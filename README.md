# bittorrent-benchmarks

TL;DR: the main outcome of this repository, so far, has been this analysis on the performance 
of Codex versus the [Deluge](https://deluge-torrent.org/) bittorrent client: https://rpubs.com/giuliano_mega/1266876

Scaffolding and experiments for benchmarking Codex against the Deluge bittorrent client.
This is general enough that it could be extended to benchmark Codex against any content
distribution network, including IPFS.

This experimental harness leans on Kubernetes. It is completely possible to run experiments
locally, however, using [Minikube](https://minikube.sigs.k8s.io/) (or Kind, or Docker Desktop).

## Limits

When running experiments locally in a Linux machine, you will likely need to adjust several
of the default OS limits. I won't go into how to make those changes permanent within your
system as there's significant variation across distributions.

**ARP Cache.** The default size for the ARP cache is too small. You should bump it
significantly, e.g.:

```bash
echo 4096 | sudo tee /proc/sys/net/ipv4/neigh/default/gc_thresh1
echo 8192 | sudo tee /proc/sys/net/ipv4/neigh/default/gc_thresh2
echo 16384 | sudo tee /proc/sys/net/ipv4/neigh/default/gc_thresh3
``` 

**inotify.** Kubernetes seems to enjoy watching the filesystem, so
you should increase inotify limits across the board:

```bash
sudo sysctl -w fs.inotify.max_user_instances=2099999999
sudo sysctl -w fs.inotify.max_queued_events=2099999999
sudo sysctl -w fs.inotify.max_user_watches=2099999999
```

**Kernel key retention service.** Kubernetes also places a large number of keys
within the kernel. Make sure you have enough room:

```bash
echo 10000 | sudo tee /proc/sys/kernel/keys/maxkeys
```