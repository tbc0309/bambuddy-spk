import importlib.util
import json
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from package_spk import build, MODELS
from prepare_source import prepare
from finalize_runtime import library_dirs

class PackagingTests(unittest.TestCase):
    def test_wheel_private_library_dirs(self):
        root=Path('/work/payload')
        modules=[root/'lib/python3.14/site-packages/pillow.libs/libwebp.so',root/'lib/python3.14/site-packages/opencv_python_headless.libs/libavcodec.so']
        paths=library_dirs(root,modules)
        self.assertEqual(paths[0],root/'lib')
        self.assertIn(modules[0].parent,paths)
        self.assertIn(modules[1].parent,paths)
    def test_template_identity(self):
        outer=ROOT/'packages/bambuddy/outer'
        privilege=json.loads((outer/'conf/privilege').read_text())
        self.assertEqual(privilege['username'],'Bambuddy')
        self.assertEqual(privilege['defaults']['run-as'],'package')
        self.assertNotIn('tool',privilege)
        setup=(outer/'scripts/service-setup').read_text(encoding='utf-8')
        self.assertLess(setup.index('EFF_USER="Bambuddy"'),setup.index('SERVICE_PORT='))
        self.assertNotIn('export LD_LIBRARY_PATH',setup)
        control=(outer/'scripts/start-stop-status').read_text(encoding='utf-8')
        self.assertNotIn('source bin/activate',control)
        self.assertNotIn('AutoBangumi',control)
    def test_spk_all_platforms(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); payload=root/'payload'
            for name in ('bin/python3.14','bin/start-bambuddy','app/backend/app/main.py','app/static/index.html','share/source/bambuddy-source.tar.gz','ui/config'):
                p=payload/name; p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(b'test fixture')
            for arch in MODELS:
                for dsm in ('7.2',):
                    result=build(payload,ROOT/'packages/bambuddy/outer','1.2.5.7',arch,dsm,root/'out')
                    with tarfile.open(result) as t:
                        info=t.extractfile('INFO').read().decode()
                        self.assertIn(f'arch="{MODELS[arch]}"',info)
                        self.assertNotIn('adminport=',info)
    def test_upstream_guard(self):
        with tempfile.TemporaryDirectory() as d:
            source=Path(d); route=source/'backend/app/api/routes/updates.py'; route.parent.mkdir(parents=True)
            route.write_text('async def apply_update():\n    # Check for managed deployment shapes that own the update lifecycle.\n    return {}\n')
            (source/'requirements.txt').write_text('fastapi>=0.1\npytest>=9\nruff>=0.8\n')
            (source/'backend/app/main.py').write_text('')
            prepare(source)
            self.assertIn('BAMBUDDY_SYNOLOGY',route.read_text(encoding='utf-8'))
            self.assertNotIn('pytest',(source/'requirements-runtime.in').read_text())

if __name__=='__main__': unittest.main()
