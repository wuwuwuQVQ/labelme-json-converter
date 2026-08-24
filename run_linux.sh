#!/bin/sh

set -eu

project_root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
export PYTHONPATH="$project_root/src"
exec python3 -m labelme_json_converter

