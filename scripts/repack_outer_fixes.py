"""将真机验证后的外层修复写入两种架构，不重建 package.tgz。"""
import hashlib
import io
import json
import re
import tarfile
from pathlib import Path

root=Path(__file__).resolve().parents[1]
template=root/'packages/bambuddy/outer'
output=root/'dist/Bambuddy_v1.2.5.7_DSM7.2_正式版'
output.mkdir(exist_ok=True)
descriptions=dict(re.findall(r'^(description(?:_chs)?|beta)="(.*)"$',(template/'INFO').read_text(encoding='utf-8'),re.M))
reports=[]
for source in sorted((root/'dist/audit-39001943868').rglob('*.spk')):
    target=output/source.name
    assert not target.exists(),target
    replacements={name:(template/name).read_bytes() for name in ('conf/privilege','scripts/start-stop-status')}
    with tarfile.open(source) as old,tarfile.open(target,'w',format=tarfile.GNU_FORMAT) as new:
        info=old.extractfile('INFO').read().decode('utf-8')
        for key,value in descriptions.items():
            info,count=re.subn(rf'(?m)^{key}=".*"$',f'{key}="{value}"',info); assert count==1
        replacements['INFO']=(info.rstrip()+'\n').encode()
        for member in old:
            if member.name in replacements:
                data=replacements[member.name]; member.size=len(data)
                new.addfile(member,io.BytesIO(data))
            else: new.addfile(member,old.extractfile(member) if member.isfile() else None)
    with tarfile.open(source) as old,tarfile.open(target) as new:
        for name in old.getnames():
            if old.getmember(name).isfile():
                actual=new.extractfile(name).read()
                assert actual==(replacements[name] if name in replacements else old.extractfile(name).read()),name
        digest=hashlib.md5(new.extractfile('package.tgz').read()).hexdigest()
        assert f'checksum="{digest}"' in new.extractfile('INFO').read().decode()
    with target.open('rb') as stream: sha256=hashlib.file_digest(stream,'sha256').hexdigest()
    reports.append({'file':target.name,'changes':list(replacements),'package.tgz':'字节完全未变','checksum':digest,'sha256':sha256})
    print(target,flush=True)
assert len(reports)==2
(output/'修复校验报告.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
