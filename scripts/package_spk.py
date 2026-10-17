"""生成标准 SPK，并复核 checksum、归档权限及关键元数据。"""
import argparse
import copy
import hashlib
import io
import json
import re
import shutil
import tarfile
import tempfile
import time
from pathlib import Path

MODELS={
    'x86_64':'apollolake avoton braswell broadwell broadwellnk broadwellnkv2 broadwellntbap bromolow cedarview denverton epyc7002 epyc7003 epyc7003ntb geminilake geminilakenk grantley icelaked kvmx64 purley r1000 r1000nk v1000 v1000nk x86 x86_64',
    'armv8':'rtd1296 rtd1619b armada37xx armv8',
}
MINIMUM={'7.2':'7.2-64570'}

def archive(root,output,compressed,stamp):
    with tarfile.open(output,'w:xz' if compressed else 'w',format=tarfile.GNU_FORMAT,**({'preset':6} if compressed else {})) as tar:
        for path in sorted(root.rglob('*')):
            member=tar.gettarinfo(str(path),path.relative_to(root).as_posix())
            member.uid=member.gid=0; member.uname=member.gname='root'; member.mtime=stamp
            if not member.issym(): member.mode=0o755
            if member.isfile():
                with path.open('rb') as stream: tar.addfile(member,stream)
            else: tar.addfile(member)

def build(payload,template,version,arch,dsm,out):
    if not re.fullmatch(r'[0-9]+(?:\.[0-9]+){2,3}(?:[ab][0-9]+)?',version): raise ValueError('Invalid version')
    out.mkdir(parents=True,exist_ok=True); stamp=int(time.time())
    with tempfile.TemporaryDirectory() as directory:
        outer=Path(directory)/'outer'; shutil.copytree(template,outer)
        archive(payload,outer/'package.tgz',True,stamp)
        digest=hashlib.md5((outer/'package.tgz').read_bytes()).hexdigest()
        info=(outer/'INFO').read_text(encoding='utf-8')
        values={'version':version,'arch':MODELS[arch],'os_min_ver':MINIMUM[dsm],'checksum':digest,'beta':'yes' if re.search(r'[ab]',version) else 'no',
                'changelog':f'更新 Bambuddy 到 v{version}。原生群晖套件，数据保存在套件 var 目录；请通过套件中心更新。'}
        for key,value in values.items():
            info,count=re.subn(rf'(?m)^{key}=.*$',f'{key}="{value}"',info)
            if count!=1: raise ValueError(f'Missing/duplicate field: {key}')
        (outer/'INFO').write_text(info.rstrip()+'\n',encoding='utf-8')
        name=f'Bambuddy_v{version}_{arch}-DSM{dsm}.spk'; target=out/name
        archive(outer,target,False,stamp)
        with tarfile.open(target) as tar:
            checked=tar.extractfile('INFO').read()
            packed=tar.extractfile('package.tgz').read()
            assert hashlib.md5(packed).hexdigest()==digest
            assert checked.endswith(b'\n') and not checked.endswith(b'\n\n')
            assert b'adminport=' not in checked
            with tarfile.open(fileobj=io.BytesIO(packed),mode='r:xz') as inner:
                members=tar.getmembers()+inner.getmembers()
                for m in members:
                    assert m.uid==m.gid==0 and m.mtime==stamp
                    assert m.issym() or m.mode==0o755
                names=inner.getnames()
                for needed in ('bin/python3.14','bin/start-bambuddy','app/backend/app/main.py','app/static/index.html','share/source/bambuddy-source.tar.gz','ui/config'):
                    assert needed in names,needed
        (out/(name+'.json')).write_text(json.dumps({'version':version,'arch':arch,'dsm':dsm,'checksum':digest,'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'audit':'passed'},indent=2)+'\n')
        print(target)
        return target

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('payload',type=Path); p.add_argument('template',type=Path)
    p.add_argument('version'); p.add_argument('arch',choices=MODELS); p.add_argument('dsm',choices=MINIMUM); p.add_argument('out',type=Path)
    build(**vars(p.parse_args()))
