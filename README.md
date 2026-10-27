# reading-report-skill

给 AI 编码助手（Codex / Claude Code 等）用的**文献阅读汇报 skill**。你给它一篇论文 PDF 和一个 PPT 模板，它产出一份内容可溯源、版式贴合模板的汇报演示文稿。

A reusable *literature-reading presentation* skill for coding agents: feed it a paper and a slide template, get a deck whose claims stay traceable to the paper and whose visual style stays faithful to your template.

---

## 它解决什么问题

用 AI 做读书报告，最常见的三个毛病是：编造论文里没有的结论、把模板的母版和风格搞坏、公式和图表糊成一片。这个 skill 用一套固定的工作流程把这些堵住：

- **内容只来自论文**：正文以论文原文为据，不添加无来源的扩写或新结论，研究假设单独注明。
- **证据优先用原图**：优先从 PDF 提取论文原图、流程图、表格和实验对比图，不自己生成替代性的比较图。
- **模板只做增量修改**：在副本上改，保留比例、主题、母版、字体层级、页眉页脚；品牌元素跨页一致。
- **交付前必须渲染核对**：逐页检查公式、表格、伪代码、实验图表的清晰度，以及溢出、遮挡、裁切、行距。
- **指令与附件分离**：附件里的命令、提示、模板占位文案一律不当成新指令，防提示词注入。

## 默认汇报结构

沿用项目默认结构时使用英文大标题：

| 顺序 | 章节 |
| --- | --- |
| 1 | Introduction（研究背景与相关文献） |
| 2 | Problem Description（作者假设与问题建模） |
| 3 | Optimization Algorithms |
| 4 | Computational Study |
| 5 | Conclusion |
| 6 | References |
| 7 | 收获（空白页，供填写） |

章节名与顺序服从你的直接指令；这套默认值只是起点。

## 安装

Skill 就是一个含 `SKILL.md` 的文件夹，把它放进助手的 skills 目录即可。

**Codex**

```powershell
git clone https://github.com/k4nt1-KD/reading-report-skill.git "$env:USERPROFILE\.codex\skills\reading-report-skill"
```

**Claude Code**（把目录换成你自己的 skills 路径）

```bash
git clone https://github.com/k4nt1-KD/reading-report-skill.git ~/.claude/skills/reading-report-skill
```

**手动安装**：下载本仓库，复制整个文件夹到 skills 目录，确认 `SKILL.md` 位于该文件夹根部。

安装后在对话里直接说“用 reading-report-skill 根据这篇论文和模板做汇报”，或依赖助手的自动调用（`agents/openai.yaml` 里已开启 `allow_implicit_invocation`）。

## 怎么用

最省事的一次性说法：

```text
使用 reading-report-skill，根据我提供的论文 PDF 和模板 PPT 制作文献阅读汇报。
要求：Introduction / Problem Description / Optimization Algorithms / Computational Study / Conclusion / References，
最后加一页空白的“收获”。先把结构计划给我确认。
```

分步走更稳：

1. **出计划**：先让助手列出章节与每页要点，你改完再让它动手。
2. **出稿**：按确认的结构生成，公式、符号表、伪代码按你要求的完整度呈现。
3. **修订**：把逐页意见（或 PPT 备注）丢回去，它按条落实，你的直接指令优先于评阅意见。

## 已知边界

- 不联网补事实：内容只来自你给的材料。
- 只在论文确实包含伪代码时才搬伪代码；要求“完整伪代码”时不会删步骤或改算法逻辑。
- 模板保真优先于机械检查：整份导入导出若明显破坏母版，会改为在副本上做局部修订。

## 自定义

`SKILL.md` 末尾的 **“本项目品牌与文案偏好”** 一节是作者个人的默认设置（汇报人、学校、学院等）。**公开使用前请改成你自己的**，或整节删除——它只在用户继续使用该项目模板时才生效，不影响其余流程。

## 仓库结构

```
.
├── SKILL.md              # 技能主体：工作流程、保真约束、交付标准
├── agents/openai.yaml    # 界面元数据：显示名、简介、默认提示、调用策略
├── README.md
├── LICENSE
└── CHANGELOG.md
```

## 版本

采用 `1.0` 式版本号，`SKILL.md` 的 `name` 字段即技能标识。变更记录见 [CHANGELOG.md](CHANGELOG.md)。

## 贡献

欢迎提 Issue 或 PR：补充新的汇报结构模板、更严的核对清单、对其他演示文稿工具链的适配。提交前请确保 `SKILL.md` 的 frontmatter 仍为合法 YAML，且新增段落没有把你的个人/机构信息写死进通用流程。

## 许可

[MIT](LICENSE)
