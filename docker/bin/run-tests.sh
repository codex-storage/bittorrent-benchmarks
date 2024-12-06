#!/usr/bin/env bash
set -e

export DELUGE_NODE_1=deluge-1
export DELUGE_NODE_2=deluge-2
export DELUGE_NODE_3=deluge-3
export TRACKER_ANNOUNCE_URL=http://tracker:8000/announce

# Initializes the shared volume.
echo "Initializing shared volume."
mkdir -p /opt/bittorrent-benchmarks/volume/deluge-{1,2,3}
touch /opt/bittorrent-benchmarks/volume/.initialized

echo "Launching tests."
cd /opt/bittorrent-benchmarks
poetry run pytest --exitfirst
