# -*- coding: utf-8 -*-
"""page_count.py — 用 Word COM (pywin32) 统计 docx 页数; 无 pywin32 则给出估算"""
import os, sys
path = sys.argv[1]
try:
    import win32com.client as wc
except ImportError:
    print('NO_PYWIN32')
    sys.exit(0)

word = wc.Dispatch('Word.Application')
word.Visible = False
try:
    d = word.Documents.Open(os.path.abspath(path), ReadOnly=True)
    try:
        n = d.ComputeStatistics(2)  # wdStatisticPages = 2
        print(f'PAGES={n}')
    finally:
        d.Close(False)
finally:
    word.Quit()
