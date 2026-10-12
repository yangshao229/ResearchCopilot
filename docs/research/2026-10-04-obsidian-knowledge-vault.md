# Obsidian 长期知识库：开源产品拆解

检索日期：2026-10-04。阶段：设计，不代表已经接通 Obsidian，也没有复制下列项目代码。

## 用户问题

目前 ResearchCopilot 能在本地 PDF 阅读器里提问、保存阅读记录、导出论文卡片，但确认过的知识仍分散在项目的运行数据与单向导出文件中。用户希望以 Obsidian 作为可长期储备、检索、关联和跨设备携带的个人论文知识库，同时继续在 ResearchCopilot 阅读原文、核对页码与控制 AI 写入。目标不是把 Obsidian 当 SQL 数据库，也不是只多一个 Markdown 导出按钮。

## 参考项目与一手资料

| 来源 | 直接观察到的机制 | 许可/边界 |
| --- | --- | --- |
| [Open Notebook：Notebooks, Sources, and Notes](https://github.com/lfnovo/open-notebook/blob/main/docs/2-CORE-CONCEPTS/notebooks-sources-notes.md) | 区分来源与可修改笔记；笔记可含引用与来源元数据；回答可经选择转为笔记；其来源归属单一 notebook。 | [MIT](https://github.com/lfnovo/open-notebook/blob/main/LICENSE)。借鉴分层，不照搬单一 notebook 归属。 |
| [Zotero：PDF Reader and Note Editor](https://www.zotero.org/support/pdf_reader)、[Note Templates](https://www.zotero.org/support/note_templates) | 批注进笔记时附引用；从笔记回到 PDF 对应页；模板辅助笔记整理。 | [AGPLv3](https://github.com/zotero/zotero/blob/main/COPYING)。只借鉴交互流程，不复制代码。 |
| [PaperQA2 官方仓库](https://github.com/Future-House/paper-qa) | 科学文献问答围绕证据和引文；解析、索引与回答是处理层，不是人的最终理解。 | [Apache-2.0](https://github.com/Future-House/paper-qa/blob/main/LICENSE)。只借鉴证据链与可重建处理层。 |
| [Karpathy：LLM Wiki 原始构想](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) | 原始资料、持久互链 Markdown wiki、约定文档三层；ingest/query/lint 与 index/log 维护知识积累。 | 这是设计构想而非本项目依赖。其“LLM 完全维护 wiki”不适合未审核的科研结论，改为 AI 提案、用户确认。 |
| [Obsidian 官方数据存储](https://obsidian.md/help/data-storage)、[Properties](https://obsidian.md/help/properties)、[Bases](https://obsidian.md/help/bases/syntax) | Vault 是本地文件夹，Markdown/YAML 存储内容，`.base` 文件提供过滤与表格视图；YAML 属性适合小型原子字段，不适合长篇正文。 | Obsidian 是目标应用，不当作开源代码来源；文件格式应保持普通 Markdown 可用。 |
| [Ink & Switch：Local-first Software](https://www.inkandswitch.com/essay/local-first/) | 本地优先关注离线可用、数据所有权和跨设备并发冲突，而不只是“文件在本地”。 | 研究文章；将冲突处理作为设计要求。 |

## 流程拆解

| 维度 | 成熟做法 | 本项目落点 |
| --- | --- | --- |
| 交互 | Zotero 从批注到笔记再回原文；Open Notebook 将回答显式保存成笔记。 | 阅读仍在 ResearchCopilot，先看 AI 候选与原文引用，再确认入库；Obsidian 负责长期浏览、连接与编辑。 |
| 数据 | 来源与笔记分层；Markdown + 结构化属性可被多种工具读取。 | 原 PDF 和可重建索引不进入 Vault 的必备内容；用户确认的论文卡、心得、问题及关联进入 Vault。 |
| 检索/模型 | PaperQA2 在原文上建索引；Karpathy wiki 用已整理知识作积累层。 | 原文证据检索与已确认知识检索分开；后者可辅助发现，但不能代替论文原文作为实证依据。 |
| 引用 | Zotero 可由笔记返回 PDF；Open Notebook 笔记保留来源。 | 引用必须带稳定论文身份、PDF 内容指纹、原始 PDF 页序号和原文片段；本地可用时点击回到原文。 |
| 隐私 | 本地优先与显式资料选择。 | Vault 和 PDF 默认本机；云端只接收用户同意发送的必要片段，不因入库自动上传。 |
| 失败 | 本地优先需要处理外部修改与设备不同步。 | 写前检查版本；冲突时停止覆盖并显示差异；缺 PDF/坏 YAML/重复 ID 均显式报错。 |

## 对 ResearchCopilot 的取舍

| 决定 | 原因 |
| --- | --- |
| 采用“原文 → 阅读记录 → 人工确认 → 持久知识笔记”的分层 | 防止未经核对的翻译或回答变成知识库事实。 |
| 采用普通 Markdown 正文 + 少量 YAML 属性 + 可选 Obsidian Bases 视图 | 文件可独立阅读、Git 可 diff，不把知识锁在插件或数据库中。 |
| 采用稳定论文 UID 和独立 PDF SHA-256 | 当前 `paper_id` 由相对路径计算；改名/移动/另一台电脑路径差异会破坏引用。 |
| 采用“AI 提案 + 人工确认 + 写前差异预览” | Karpathy 的全自动 wiki 维护适合探索，但科研断言必须由人确认。 |
| 一篇论文只存一份论文笔记，主题是多对多链接 | 不照搬 Open Notebook 的单一 notebook 归属，避免跨主题重复论文和注释。 |
| 暂不把聊天全文、译文缓存、Embedding、索引写进 Vault | 它们量大、可重建或未审定，会污染可信知识层。 |
| 暂不引入 Dataview、社区插件或图数据库 | Obsidian 内置 Bases + Markdown 已覆盖第一阶段的表格筛选；尽量减少依赖。 |

## 架构影响与兼容性

- 复用现有 `Paper`、`SourceDocument`、`ReadingAnchor`、`ReadingRecord`、`KnowledgeArtifact`；Vault 是 `KnowledgeArtifact` 的持久存储适配器，而不是第九个业务对象。
- 当前 `src/research_copilot/paper_library.py` 的 `paper_id` 为相对路径哈希；需先引入不可变 `paper_uid` 并维护旧 ID 映射，不能直接改掉所有旧记录的主键。
- `src/research_copilot/paper_card_compiler.py` 与 `src/research_copilot/reading_history.py` 目前主要是向 `artifacts/` 单向导出；`artifacts/` 被 Git 忽略。这些导出是迁移候选，不应与 Vault 同时被当作“正式笔记”权威来源。
- 当前论文和跨论文：单篇笔记以 `paper_uid` 关联；主题笔记引用多个 `paper_uid` 与各自锚点，但跨论文生成门槛仍须先通过，不因 Obsidian 接入而放开。
- 原文和译文：正式证据锚点只指向原始 PDF；译文标注目标语言、模型和“辅助理解”，不可替换原文引用。
- 不同会话：阅读记录保持会话隔离；入库后以稳定记录 UID 标识，仍保留来源会话 ID 以便追溯。
- 本地和云端：入库/浏览不调用模型；云端翻译问答遵守现有显式调用与最少上传策略。
- macOS 和 Windows：Vault 内不存绝对路径；以稳定 UID + PDF 指纹匹配设备本地 PDF，缺失时保留笔记和页码但显示“原文暂不可用”。

## 数据与隐私边界

正式知识笔记的唯一权威是用户选择的 Vault 文件。原始 PDF 是证据权威；应用数据库/JSON 可做运行状态或迁移缓存，不能成为第二套正式笔记。Vault 路径由用户显式选择，第一版不自动扫描或改写已有 Vault。独立 Vault 推荐单独私有同步/备份；源码 Git、模型缓存、向量索引和密钥与其分开。不能仅因“本地文件”就认为跨设备冲突已解决。

## 实现顺序

1. 设计稿与最小 schema；冻结稳定 UID、来源指纹、引用页码语义和权威归属（本轮）。
2. 只读连接选定 Vault，解析并校验现有笔记；预览旧卡片和阅读记录的迁移，不写文件。
3. 经用户确认，将单篇论文卡和一条已确认阅读记录安全写入 Vault；先比较文件版本，再原子保存，拒绝静默覆盖。
4. 从 Obsidian 外部编辑回读到 ResearchCopilot；展示冲突与手动合并，验证链接跳转。
5. 在真实使用证明需要后，加入主题/概念笔记、Bases 视图、索引与 lint；跨论文自动综合仍受证据门槛约束。
6. 两台设备同步演练，验证同一笔记 UID、PDF 缺失/重定位、冲突与备份恢复。

## 验收标准

- 两篇测试论文即使文件同名、移动目录，Vault 中的论文身份也不变；PDF 内容改变时能够提示版本不符。
- 一条确认过的笔记在 Obsidian 修改后，ResearchCopilot 刷新可读回，不能用旧内容覆盖它。
- 候选 AI 答案未经确认不能自动进入正式知识库；正式事实能看到原文引文和 PDF 页序号。
- Vault 离线可直接用普通 Markdown 打开；未安装 Obsidian 时应用仍可阅读 PDF，连接状态明确显示。
- Windows 缺少对应 PDF 时可读笔记，但回原文按钮解释不可用原因，不显示错误论文。
- 重复 UID、坏 YAML、路径穿越和并发修改均失败关闭并保留原文件。
- 不调用 DeepSeek 就能完成入库、检索已确认笔记和回读；密钥、模型、索引不进入 Vault。

## 暂不实现

不在本轮安装 Obsidian、选择或创建用户 Vault、迁移旧数据、复制第三方代码，也不提供“自动维护整个 wiki”或跨论文未经核对的结论生成。

## 后续实现记录

M8.V1a 已先实现稳定论文身份基础：生成不可变 `paper_uid`，保留旧路径哈希 ID 与相对路径别名，并用独立 `pdf_sha256` 检测内容版本变化。PDF 改名/移动且字节不变时复用 UID；同一路径内容变化时只报告 `changed`，不静默改写已登记指纹。旧 API 继续使用原 `paper_id`，尚未迁移阅读记录、连接 Vault 或写入正式笔记。验收见 [M8.V1a 稳定论文身份验收](../M8_V1A_VALIDATION.md)。

M8.V1b 增加了显式选择后的只读连接与格式校验。YAML 使用 [PyYAML 官方仓库](https://github.com/yaml/pyyaml)的 SafeLoader 扩展并拒绝重复字段；该项目采用 [MIT 许可证](https://github.com/yaml/pyyaml/blob/main/LICENSE)，不复制其源码。只扫 `Papers/`、`Notes/`，不追随符号链接、不读取超大笔记；已核对的旧卡片仅列为候选数。当前用户尚未安装 Obsidian 或创建 Vault，因此只在临时 Vault 测试了连接，没有读取真实用户笔记；见 [M8.V1b 验收](../M8_V1B_VALIDATION.md)。
