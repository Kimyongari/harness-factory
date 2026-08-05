#!/usr/bin/env bash
# 골든: 오타만 고친다.
set -euo pipefail
cd "$1"
sed -i.bak 's/## Instalation/## Installation/' README.md && rm -f README.md.bak
