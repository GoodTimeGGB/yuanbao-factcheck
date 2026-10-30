# -*- coding: utf-8 -*-
"""通过 PicGo 本地服务（127.0.0.1:36677/upload）上传正文全部本地图片，
拿到 URL 后按“正文出现顺序”逐个回填，并留一份映射清单便于审计。"""
import json
import os
import re
import shutil
import time

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MD = os.path.join(ROOT, '文章正文-v1.md')
ENDPOINT = 'http://127.0.0.1:36677/upload'
MANIFEST = os.path.join(ROOT, 'data', 'uploaded_urls.json')

IMG = re.compile(r'!\[([^\]]*)\]\(([^)\s]+)\)')
CAP = re.compile(r'\*图\s*(\d+)｜')


def main():
    text = open(MD, encoding='utf-8').read()

    # 1) 按正文顺序收集本地图
    todo = []
    for m in IMG.finditer(text):
        alt, path = m.group(1), m.group(2)
        if path.startswith(('http://', 'https://')):
            continue
        cap = CAP.search(text[m.end(): m.end() + 400])
        todo.append({'alt': alt, 'path': path, 'fig': cap.group(1) if cap else '?'})

    if not todo:
        print('没有需要上传的图片')
        return

    print('待上传 %d 张\n' % len(todo))
    shutil.copy(MD, MD + '.bak')

    # 2) 逐张上传（一张一次请求，确保顺序绝不会错位）
    records = []
    for i, item in enumerate(todo, 1):
        abs_path = os.path.join(ROOT, item['path'])
        if not os.path.exists(abs_path):
            print('  %2d 图%-3s 文件缺失：%s' % (i, item['fig'], item['path']))
            continue
        for attempt in range(3):
            try:
                r = requests.post(ENDPOINT, json={'list': [abs_path]}, timeout=90)
                data = r.json()
                url = (data.get('result') or [None])[0]
                if data.get('success') and url:
                    break
                raise RuntimeError(data)
            except Exception as e:
                url = None
                if attempt == 2:
                    print('  %2d 图%-3s 失败：%s' % (i, item['fig'], e))
                else:
                    time.sleep(2)
        if not url:
            continue
        item['url'] = url
        records.append(item)
        print('  %2d 图%-3s %-30s -> %s' % (i, item['fig'], os.path.basename(item['path']), url))

    # 3) 回填（按原始 path -> url，逐个精确替换，不依赖位置）
    for item in records:
        text = text.replace('(%s)' % item['path'], '(%s)' % item['url'])
    open(MD, 'w', encoding='utf-8').write(text)

    os.makedirs(os.path.dirname(MANIFEST), exist_ok=True)
    old = []
    if os.path.exists(MANIFEST):
        old = json.load(open(MANIFEST, encoding='utf-8'))
    json.dump(old + [{k: v for k, v in r.items()} for r in records],
              open(MANIFEST, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

    print('\n成功 %d 张，映射写入 data/uploaded_urls.json' % len(records))
    print('备份：文章正文-v1.md.bak')


if __name__ == '__main__':
    main()
