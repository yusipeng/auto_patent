# -*- coding: utf-8 -*-
"""batch_patent_search.py — 批量 Google Patents 查新检索
用法: cd /d/auto_patent && PYTHONPATH="" .venv_patent/Scripts/python.exe tools/batch_patent_search.py
输出: tools/patent_search_results.json (组名->results 列表)
"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import patent_search as ps

# (组名, 查询词, country, limit)
QUERIES = [
    ("flow_bid", "flow matching bid", "CN", 10),
    ("flow_autobid", '"flow matching" "auto bidding"', "CN", 10),
    ("flow_ad_bid", '"flow matching" advertising bidding', "CN", 10),
    ("gen_bid", "generative bidding advertising", "CN", 10),
    ("diff_bid", "diffusion model bidding advertising", "CN", 10),
    ("dt_bid", "decision transformer bidding", "CN", 10),
    ("autobid_platform", "auto bidding platform advertiser", "CN", 10),
    ("multi_advertiser", "multi advertiser bidding optimization", "CN", 10),
    ("unified_platform", "unified advertising platform bidding", "CN", 10),
    ("video_bid", "video advertisement bidding", "CN", 10),
    ("multiformat", "multi-format advertising bidding", "CN", 10),
]

def run():
    out = {}
    for name, q, country, lim in QUERIES:
        ok = False
        for attempt in range(3):
            try:
                res = ps.search(q, lim, country=country)
                out[name] = res
                print(f"[OK] {name} ({country}) q='{q}': {len(res)} results", flush=True)
                ok = True
                time.sleep(2)
                break
            except Exception as e:
                print(f"[RETRY {attempt+1}] {name}: {e}", flush=True)
                time.sleep(6)
        if not ok:
            out[name] = []
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'patent_search_results.json'), 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("DONE. groups:", len(out))

if __name__ == '__main__':
    run()
