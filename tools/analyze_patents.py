# -*- coding: utf-8 -*-
"""analyze_patents.py — 聚合分析查新结果"""
import json, os

path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'patent_search_results.json')
with open(path, encoding='utf-8') as f:
    data = json.load(f)

all_res = {}
for group, results in data.items():
    for r in results:
        pn = r['patent_number']
        if pn not in all_res:
            all_res[pn] = {**r, 'groups': [group]}
        else:
            all_res[pn]['groups'].append(group)

print("总去重专利数:", len(all_res))
print()
for pn, r in all_res.items():
    print(f"--- {pn} | {r['assignee'][:40]}")
    print(f"    groups={r['groups']}")
    print(f"    {r['title'][:90]}")
    ab = r['abstract'][:220].replace('\n', ' ')
    print(f"    {ab}")
