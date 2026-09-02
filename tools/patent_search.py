# -*- coding: utf-8 -*-
"""patent_search.py — Google Patents 检索 (走 Clash 代理 127.0.0.1:7897)
用法: .venv_patent/Scripts/python.exe tools/patent_search.py "<query>" [limit]
输出: JSON 行到 stdout (title/patent_number/assignee/filing_date/publication_date/abstract)
注意: Google Patents 页面为 JS 渲染, 此脚本用 XHR 接口; 失败时提示改用浏览器工具
"""
import sys, os, json, time
import requests

PROXY = {'http': 'http://127.0.0.1:7897', 'https': 'http://127.0.0.1:7897'}
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36',
    'Accept': 'application/json',
}

def search(query, limit=10, country='CN'):
    url = 'https://patents.google.com/xhr/query'
    params = {
        'url': f'q={query}&country={country}&num={limit}',
    }
    r = requests.get(url, params=params, headers=HEADERS, proxies=PROXY, timeout=30)
    r.raise_for_status()
    data = r.json()
    results = []
    for item in data.get('results', {}).get('cluster', [{}])[0].get('result', []):
        p = item.get('patent', {})
        results.append({
            'title': p.get('title', ''),
            'patent_number': p.get('publication_number', ''),
            'assignee': p.get('assignee', ''),
            'inventor': p.get('inventor', ''),
            'filing_date': p.get('filing_date', ''),
            'priority_date': p.get('priority_date', ''),
            'publication_date': p.get('publication_date', ''),
            'grant_date': p.get('grant_date', ''),
            'abstract': p.get('snippet', ''),
            'url': f"https://patents.google.com/patent/{p.get('publication_number', '')}",
        })
    return results

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('用法: patent_search.py "<query>" [limit]')
        sys.exit(1)
    q = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    try:
        for r in search(q, limit):
            print(json.dumps(r, ensure_ascii=False))
    except Exception as e:
        print(f'ERROR: {e}', file=sys.stderr)
        sys.exit(2)
