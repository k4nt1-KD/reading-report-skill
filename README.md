# reading-report-skill

给 AI 编码助手（Codex / Claude Code / DSH 等）用的**文献阅读汇报 skill**。你给它一篇论文 PDF 和一个 PPT 模板，它产出一份"内容可溯源、公式图表取自原文、版式贴合模板、交付前整套渲染核对过"的汇报演示文稿。

A reusable *literature-reading presentation* skill: feed it a paper and a slide template, get a deck whose every figure, table and formula is cropped from the paper, whose style follows your template, and which was rendered page by page before delivery.

当前版本：**2.0**（`SKILL.md` 的 `name` 为 `reading-report-skill-2-0`）。

---

## 它解决什么问题

用 AI 做读书报告，常见的坑有五个：

1. **编造结论** —— 正文加进论文里没有的分析、背景和判断。
2. **抄错符号** —— 公式重排时把下标、上标、集合符号写错，观众看不出来、作者本人也未必对得上。
3. **图表糊** —— 自己画"替代比较图"，或用低分辨率截图。
4. **毁模板** —— 整份导入导出把母版、页眉页脚、配色搞坏。
5. **没核对** —— 交付前没逐页看过，溢出、遮挡、裁切留到现场才发现。

2.0 用一条固定流水线把这些堵住：**原图裁剪、模板继承、排版工具箱、渲染核对**。

## 2.0 与 1.0 的差别

| | 1.0 | 2.0 |
| --- | --- | --- |
| 流程 | 九步纪律（文字） | 九步纪律 + 可直接执行的脚本 |
| 素材 | "优先从 PDF 提取原图" | `crop_assets.py`：300 dpi → 归一化坐标 → 墨迹 trim → 公式行带切分 → contact sheet |
| 模板 | "在副本上修改" | `inherit_template.py`：继承上一份 deck 的母版，删页留版式（原模板丢了也能干） |
| 排版 | 靠手感 | `deck_kit.py`：标题/项目符号/卡片/公式行/页码，含已知渲染坑的处理 |
| 核对 | "渲染全部页面" | `verify_deck.py`：越界检查 + 标题序列 + 整套渲染 + 缩略图 |
| 经验 | — | §10 已知坑清单（阴影、页码占位符、段首空格、公式粘连……） |

## 目录结构

```
.
├── SKILL.md                  # 技能主体：流程、house style、已知坑
├── scripts/
│   ├── crop_assets.py        # PDF → 100% 原文素材
│   ├── inherit_template.py   # 复用已通过 deck 的母版
│   ├── deck_kit.py           # python-pptx 版式工具箱
│   ├── verify_deck.py        # 交付前核对
│   └── assets.example.json   # 裁剪规格示例
├── agents/openai.yaml        # 界面元数据与隐式调用策略
├── README.md
├── LICENSE
└── CHANGELOG.md
```

## 安装

Skill 就是一个含 `SKILL.md` 的文件夹，放进助手的 skills 目录即可。

**Codex**

```powershell
git clone https://github.com/k4nt1-KD/reading-report-skill.git "$env:USERPROFILE\.codex\skills\reading-report-skill"
```

**Claude Code**（目录换成你自己的 skills 路径）

```bash
git clone https://github.com/k4nt1-KD/reading-report-skill.git ~/.claude/skills/reading-report-skill
```

**手动安装**：下载本仓库，复制整个文件夹到 skills 目录，确认 `SKILL.md` 位于该文件夹根部。

安装后在对话里说"用 reading-report-skill 2.0 根据这篇论文做汇报"，或依赖自动调用（`agents/openai.yaml` 里已开启 `allow_implicit_invocation`）。

## 怎么用

一句话版本：

```text
使用 reading-report-skill 2.0，根据我提供的论文 PDF 制作文献阅读汇报。
要求：Introduction / Problem Description / Optimization Algorithms / Computational Experiment /
Conclusion / References，公式与约束从原文裁剪并逐条解释，伪代码整页照搬，最后加一页空白"收获"。
先把结构计划给我确认。
```

分三步走更稳：

1. **出计划**：先要章节与每页要点，改完再动手。
2. **出稿**：按确认的结构生成；公式、符号表、伪代码按你要求的完整度呈现。
3. **修订**：把逐页意见（或 PPT 备注）丢回去，它按条落实并重新渲染核对。

配套脚本（可选，供助手在终端里调用）：

```powershell
python scripts/inherit_template.py --base last-approved.pptx --out build/base.pptx --list
python scripts/crop_assets.py --spec build/assets.json          # 见 assets.example.json
python scripts/verify_deck.py --pptx output/deck.pptx --out build/render --sheet build/sheet.png
```

## 已知边界

- 不联网补事实：内容只来自你给的材料。
- 只在论文确实包含伪代码时才搬伪代码；要求"照搬"时不删步骤、不改逻辑、不加旁注。
- 不自己画替代论文证据的比较图或分析图。
- 模板保真优先于机械检查：整份导入导出若明显破坏母版，改为在副本上做局部修订。
- 2.0 的脚本默认 16:9（10 × 5.625 in）；换 4:3 模板需要改常量。

## 自定义

`SKILL.md` 末尾的 **"本项目默认值"** 是作者个人的默认设置（汇报人、学校、学院、章节名、输出目录）。**公开使用前请改成你自己的**，或整节删除——它只在沿用该项目模板时生效。

## 许可

[MIT](LICENSE)
