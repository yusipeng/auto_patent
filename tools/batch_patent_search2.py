# -*- coding: utf-8 -*-
"""batch_patent_search2.py — 增强查新: 大厂定向 + 全球辖区 + 精化关键词
用法: cd /d/auto_patent && PYTHONPATH="" .venv_patent/Scripts/python.exe tools/batch_patent_search2.py
输出: tools/patent_search_results2.json
"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import patent_search as ps

# (组名, 查询词, country, limit)
QUERIES = [
    # 方法链: 流匹配/生成式出价精化 (CN)
    ("flow_bid_cn", '"flow matching" bid', "CN", 10),
    ("flow_rl_cn", '"flow matching" reinforcement learning', "CN", 10),
    ("flow_ad_cn2", '"flow matching" "real-time bidding"', "CN", 10),
    ("gen_ad_cn", 'generative "auto-bidding" advertising', "CN", 10),
    ("diff_ad_cn2", '"diffusion model" "advertising" bidding', "CN", 10),
    # 大厂定向 (CN)
    ("tencent_bid", '腾讯 广告 出价 自动', "CN", 10),
    ("alibaba_bid", '阿里巴巴 广告 出价 竞价', "CN", 10),
    ("bytedance_bid", '字节跳动 广告 出价 竞价', "CN", 10),
    ("kuaishou_bid", '快手 广告 出价 竞价', "CN", 10),
    ("baidu_bid", '百度 广告 出价 竞价', "CN", 10),
    # 框架链: 平台/多广告主 (CN)
    ("platform_bid_cn", '"auto-bidding" platform advertiser', "CN", 10),
    ("multiagent_bid", 'multi-agent auto bidding advertising', "CN", 10),
    ("floor_price", 'auction "floor price" advertising bidding', "CN", 10),
    # 场景链: 视频/多形态 (CN)
    ("video_bid_cn2", '"video" "auto bidding" advertisement', "CN", 10),
    ("multi_ad_form", '广告 多形态 竞价 统一', "CN", 10),
    # 全球辖区 (US/WO)
    ("flow_bid_us", '"flow matching" bid', "US", 10),
    ("flow_ad_us", '"flow matching" advertising bidding', "US", 10),
    ("gen_bid_us", 'generative "auto-bidding" advertising', "US", 10),
    ("autobid_platform_us", '"auto-bidding" advertising platform', "US", 10),
    ("diff_bid_us", '"diffusion model" bidding advertising', "US", 10),
    ("flow_bid_wo", '"flow matching" bid', "WO", 10),
    ("autobid_wo", 'auto-bidding advertising', "WO", 10),
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
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'patent_search_results2.json'), 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("DONE. groups:", len(out))

if __name__ == '__main__':
    run()
