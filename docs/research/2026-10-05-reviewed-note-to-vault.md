# 经确认的阅读记录入库：开源论文阅读产品拆解

检索日期：2026-10-05。本阶段只实现一条已确认阅读记录的**预览与首次保存**；不迁移旧导出、不批量写入，也不自动生成研究结论。

## 用户问题

ResearchCopilot 已可在 PDF 上提问、核对页码并记录“我的理解”，Obsidian Vault 也已连接，但知识库仍为空。用户需要把自己确认过的一条理解明确存入普通 Markdown，而不能让 AI 回答或旧导出悄悄变成正式笔记。

## 参考项目与一手资料

| 项目 | 观察到的流程 | 本阶段取舍 |
| --- | --- | --- |
| [Open Notebook：Working with Notes](https://github.com/lfnovo/open-notebook/blob/main/docs/3-USER-GUIDE/working-with-notes.md) | 从问答保存笔记时可先编辑、补上下文，再点击保存；文档特别提醒不要保存所有聊天回答。 | 借鉴“选择后保存”，但只允许已有人工确认的个人理解入库。仓库代码为 MIT；不复制代码。 |
| [Zotero：PDF Reader and Note Editor](https://www.zotero.org/support/pdf_reader) | PDF 批注进入笔记后保留可回原文的引用和页码。 | 保留 PDF 文件页序号、原文短引和指纹；不复制 Zotero 实现（AGPL）。 |
| [PaperQA2 官方仓库](https://github.com/Future-House/paper-qa) | 问答以来源和引文为核心，原文检索是处理层。 | 正式笔记不只保存答案文本，必须带原始 PDF 身份和页码；不复制代码（Apache-2.0）。 |
| [Obsidian Properties](https://obsidian.md/help/properties) 与 [数据存储](https://obsidian.md/help/data-storage) | Vault 是本地文件夹，属性在 YAML 中；属性适合简短原子字段，长解释留在正文。 | UID、状态、来源放 YAML，人的理解和引文留在 Markdown 正文。Obsidian 是目标应用，不当作开源代码来源。 |
| [Obsidian Sync 冲突说明](https://obsidian.md/help/sync/troubleshoot) | 多设备会产生冲突，自动合并也可能造成重复或格式问题。 | 本阶段仅首次创建，用原子、排他创建避免覆盖已有笔记；更新与多设备合并留待后续。 |

## 流程与数据拆解

交互：在当前论文的“笔记”页确认个人理解 → 预览最终 Markdown、目标相对路径及原文依据 → 用户再点击保存 → 知识库只读扫描能看到该记录。保存不是模型调用，不能因问答完成而自动触发。

数据：复用 `ReadingRecord`、稳定 `paper_uid`、`pdf_sha256` 与现有 `ObsidianVaultStore`；以阅读记录 ID 生成 `Notes/record-<id>.md`，不新增第二套会话或问答模型。原文引用带 1 起始 PDF 页序号和 PDF 指纹。笔记不包含本机绝对路径、密钥、Embedding 或完整聊天。

失败：未连接 Vault、记录未确认、个人理解为空、无原文引用、PDF 指纹变化、预览后记录变化或目标文件已存在时，拒绝写入；已有文件绝不覆盖。外部改动的回读和正式更新另作下一阶段。

## 对 ResearchCopilot 的取舍与架构影响

- 采用 Open Notebook 的显式“保存好笔记”动作，而非自动批量生成。
- 采用 Zotero 的页码回原文思路，但目前只保存稳定页锚点；跨设备缺 PDF 时应安全降级。
- 采用普通 Markdown + 简短 YAML，不装 Obsidian 插件，也不把 Vault 变成 SQL 服务。
- 现有 `paper_card_compiler.py` 的旧单向导出不改写为正式库；论文卡正式写入留待 M8.V2b，以免产生两份权威文件。
- API 只接受预览摘要作为确认凭据；服务端重新读取记录并重算内容，客户端不能提交任意 Markdown 或目标路径。

## 兼容性矩阵

| 情况 | 本阶段行为 |
| --- | --- |
| 当前单篇 / 跨论文 | 只允许单篇确认记录；跨论文自动主题笔记仍关闭。 |
| 原文 / 译文 | 引用只锚定 PDF 原文；AI 译文不作为正式引用。 |
| 不同会话 | 笔记保留来源会话 ID，但保存后属于该论文的长期知识。 |
| 本地 / 云端 | 入库只做本地文件操作，不调用 DeepSeek。 |
| macOS / Windows | 文件名由稳定记录 ID 生成；Vault 中无设备绝对路径；使用跨平台普通 Markdown 和 YAML。 |

## 验收标准

1. 未确认记录无法预览和保存；有效记录的预览不写 Vault。
2. 用户提交预览摘要后，恰好创建一条笔记；重新扫描能识别它，字段与引文页码正确。
3. 预览后修改记录、断开 Vault、PDF 指纹改变或目标已有文件均失败关闭，原文件字节不变。
4. 无需模型、Obsidian 插件或网络。真实用户 Vault 只在用户于页面亲自确认后写入。

## 暂不实现

已有笔记覆盖/合并、整篇论文卡、自动迁移旧 `artifacts/`、Bases、主题综述和双设备同步。
