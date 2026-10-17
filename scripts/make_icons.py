"""使用上游图标生成群晖所需尺寸，不修改商标内容。"""
import sys
from pathlib import Path
from PIL import Image

source, outer, ui = map(Path,sys.argv[1:])
ui.mkdir(parents=True,exist_ok=True)
image=Image.open(source).convert('RGBA')
for size in (16,24,32,48,64,72,96,128,256):
    image.resize((size,size),Image.Resampling.LANCZOS).save(ui/f'icon_{size}.png')
for size,name in ((72,'PACKAGE_ICON.PNG'),(256,'PACKAGE_ICON_256.PNG')):
    image.resize((size,size),Image.Resampling.LANCZOS).save(outer/name)
