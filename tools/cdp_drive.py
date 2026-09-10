# -*- coding: utf-8 -*-
"""cdp_drive.py — 通过 CDP 驱动本地 Chrome (9223 端口) 的极简工具
用法:
  python cdp_drive.py goto <url>                  # 新开 tab 导航
  python cdp_drive.py eval <js表达式>              # 当前页执行 JS 并打印结果
  python cdp_drive.py text                          # 打印当前页可见文本
  python cdp_drive.py save <url> <outfile>          # fetch URL 存文件(带浏览器cookie)
  python cdp_drive.py pdf <url> <outfile>           # 导航到 PDF URL 并抓取完整内容
"""
import sys, json, time, base64
import requests
import websocket

PORT = 9223
BASE = f'http://127.0.0.1:{PORT}'

def get_target():
    for t in requests.get(f'{BASE}/json/list', timeout=5).json():
        if t.get('type') == 'page':
            return t['webSocketDebuggerUrl']
    # 没有 page 就建一个
    r = requests.put(f'{BASE}/json/new?about:blank', timeout=5)
    return r.json()['webSocketDebuggerUrl']

def send(ws, method, params=None, timeout=60):
    msg_id = int(time.time() * 1000) % 100000
    ws.send(json.dumps({'id': msg_id, 'method': method, 'params': params or {}}))
    while True:
        r = json.loads(ws.recv())
        if r.get('id') == msg_id:
            return r.get('result', {})

def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return
    ws = websocket.create_connection(get_target(), timeout=90)
    cmd = args[0]
    if cmd == 'goto':
        send(ws, 'Page.enable')
        send(ws, 'Page.navigate', {'url': args[1]})
        time.sleep(5)
        print('NAVIGATED')
    elif cmd == 'eval':
        r = send(ws, 'Runtime.evaluate', {'expression': args[1], 'returnByValue': True, 'awaitPromise': True}, timeout=90)
        v = r.get('result', {})
        if 'value' in v:
            print(v['value'])
        elif 'description' in v:
            print(v['description'])
        else:
            print(json.dumps(r, ensure_ascii=False)[:1000])
    elif cmd == 'text':
        r = send(ws, 'Runtime.evaluate', {'expression': 'document.body ? document.body.innerText.slice(0, 3000) : ""', 'returnByValue': True})
        print(r.get('result', {}).get('value', ''))
    elif cmd == 'title':
        r = send(ws, 'Runtime.evaluate', {'expression': 'document.title + " | " + location.href', 'returnByValue': True})
        print(r.get('result', {}).get('value', ''))
    elif cmd == 'save':
        url, out = args[1], args[2]
        expr = f'''(async () => {{
            const r = await fetch({json.dumps(url)}, {{credentials: 'include'}});
            const b = await r.arrayBuffer();
            const bytes = new Uint8Array(b);
            let bin = ''; for (let i = 0; i < bytes.length; i += 0x8000) bin += String.fromCharCode.apply(null, bytes.subarray(i, i+0x8000));
            return JSON.stringify({{status: r.status, size: b.byteLength, b64: btoa(bin)}});
        }})()'''
        r = send(ws, 'Runtime.evaluate', {'expression': expr, 'returnByValue': True, 'awaitPromise': True}, timeout=120)
        v = r.get('result', {})
        val = v.get('value')
        if val is None:
            print('NO VALUE:', json.dumps(r, ensure_ascii=False)[:300])
            return
        d = json.loads(val)
        print(f'status={d["status"]} size={d["size"]}')
        if d['size'] > 500:
            with open(out, 'wb') as f:
                f.write(base64.b64decode(d['b64']))
            print(f'SAVED {out}')
    elif cmd == 'click':
        expr = f'''(async () => {{
            const els = [...document.querySelectorAll('a,button,div,span')];
            const t = els.find(e => (e.textContent||'').trim() === {json.dumps(args[1])});
            if (!t) return 'NOT_FOUND';
            t.click(); return 'CLICKED';
        }})()'''
        r = send(ws, 'Runtime.evaluate', {'expression': expr, 'returnByValue': True, 'awaitPromise': True})
        print(r.get('result', {}).get('value', ''))
    ws.close()

if __name__ == '__main__':
    main()
