#!/usr/bin/env sh
# Codex Cloud setup: run from any directory; uv must be on PATH.
set -eu
cd "$(dirname "$0")/.."
uv python install 3.12
uv sync --locked --dev
