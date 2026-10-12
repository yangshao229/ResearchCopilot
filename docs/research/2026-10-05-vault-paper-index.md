# 正式论文卡作为已确认笔记索引：开源产品拆解

检索日期：2026-10-05。范围是 ResearchCopilot 与 Obsidian 的单篇论文知识闭环，不新增模型调用或第二套研究数据库。

## 用户问题

目前阅读记录可逐条审阅并存入 Vault，但没有一篇论文的正式入口。旧 `artifacts/paper_cards/` 导出会复制 AI 回答，不能与 Obsidian 中可编辑的正式知识并列为权威卡片。用户应能从论文出发，看到自己确认过的笔记，建立一张可迁移、可在 Obsidian 中继续编辑的索引卡。

## 参考项目与一手资料

| 项目 | 已验证的成熟做法 | 对本项目的取舍 |
| --- | --- | --- |
| [Open Notebook：Working with Notes](https://github.com/lfnovo/open-notebook/blob/main/docs/3-USER-GUIDE/working-with-notes.md) | 区分原始 source 与可修改的 note；从聊天保存时还要补标题和上下文。 | 保留“原文 PDF／人工知识”边界，拒绝自动把 AI 回答变成卡片。MIT 项目，只借鉴流程，不复制代码。 |
| [Zotero：PDF Reader and Note Editor](https://www.zotero.org/support/pdf_reader) | 从 PDF 标注加入笔记时可回到原文页，并保留引文。 | 页码、PDF 指纹继续留在各条笔记中；论文卡链接笔记，不复制全文和 PDF。Zotero 代码通常为 AGPL，不复制。 |
| [PaperQA 官方仓库](https://github.com/Future-House/paper-qa) | 科学文档问答强调引文来源，PDF 由使用者提供。 | 原文问答继续走既有 RAG；长期卡片只索引有原文引用且经人确认的记录。仓库为 Apache-2.0，不复制代码。 |
| [Obsidian 官方链接文档](https://obsidian.md/help/links)及[Properties](https://obsidian.md/help/properties) | 可以用带文件夹路径的普通 Markdown 链接；YAML 属性适合短字段。 | `Papers/<paper_uid>.md` 用相对 Markdown 链接指向 `Notes/record-*.md`，即使没有 Obsidian 插件仍可读。Obsidian 产品文档不是开源代码来源。 |

## 流程、数据与失败处理

PDF 阅读 → 人工确认含页码引用的阅读记录 → 逐条预览并存入 `Notes/` → 在“总结”页预览论文索引卡 → 用户再次确认 → 首次创建 `Papers/<paper_uid>.md`。论文卡只列出已经保存在当前 Vault 的同一 `paper_uid` 笔记。旧 `paper_card_compiler` 的下载能力暂留兼容，不在主要页面与正式卡并列。

前端不提交卡片正文或文件路径，只提交预览摘要；后端重新扫描 Vault 并构建 Markdown。预览摘要绑定 Vault 路径与卡片内容；断开／切换 Vault、笔记新增／删除／改名、PDF 版本变化、目标文件已存在、重复 UID 或无有效笔记时拒绝写入。目标采用排他创建，永不覆盖 Obsidian 修改。无需访问 DeepSeek、网络、Embedding 或本机绝对 PDF 路径。

## 架构影响与取舍

- 复用既有 `PaperSummary` 身份、`VaultNote`、`ObsidianVaultStore` 和 Vault 扫描；不增加第九个核心对象或另一套索引存储。
- `PaperCardCompiler` 仍可解析旧导出，但不是正式卡写入器；正式卡仅由 Vault 中现存笔记生成，避免同一理解有两个权威正文。
- 不将“已确认的旧 JSON 记录”直接列入卡片：确认记录和正式入库是两个不同动作。
- 不自动更新已有论文卡。Obsidian 的编辑是人的工作；后续若要更新，必须先回读再显示差异并校验版本。

## 兼容性矩阵

| 情况 | 行为 |
| --- | --- |
| 当前论文／跨论文 | 仅为当前论文建卡；跨论文主题笔记仍独立。 |
| 原文／译文 | 正式链接的笔记锚定 PDF 原文页；机器译文不作为引用。 |
| 不同会话 | 同一论文的已入库笔记可汇总为一张卡；不会串到另一篇。 |
| 本地／云端 | 纯本地文件写入，无模型调用。 |
| macOS／Windows | 相对 Markdown 路径和稳定 UID；不写设备绝对路径。 |

## 验收标准

1. 无已保存笔记、PDF 指纹过期、Vault 未连接时不能生成正式卡；预览不写文件。
2. 首次确认恰好创建一张 `Papers/<paper_uid>.md`，扫描可识别，卡片链接均指向已存在的同论文笔记。
3. 预览后笔记或 Vault 发生变化、目标已存在、重复 UID、无效文件时拒绝保存，原文件字节不变。
4. 页面清楚区分“旧导出”和“正式 Vault 论文卡”，后者可在 Obsidian 继续编辑。

## 暂不实现

自动摘要、批量迁移、自动覆盖、双向合并、Bases 视图、云同步与 Windows PDF 配对；这些需要独立验收，不能随着一个按钮暗中引入。
