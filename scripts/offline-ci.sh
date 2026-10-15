#!/usr/bin/env sh
# Isolate runtime networking, then restore the runner identity and CLI environment.
set -eu
runtime_user=$(id -un)
exec sudo unshare --net -- runuser --user "$runtime_user" -- \
  env PATH="$PWD/.venv/bin:$PATH" "$@"
