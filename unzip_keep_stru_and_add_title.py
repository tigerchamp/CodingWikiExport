#!/usr/bin/env python3
import zipfile, os, argparse
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('-r', '--root', required=True)
args = parser.parse_args()


root = Path(args.root)

# ---------- 1. 解压 ----------
for zip_path in root.glob('*.zip'):
    
    print(f'解压 {zip_path} ...')        

    with zipfile.ZipFile(zip_path) as zf:
        root_mds = [n for n in zf.namelist() if n.endswith('.md') and '/' not in n]

        # 计数根目录 md
        # 如果zip文件的根目录中有多个md文件，则解压到extract_dir/zip_name目录；
        # 如果只有一个md文件，则直接解压到extract_dir目录。但zip文件中的目录结构都得保留
    
        if len(root_mds) > 1:
            zf.extractall(root / zip_path.stem)
        else:
            zf.extractall(root)

# 还需要完善，wiki与knowledge导入目录结构不同。
# wiki是 目录名.md加目录（含子文档），因此wiki在脚本处理后，需将目录名.md移入目录，再改名
# knowledge是 目录（目录名.md，与子文档.md）


# ---------- 2. 统一处理所有 md ----------
# 2-1 给所有 md 加标题
for md in root.rglob('*.md'):
    title = md.stem
    md.write_text(f"# {title}\n\n{md.read_text(encoding='utf-8')}", encoding='utf-8')

    # 针对wiki目录下的zip文件进行处理
    # wiki是 目录名.md加目录（含子文档），因此wiki在脚本处理后，需将目录名.md移入目录，再改名
    sub_dir = md.parent / title
    if sub_dir.is_dir():
        new_md = sub_dir / md.name
        md.rename(new_md)

# 2-2 每个目录生成/重命名 README.md

for dir_path in root.rglob('*'):
    if not dir_path.is_dir() or dir_path.name.lower() in ('image', 'knowledge', 'proto', 'file'):
        continue

    dir_name = dir_path.name
    print(dir_path)

    readme_path = dir_path / "README.md"

    # 优先把同名 md 改名
    same_md = dir_path / f"{dir_name}.md"
    if same_md.exists():
        same_md.rename(readme_path)
    elif not readme_path.exists():
        readme_path.write_text(f"# {dir_name}\n", encoding='utf-8')

print("全部完成！")