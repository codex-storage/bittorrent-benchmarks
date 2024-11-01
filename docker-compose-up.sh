#!/usr/bin/env bash
set -e

# These have to be wiped out before we boot the containers.
rm -rf ./volume/{deluge-1,deluge-2}
docker compose up