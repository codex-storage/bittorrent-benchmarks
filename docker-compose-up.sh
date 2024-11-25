#!/usr/bin/env bash
set -e

# These have to be wiped out before we boot the containers. Note that this will only work
# if you've set up rootless Docker.
rm -rf ./volume/{deluge-1,deluge-2,deluge-3}
docker compose up