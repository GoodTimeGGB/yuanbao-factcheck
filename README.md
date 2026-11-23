# 元宝搜索事实核验 · 可复现实证仓库

配套文章：**《数字是填空，叙述是续写——我用元宝搜索给 AI 技术稿做核验，误报率从 58% 降到 0》**
（正文见 `文章-CSDN终稿.md`，已首发于 CSDN 与公众号「宁的AI小站」）

这个仓库里没有"演示效果"。只有 **220 次真实 SearchPro 调用的原始日志**，和一套能把这些日志重算成文章里每个数字的脚本。

读者不必信我写的，跑一行命令就行。

---

## 30 秒验证

```bash
pip install -r requirements.txt
python scripts/reproduce.py
```

不联网、不消耗额度、耗时约 3 秒，输出（节选，实测）：

```
C1  调用日志  data/calls.jsonl
  总调用 220 次，失败 0 次，中位耗时 440 ms，P90 686 ms
  [PASS]  总调用 = 220 / 失败 = 0 / 中位耗时 ≈440ms

C2  A/B 对照  data/compare.csv × claims_v2.json
  样本 24 条（真 12 / 假 12）
  指标                 对照组(A)    本文做法(B)
  准确率                   54%        75%
  误报率 假→真               58%         0%
  漏报率 真→假               33%         0%
  无证据占比                  0%        25%

C3  四格对照  scripts/eval_four.py
  DeepSeek（检索关）  4/12 (33%)     DeepSeek（检索开）  9/12 (75%)     Gemini（检索开） 11/12 (92%)
  [PASS]  DeepSeek 检索开 = 75%

C5  正文硬性项
  正文 6151 字（去代码块/表格/图片行/图注）
  [PASS]  正文 ≥ 1500 字 / 标题包含元宝搜索 / 图注编号 1–10 连续 / 线上图片 = 10 张

汇总
  共 27 项，通过 27，失败 0
  全部通过：文中每个数字都能用 data/ 下的原始数据重算出来。
```

任何一项对不上，脚本退出码为 1 并列出差异项。

---

## 它到底回答了什么

| 问题 | 证据 | 结论 |
|---|---|---|
| AI 写的技术稿错在哪 | `claims_ds2.json` 逐条对齐 | 9 条错误里 8 条是**数字类**——旧版本号配了新日期 |
| 检索能把数字收敛多少 | `claims_ds2.json` + `draft_verdicts.json` | 33% → 75% → 92%（关检索 / 开检索 / 换个模型开检索） |
| "多搜几条"能提高可信度吗 | `compare.csv` 24 条对照 | 不能。对照组误报率 **58%**，本文做法 **0%**；代价是 25% 说"无证据" |
| 元宝搜索本身稳不稳 | `calls.jsonl` 220 条 | 0 失败，中位 **440 ms**，P90 686 ms，版本 `standard` |
| 为什么不用大模型直接判真假 | 文章 3.1 的 .NET 案例 | 它会因为"日期对得上、来源是微软"就判真 |

一句话：**数字是填空，检索能把空填对；叙述是续写，检索不知道该续哪一句。**

---

## 三档复现

| 档 | 命令 | 联网 | 调用 | 耗时 | 说明 |
|---|---|---|---|---|---|
| **A 只读复核** | `python scripts/reproduce.py` | 否 | 0 | ~3 s | 把文中数字全部重算一遍，推荐先跑这个 |
| **B 单次真实调用** | `python scripts/yb.py "Vue 3.5 released" --mode 0 --site blog.vuejs.org` | 是 | 1 | ~1 s | 须先配 `.env`，见下节 |
| **C 完整重跑 A/B** | `python scripts/compare.py` | 是 | 48 | ~30 s | ⚠️ 会往 `calls.jsonl` **追加** 48 行；想保持 220 的基准，先 `cp data/calls.jsonl data/calls.jsonl.bak` |

### 配置密钥（仅 B / C 档需要）

```bash
# 方式一：环境变量（推荐）
export TENCENTCLOUD_SECRET_ID=AKID...
export TENCENTCLOUD_SECRET_KEY=...

# 方式二：项目根目录 .env（已被 .gitignore 忽略）
cp .env.example .env    # 再填入真实值
```

脚本按 `环境变量 → .env → scripts/.env` 顺序查找，**密钥不进日志、不进原始返回落盘**（`reproduce.py` 的 C6 项会扫一遍）。

---

## 目录结构

