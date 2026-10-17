#!/usr/bin/env bash
set -euo pipefail
version="${1:?version required}"
[[ "$version" =~ ^[0-9]+(\.[0-9]+){2,3}([ab][0-9]+)?$ ]] || { echo 'Invalid upstream version'; exit 1; }
mkdir -p .build/source
commit="$(gh api "repos/maziggy/bambuddy/commits/v${version}" --jq .sha)"
[[ "$commit" =~ ^[0-9a-f]{40}$ ]] || exit 1
curl -fL --retry 4 "https://codeload.github.com/maziggy/bambuddy/tar.gz/${commit}" -o .build/upstream.tar.gz
tar -xzf .build/upstream.tar.gz -C .build/source --strip-components=1
printf '%s\n' "$commit" > .build/UPSTREAM_COMMIT
python3 scripts/prepare_source.py .build/source
for dsm in 7.2; do
  platform=x86_64-manylinux_2_28
  uv pip compile .build/source/requirements-runtime.in --python-version 3.14 \
    --python-platform "$platform" --constraint scripts/constraints.txt \
    --no-header --no-annotate -o ".build/requirements-${dsm}.lock"
done
