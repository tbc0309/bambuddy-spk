"""发布前核验正式包与已构建并真机测试的载荷完全一致。"""
import hashlib
import json
import tarfile
from pathlib import Path
from audit_spk import audit

root=Path(__file__).resolve().parents[1]
directory=root/'dist/Bambuddy_v1.2.5.7_DSM7.2_正式版'
manifest=json.loads((directory/'修复校验报告.json').read_text(encoding='utf-8'))
assert len(manifest)==2
reports=[]
for item in manifest:
    source=directory/item['file']
    report=audit(source,expected_sha256=item['sha256'],expected_beta='no')
    old=list((root/'dist/audit-39001943868').rglob(source.name)); assert len(old)==1
    with tarfile.open(old[0]) as before,tarfile.open(source) as after:
        before_hash=hashlib.file_digest(before.extractfile('package.tgz'),'sha256').hexdigest()
        after_hash=hashlib.file_digest(after.extractfile('package.tgz'),'sha256').hexdigest()
        assert before_hash==after_hash
        report['payload_sha256']=after_hash
    reports.append(report)
(directory/'正式发布审计.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
