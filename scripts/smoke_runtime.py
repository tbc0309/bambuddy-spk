"""用打包后的解释器进行本地 HTTP 启动和优雅退出测试。"""
import os
import subprocess
import time
import urllib.request
from pathlib import Path

root=Path('/work/payload'); logs=Path('/work/smoke.log')
env=dict(os.environ,PYTHONHOME=str(root),PYTHONPATH='/work/source',DATA_DIR='/work/test-data',LOG_DIR='/work/test-logs',BAMBUDDY_SYNOLOGY='1',MPLCONFIGDIR='/work/test-cache')
with logs.open('w') as stream:
    process=subprocess.Popen([str(root/'bin/python3.14'),'-m','uvicorn','backend.app.main:app','--host','127.0.0.1','--port','18000','--loop','asyncio','--timeout-graceful-shutdown','5'],env=env,cwd='/work/source',stdout=stream,stderr=subprocess.STDOUT)
    try:
        for _ in range(90):
            if process.poll() is not None: raise RuntimeError(logs.read_text())
            try:
                with urllib.request.urlopen('http://127.0.0.1:18000/health',timeout=2) as response:
                    assert response.status==200; break
            except OSError: time.sleep(1)
        else: raise RuntimeError('HTTP startup timeout\n'+logs.read_text())
    finally:
        process.terminate()
        try: process.wait(timeout=20)
        except subprocess.TimeoutExpired:
            process.kill(); process.wait(); raise RuntimeError('Service failed to exit gracefully')
print('HTTP /health and shutdown OK')
