# -*- coding: utf-8 -*-
"""把正文渲染成本地预览页，用来在投稿前整篇核对（图片已为线上 URL）。"""
import os
import re

import markdown

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MD = os.path.join(ROOT, '文章正文-v1.md')
OUT = os.path.join(ROOT, '预览.html')

text = open(MD, encoding='utf-8').read()
html = markdown.markdown(
    text,
    extensions=['tables', 'fenced_code', 'toc', 'sane_lists'],
)

css = '''
:root{--ink:#1a1a1a;--muted:#6b7280;--line:#e5e7eb;--bg:#fff;--code:#f6f8fa;}
*{box-sizing:border-box}
body{margin:0;background:#f3f4f6;color:var(--ink);
 font:16px/1.85 -apple-system,"Segoe UI","Microsoft YaHei",sans-serif;}
.page{max-width:840px;margin:0 auto;background:var(--bg);padding:56px 64px 96px;
 box-shadow:0 1px 3px rgba(0,0,0,.08);}
h1{font-size:26px;line-height:1.5;margin:0 0 8px;letter-spacing:-.01em;}
h2{font-size:21px;margin:44px 0 14px;padding-bottom:8px;border-bottom:2px solid var(--line);}
h3{font-size:17px;margin:30px 0 10px;color:#111;}
p{margin:14px 0;}
strong{color:#000;}
blockquote{margin:18px 0;padding:12px 18px;background:#f8fafc;border-left:3px solid #94a3b8;
 color:#374151;border-radius:0 4px 4px 0;}
blockquote p{margin:6px 0;}
code{background:var(--code);padding:2px 6px;border-radius:4px;font-size:13.5px;
 font-family:"Cascadia Mono",Consolas,monospace;color:#b91c1c;}
pre{background:var(--code);padding:16px 18px;border-radius:8px;overflow:auto;border:1px solid var(--line);}
pre code{background:none;padding:0;color:#1f2937;font-size:13px;line-height:1.65;}
table{border-collapse:collapse;width:100%;margin:20px 0;font-size:14.5px;}
th,td{border:1px solid var(--line);padding:9px 12px;text-align:left;vertical-align:top;}
th{background:#f8fafc;font-weight:600;}
tr:nth-child(even) td{background:#fcfcfd;}
img{max-width:100%;display:block;margin:24px auto 8px;border:1px solid var(--line);border-radius:6px;}
em{color:var(--muted);font-style:normal;font-size:14px;display:block;text-align:center;margin:0 0 26px;}
hr{border:0;border-top:1px solid var(--line);margin:40px 0;}
ul,ol{padding-left:26px;}
li{margin:7px 0;}
.ribbon{max-width:840px;margin:0 auto;padding:14px 64px 0;color:var(--muted);font-size:13px;}
'''

body = html
html_full = ('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
             '<meta name="viewport" content="width=device-width,initial-scale=1">'
             '<title>征文预览</title><style>%s</style></head><body>'
             '<div class="ribbon">本地预览 · 图片为线上 COS 链接 · 正文 %d 字</div>'
             '<div class="page">%s</div></body></html>'
             % (css, len(re.findall(r'[\u4e00-\u9fa5]', text)), body))

open(OUT, 'w', encoding='utf-8').write(html_full)
print('已生成：', OUT)
print('图片标签数：', html.count('<img'))
