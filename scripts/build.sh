#!/usr/bin/env bash
set -Eeuo pipefail
version="${1:?version required}"; arch="${2:?architecture required}"; dsm="${3:?DSM required}"
case "$arch" in x86_64) machine=x86_64 ;; armv8) machine=aarch64 ;; *) exit 1 ;; esac
case "$dsm" in 7.2) image="manylinux_2_28_${machine}" ;; *) echo 'Only DSM 7.2 is supported' >&2; exit 1 ;; esac
repo="$(pwd)"
mkdir -p .build/runtime/payload .build/runtime/venv "dist/${dsm}/${arch}"
cp -a .build/source .build/runtime/source
cp ".build/requirements-${dsm}.lock" .build/runtime/requirements.lock
# 由旧 glibc 基线容器提供可迁移解释器，必要 wheel 使用群晖工具链重编译。
docker run --rm -e DSM="$dsm" -v "$repo:/repo:ro" -v "$repo/.build/runtime:/work" \
  "quay.io/pypa/${image}:latest" bash /repo/scripts/build_runtime.sh
sudo chown -R "$(id -u):$(id -g)" .build/runtime
payload="$repo/.build/runtime/payload"
mkdir -p "$payload/app" "$payload/share/source" "$payload/var/data" "$payload/var/logs"
cp -a .build/source/backend "$payload/app/"
cp -a .build/frontend/static "$payload/app/"
python3 - "$payload/app/static/index.html" <<'PY'
import sys
from pathlib import Path
p=Path(sys.argv[1]); text=p.read_text()
text=text.replace('</body>','<a href="/synology/source" style="position:fixed;bottom:2px;right:6px;z-index:99999;font-size:11px">SPK source / 套件源码</a></body>')
p.write_text(text)
PY
cp -a packages/bambuddy/payload/ui "$payload/"
cp packages/bambuddy/payload/supervisord.conf "$payload/"
install -m 0755 packages/bambuddy/payload/start-bambuddy "$payload/bin/start-bambuddy"
cp .build/UPSTREAM_COMMIT .build/runtime/requirements.lock "$payload/share/source/"
cp LICENSE "$payload/share/source/LICENSE"
# 随包提供修改后的上游源码，前后端均包括，便于遵守 AGPL 和复现。
tar --exclude='__pycache__' --exclude='*.pyc' -czf "$payload/share/source/bambuddy-source.tar.gz" -C .build/source .
python3 scripts/make_icons.py .build/source/frontend/public/img/android-chrome-512x512.png packages/bambuddy/outer "$payload/ui/images"
python3 scripts/package_spk.py "$payload" packages/bambuddy/outer "$version" "$arch" "$dsm" "dist/${dsm}/${arch}"
