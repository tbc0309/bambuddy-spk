"""下载后独立核验两个完整 SPK，不执行包内程序。"""
import argparse
import hashlib
import io
import json
import re
import struct
import tarfile
from pathlib import Path
from package_spk import MODELS

class DigestReader:
    def __init__(self,stream): self.stream=stream; self.digest=hashlib.md5()
    def read(self,size=-1):
        data=self.stream.read(size); self.digest.update(data); return data

def audit(source,expected_sha256=None,expected_beta=None):
    arch='armv8' if '_armv8-' in source.name else 'x86_64'
    if expected_sha256 is None:
        expected_sha256=json.loads(source.with_name(source.name+'.json').read_text(encoding='utf-8'))['sha256']
    with source.open('rb') as stream: sha256=hashlib.file_digest(stream,'sha256').hexdigest()
    assert sha256==expected_sha256
    with tarfile.open(source,'r:') as outer:
        info=outer.extractfile('INFO').read()
        fields=dict(re.findall(r'^([a-z_]+)="(.*)"$',info.decode('utf-8'),re.M))
        assert fields['version']=='1.2.5.7'
        if expected_beta is not None:
            assert fields['beta']==expected_beta
            assert fields['description'].endswith('privilege file.)')
            assert fields['description_chs'].endswith('改为 root。）')
        assert fields['arch']==MODELS[arch]
        assert fields['os_min_ver']=='7.2-64570'
        assert 'adminport' not in fields
        assert info.endswith(b'\n') and not info.endswith(b'\n\n')
        privilege=json.load(outer.extractfile('conf/privilege'))
        assert privilege['defaults']['run-as']=='package'
        assert privilege['username']==privilege['groupname']=='Bambuddy'
        assert 'tool' not in privilege
        setup=outer.extractfile('scripts/service-setup').read()
        assert b'USER="Bambuddy"' in setup and b'EFF_USER="Bambuddy"' in setup
        control=outer.extractfile('scripts/start-stop-status').read()
        assert b'source bin/activate' not in control and b'AutoBangumi' not in control
        stamp=outer.getmember('INFO').mtime
        def metadata(member):
            assert member.uid==member.gid==0,(member.name,'owner')
            assert member.issym() or member.mode==0o755,(member.name,oct(member.mode))
            assert member.mtime==stamp,(member.name,'time')
        for member in outer.getmembers(): metadata(member)
        stream=DigestReader(outer.extractfile('package.tgz'))
        names=set(); count=0; python_ok=False
        with tarfile.open(fileobj=stream,mode='r|xz') as inner:
            for member in inner:
                metadata(member); names.add(member.name.rstrip('/')); count+=1
                if member.name=='bin/python3.14':
                    assert member.isfile() and not member.islnk()
                    header=inner.extractfile(member).read(20)
                    assert header[:4]==b'\x7fELF'
                    assert struct.unpack(('<' if header[5]==1 else '>')+'H',header[18:20])[0]==(183 if arch=='armv8' else 62)
                    python_ok=True
        while stream.read(1024*1024): pass
        assert python_ok and stream.digest.hexdigest()==fields['checksum']
        for required in ('bin/start-bambuddy','app/backend/app/main.py','app/static/index.html','var/data','var/logs','ui/config','supervisord.conf','share/source/bambuddy-source.tar.gz','share/source/requirements.lock'):
            assert required in names,required
        report={'file':source.name,'arch':arch,'version':fields['version'],'os_min_ver':fields['os_min_ver'],'payload_members':count,'checksum':fields['checksum'],'sha256':sha256,'audit':'passed','mode':'0755','owner':'root:root','package_account':'Bambuddy','timestamp':stamp}
        print(json.dumps(report,ensure_ascii=False),flush=True)
        return report

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('directory',type=Path); args=parser.parse_args()
    files=sorted(args.directory.rglob('*.spk')); assert len(files)==2
    reports=[audit(source) for source in files]
    (args.directory/'独立审计报告.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
