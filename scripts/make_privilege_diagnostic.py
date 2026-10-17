"""仅重建外层权限配置，用于 DSM 真机诊断，保留原始 SPK。"""
import hashlib
import io
import json
import tarfile
from pathlib import Path

root=Path(__file__).resolve().parents[1]
source=root/'dist/audit-39001943868/bambuddy-spk-x86_64-7.2/7.2/x86_64/Bambuddy_v1.2.5.7_x86_64-DSM7.2.spk'
out=root/'dist/DSM权限诊断'; out.mkdir(exist_ok=True)
target=out/'Bambuddy_v1.2.5.7_x86_64-DSM7.2_权限启动修复.spk'
assert not target.exists()
privilege={'defaults':{'run-as':'package'},'username':'Bambuddy','groupname':'Bambuddy'}
with tarfile.open(source) as old,tarfile.open(target,'w',format=tarfile.GNU_FORMAT) as new:
    for member in old:
        if member.name=='conf/privilege':
            data=(json.dumps(privilege,indent=2)+'\n').encode(); member.size=len(data)
            new.addfile(member,io.BytesIO(data))
        elif member.name=='scripts/start-stop-status':
            data=(root/'packages/bambuddy/outer/scripts/start-stop-status').read_bytes()
            member.size=len(data); new.addfile(member,io.BytesIO(data))
        else: new.addfile(member,old.extractfile(member) if member.isfile() else None)
with tarfile.open(source) as old,tarfile.open(target) as new:
    for name in old.getnames():
        if old.getmember(name).isfile() and name not in ('conf/privilege','scripts/start-stop-status'):
            assert old.extractfile(name).read()==new.extractfile(name).read(),name
    assert json.load(new.extractfile('conf/privilege'))==privilege
print(target)
