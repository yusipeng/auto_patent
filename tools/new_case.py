# -*- coding: utf-8 -*-
"""new_case.py — 创建新案件目录结构
用法: .venv_patent/Scripts/python.exe tools/new_case.py "<发明名称>"
创建: D:\\auto_patent\\cases\\<发明名称>\\{01_source,02_draft,03_review,04_docx}
"""
import sys, os

CASES = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'cases')

def main():
    if len(sys.argv) < 2:
        print('用法: new_case.py "<发明名称>"')
        sys.exit(1)
    name = sys.argv[1].strip().replace('/', '_').replace('\\', '_')
    case_dir = os.path.join(CASES, name)
    for sub in ['01_source', '02_draft', '03_review', '04_docx']:
        os.makedirs(os.path.join(case_dir, sub), exist_ok=True)
    print(f'OK -> {case_dir}')

if __name__ == '__main__':
    main()
