#!/usr/bin/env bash

SCRIPT_DIR="$( cd "$(dirname "$(readlink -f $0)")" && pwd )"

"${SCRIPT_DIR}/curate-agents.py" &> /dev/null
"${SCRIPT_DIR}/container-perms.py" &> /dev/null
