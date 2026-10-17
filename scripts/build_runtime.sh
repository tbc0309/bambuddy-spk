#!/usr/bin/env bash
set -Eeuo pipefail
python=/opt/python/cp314-cp314/bin/python
"$python" -m pip install --disable-pip-version-check uv patchelf
"$python" -m venv /work/venv
"$python" -m uv pip install --python /work/venv/bin/python \
  --find-links "/repo/cross-wheels-${DSM}" --no-deps -r /work/requirements.lock
if compgen -G "/repo/cross-wheels-${DSM}/*.whl" >/dev/null; then
  "$python" -m uv pip install --python /work/venv/bin/python --no-deps --reinstall /repo/cross-wheels-${DSM}/*.whl
fi
prefix="$("$python" -c 'import sys; print(sys.base_prefix)')"
cp -a "$prefix/." /work/payload/
# 本套件需要对独立解释器授权，不能授权或修改系统 Python 的符号链接。
rm -f /work/payload/bin/python /work/payload/bin/python3 /work/payload/bin/python3.14
cp -L "$python" /work/payload/bin/python3.14
ln -s python3.14 /work/payload/bin/python
ln -s python3.14 /work/payload/bin/python3
cp -a /work/venv/lib/python3.14/site-packages/. /work/payload/lib/python3.14/site-packages/
find "/repo/cross-wheels-${DSM}" -maxdepth 1 -type f -name '*.so*' -exec cp -L '{}' /work/payload/lib/ \;
PYTHONPATH=/work/source DATA_DIR=/work/test-data LOG_DIR=/work/test-logs \
  /work/venv/bin/python -c 'import numpy, cv2, matplotlib, PIL, asyncpg, fast_simplification, curl_cffi, pypdfium2; import backend.app.main; print("Backend imports OK")'
"$python" /repo/scripts/finalize_runtime.py
# 在模拟套件绝对路径运行解释器，确认修正后的 RPATH 与独立 PythonHOME。
mkdir -p /var/packages/Bambuddy
ln -s /work/payload /var/packages/Bambuddy/target
PYTHONHOME=/work/payload PYTHONPATH=/work/source DATA_DIR=/work/test-data LOG_DIR=/work/test-logs \
  /work/payload/bin/python3.14 -c 'import ssl, sqlite3, cv2, PIL; import backend.app.main; print("Relocated runtime OK")'
"$python" /repo/scripts/smoke_runtime.py
# 真机 DSM 拒绝第三方套件声明 tool capabilities，必须使用普通账户。
# 不通过 root、setcap 或修改系统 sysctl 绕过平台限制。
chmod -R a+rX /work/payload
setpriv --reuid 65534 --regid 65534 --clear-groups \
  env PYTHONHOME=/work/payload /work/payload/bin/python3.14 -c \
  'import os,socket,ssl,sqlite3,cv2,PIL; assert os.geteuid()!=0; s=socket.socket(); s.bind(("127.0.0.1",18000)); s.close(); print("Unprivileged runtime and high port OK")'
