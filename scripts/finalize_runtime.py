"""收集运行库、修正可迁移路径并检查 DSM ABI，不替换系统 libc。"""
import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

ROOT=Path('/work/payload')
TARGET=Path('/var/packages/Bambuddy/target')
BASELINE=re.compile(r'^(?:lib(?:c|m|pthread|dl|rt|resolv|util|nsl|anl|z)\.so\.|ld-linux)')

def elf(path):
    if not path.is_file() or path.is_symlink(): return False
    with path.open('rb') as stream: return stream.read(4)==b'\x7fELF'

def run(*args):
    return subprocess.check_output(args,text=True).strip()

def library_dirs(root, modules):
    # auditwheel 将共享库放在 pillow.libs、opencv_python_headless.libs 等目录。
    # 单独检查这些库时，不能依赖父扩展模块的 RPATH。
    return [root/'lib']+sorted({p.parent for p in modules if '.so' in p.name and p.parent!=root/'lib'})

def main():
    lib=ROOT/'lib'; copied={}
    modules=[p for p in ROOT.rglob('*') if elf(p)]
    search=library_dirs(ROOT,modules)
    env=dict(os.environ,LD_LIBRARY_PATH=':'.join(map(str,search)))
    queue=list(modules)
    while queue:
        module=queue.pop()
        result=subprocess.run(['ldd',str(module)],capture_output=True,text=True,env=env)
        if 'not found' in result.stdout: raise RuntimeError(f'Unresolved ELF dependency: {module}\n{result.stdout}')
        for name,path in re.findall(r'^\s*(\S+)\s+=>\s+(/\S+)\s+\(',result.stdout,re.M):
            source=Path(path).resolve()
            if BASELINE.match(name) or source.is_relative_to(ROOT): continue
            target=lib/name
            if target.exists() and target.read_bytes()!=source.read_bytes():
                raise RuntimeError(f'Conflicting library: {name}')
            if name not in copied:
                shutil.copy2(source,target); copied[name]=hashlib.sha256(target.read_bytes()).hexdigest()
                queue.append(target)
    # 文件 capabilities 触发安全加载模式，不能依赖 LD_LIBRARY_PATH。
    # 使用套件绝对 RPATH，并保留 wheel 自带库目录的对应路径。
    for module in [p for p in ROOT.rglob('*') if elf(p)]:
        dynamic=subprocess.run(['patchelf','--print-rpath',str(module)],capture_output=True,text=True)
        if dynamic.returncode: continue
        paths=[str(TARGET/path.relative_to(ROOT)) for path in search]
        for entry in dynamic.stdout.strip().split(':'):
            if not entry: continue
            if '$ORIGIN' in entry or '${ORIGIN}' in entry:
                local=Path(entry.replace('${ORIGIN}',str(module.parent)).replace('$ORIGIN',str(module.parent))).resolve()
                if local.is_relative_to(ROOT): paths.append(str(TARGET/local.relative_to(ROOT)))
            elif entry.startswith(str(ROOT)):
                paths.append(str(TARGET/Path(entry).relative_to(ROOT)))
        subprocess.run(['patchelf','--force-rpath','--set-rpath',':'.join(dict.fromkeys(paths)),str(module)],check=True)
        symbols=run('readelf','--version-info',str(module))
        versions=[tuple(map(int,x.split('.'))) for x in re.findall(r'(?<![A-Z_])GLIBC_(\d+\.\d+)',symbols)]
        limit=(2,17) if os.environ['DSM']=='7.1' else (2,28)
        if versions and max(versions)>limit: raise RuntimeError(f'{module}: GLIBC {max(versions)} exceeds DSM {limit}')
    (ROOT/'RUNTIME-LIBRARIES.json').write_text(json.dumps(copied,indent=2)+'\n')
    for path in ROOT.rglob('*.pyc'): path.unlink()
    for path in ROOT.rglob('*.a'): path.unlink()

if __name__=='__main__': main()