```
yuanbao-factcheck/
├── 文章-CSDN终稿.md      # 正文（10 图，图片走 COS 直链）
├── 投稿清单.md             # 逐条对照活动规则的自查表（过程稿，未入库）
├── 实验记录-阶段1~4.md     # 每个阶段的过程记录（含失败的尝试）
├── 预览.html               # 本地渲染预览
├── 配图/                   # fig01–fig10，与正文图号一一对应
├── scripts/                # 19 个脚本，见下表
├── data/
│   ├── calls.jsonl         # ★ 220 条调用日志，运行证据的源头
│   ├── compare.csv         # ★ 24 条 A/B 对照逐条结果
│   ├── claims*.json        # 标注集与三篇 AI 稿的断言
│   ├── draft_verdicts.json # 三篇稿子逐条判定
│   ├── pkg_times_cache.json# npm registry 真值缓存（30 个包全量版本日期）
│   ├── fig_md5.json        # 配图哈希锁
│   └── uploaded_urls.json  # 配图 → COS 地址映射
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## 脚本清单

| 脚本 | 做什么 | 联网 |
|---|---|---|
| `reproduce.py` | **一键复核**：27 项检查，只读 | 否 |
| `tc3.py` | 腾讯云 API 3.0 TC3-HMAC-SHA256 签名 | 否 |
| `yb.py` | SearchPro 调用底座 + JSONL 日志（其余脚本都基于它） | 是 |
| `probe_mode.py` | Mode / Cnt / Site / Freshness 参数边界探针（18 次） | 是 |
| `harvest_truth.py` | 采集 30 个实体的真值候选 | 是 |
| `truth_npm.py` / `refine_truth.py` | 打 npm registry 拿版本发布日期，二次精化 | 是 |
| `gen_claims.py` | 生成 24 条标注集（12 真 / 12 假） | 否 |
| `compare.py` | A/B 两组各自搜、各自判，落 `compare.csv` | 是（48） |
| `probe_claims.py` | 标注集初版试判 | 是 |
| `verify_drafts.py` | 三篇 AI 稿逐条核验 | 是 |
| `eval_four.py` | 四格对照（33/75/92）离线重算 | 否 |
| `trace_one.py` | 单条断言全链路追踪（query → 返回 → 判定） | 是 |
| `stat_calls.py` | 按用途汇总 220 次调用（表 8 的数据源） | 否 |
| `make_figs.py` | 生成 fig01–03、06、07、10 数据图 | 否 |
| `make_screens.py` | 把终端输出渲染成等宽截图（`render_` 前缀，不覆盖真实截图） | 否 |
| `make_preview.py` | 生成 `预览.html` | 否 |
| `check_links.py` | 检查正文图片 / 引用链接可达性 | 是（HEAD） |
| `upload_figs.py` | 经本地 PicGo 服务上传配图 | 是（本地端口） |

## 结论是怎么算出来的

1. **真值**：`truth_npm.py` 直接打 `registry.npmjs.org`，取 30 个包每个版本的发布日期 → `pkg_times_cache.json`。不依赖任何模型的说法。
2. **断言**：`gen_claims.py` 造 24 条，12 条真（版本号与月份都对），12 条假（真版本号配错月份）。
3. **判定**：`compare.py` 让对照组（断言原文直搜）和本文做法（三元组 + 官方域 + 主体对齐）各跑一遍，逐条落 `compare.csv`。
4. **复核**：`reproduce.py` 只读上面三份数据，把准确率 / 误报率 / 漏报率 / 无证据占比重算一遍。

> 注意：`compare.csv` 里的判定是**当时跑出来的结果**，`reproduce.py` 复算的是"从这些结果能不能得出文中那些百分比"，不是重新判定。要重新判定就跑 C 档。

---

## 已知边界（请别把结论读大）

- **24 条是案例，不是估计。** 每格 n=1，33%/75%/92% 说明的是"同一条断言在不同检索条件下会被答成什么样"，不是总体错误率。
- **四格缺一格。** Gemini 网页端默认开检索，没找到关闭开关，所以"Gemini 关检索"这一格是空的。文章 7.2 已写明。
- **`date` 字段不可信。** 部分站点返回占位值（微软支持页恒为 `2025/01/01`），文章 3.2 给了三个实例。判定逻辑对 `date` 做了交叉验证，但没有完全消除这个坑。
- **`Cnt` 只能取 10/20/30/40/50。** 传其他值直接报错，所以"只取前 3 条"做不到。
- **`Mode=1` 加限定词会归零。** 3 次加限定词的试跑全部返回 0 条，而 `Mode=0` / `Mode=2` 相同 query 正常返回。这是选 `Mode=0` 做对照实验的直接原因。
- **`standard` 版不返回 `authority_level`。** 该字段仅旗舰版有，所以证据打分只能退化为站点白名单 + 标题语义，文章 3.3 交代了这个降级。
- **作品阶段是「可演示原型」。** 它审过的三篇稿子是为实验特意让 AI 写的，24 条标注集是为对照特意构造的——都算"跑过"，不算"用起来"。

## 密钥与合规

- `.env` 已被 `.gitignore` 排除；`reproduce.py` 的 C6 项会对全仓做一次 `AKID` 明文扫描。
- 220 条日志只记录 query / 参数 / 耗时 / 条数 / 版本 / 是否报错，**不含密钥、不含完整返回原文**。
- 引用的官方来源、抓取时间见正文文末的来源表；标注集只用了 npm 公开的版本元数据。
- AI 参与环节：正文与代码在 AI 辅助下完成，具体分工见正文文末《AI 使用声明》。

## 引用

元宝搜索（腾讯云 WSA）接口文档：<https://cloud.tencent.com/document/product/1806/121811>
端点 `wsa.tencentcloudapi.com`，`Action=SearchPro`，`Version=2025-05-08`。
