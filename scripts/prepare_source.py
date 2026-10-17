"""生成运行依赖清单，并限制 SPK 的程序更新入口。"""
import argparse
import re
from pathlib import Path

def prepare(source: Path):
    runtime = []
    for line in (source/'requirements.txt').read_text(encoding='utf-8').splitlines():
        if re.match(r'^(pytest(?:-asyncio)?|ruff)\b',line.strip(),re.I):
            continue
        runtime.append(line)
    runtime += ['tzdata>=2024.1', 'supervisor==4.3.0']
    (source/'requirements-runtime.in').write_text('\n'.join(runtime)+'\n',encoding='utf-8')
    path=source/'backend/app/api/routes/updates.py'
    text=path.read_text(encoding='utf-8')
    marker='    # Check for managed deployment shapes that own the update lifecycle.'
    if text.count(marker)!=1:
        raise RuntimeError('上游更新入口已变化，需要审核补丁，禁止静默跳过')
    guard='''    # 群晖套件由套件中心更新，不在程序中运行 git、pip 或 npm。
    if os.environ.get("BAMBUDDY_SYNOLOGY") == "1":
        return {"success": False, "message": "Please update Bambuddy through Synology Package Center / 请通过群晖套件中心更新 Bambuddy。"}

'''
    text=text.replace(marker,guard+marker)
    path.write_text(text,encoding='utf-8')
    # 向通过网络访问程序的用户提供本套件实际包含的修改后源码。
    main=source/'backend/app/main.py'
    main.write_text(main.read_text(encoding='utf-8')+'''

# 群晖版本的对应源码下载入口，源归档随 SPK 一起提供。
@app.get("/synology/source", include_in_schema=False)
async def synology_package_source():
    return FileResponse("/var/packages/Bambuddy/target/share/source/bambuddy-source.tar.gz", filename="bambuddy-source.tar.gz")
''',encoding='utf-8')

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('source',type=Path)
    prepare(parser.parse_args().source)
