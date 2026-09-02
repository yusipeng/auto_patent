# -*- coding: utf-8 -*-
"""versioned_output.py — 案件产物版本管理
规范: 交底书/检索报告初始为 <发明名称>-交底书V1.docx / <发明名称>-检索报告V1.docx
      每次修改: 复制上一版为 V+1 副本再覆盖写新内容 (旧版永不覆盖)

用法:
  .venv_patent/Scripts/python.exe tools/versioned_output.py <案件04_docx目录> <发明名称> <交底书|检索报告> [--peek]
  --peek 只报告当前最新版本号, 不创建副本

流程:
  1. 首次产出: 直接写 <名称>-<类型>V1.docx
  2. 修改产出: 先 cp 最新版 -> V+1 (留档), 再由调用方把新内容写到 V+1 文件
     本脚本返回应写入的目标路径 (V+1 已由旧版复制占位, 新内容直接覆盖该副本)
"""
import sys, os, re, shutil, glob

def latest_version(docx_dir, inv_name, kind):
    """返回 (最新版本号, 最新文件路径); 无文件返回 (0, None)"""
    pattern = os.path.join(docx_dir, f'{inv_name}-{kind}V*.docx')
    best_v, best_f = 0, None
    for f in glob.glob(pattern):
        m = re.search(r'V(\d+)\.docx$', os.path.basename(f))
        if m:
            v = int(m.group(1))
            if v > best_v:
                best_v, best_f = v, f
    return best_v, best_f

def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    peek = '--peek' in sys.argv
    if len(args) < 3:
        print('用法: versioned_output.py <案件04_docx目录> <发明名称> <交底书|检索报告> [--peek]')
        sys.exit(1)
    docx_dir, inv_name, kind = args[0], args[1], args[2]
    os.makedirs(docx_dir, exist_ok=True)
    v, latest = latest_version(docx_dir, inv_name, kind)
    if peek:
        print(f'CURRENT={v}')
        return
    if v == 0:
        target = os.path.join(docx_dir, f'{inv_name}-{kind}V1.docx')
        print(f'CREATE={target}')
        return
    # 修改: 复制最新版为 V+1, 目标即 V+1
    nv = v + 1
    target = os.path.join(docx_dir, f'{inv_name}-{kind}V{nv}.docx')
    shutil.copy2(latest, target)
    print(f'VERSION={nv}')
    print(f'FROM={latest}')
    print(f'TARGET={target}')

if __name__ == '__main__':
    main()
