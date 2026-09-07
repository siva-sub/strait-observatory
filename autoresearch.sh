#!/usr/bin/env bash
# Changi bench: fetch S2 (cached) -> detect per zone -> join CAAS cargo -> r/n
set -euo pipefail
cd "$(dirname "$0")"
.venv/bin/python experiments/changi_bench.py
