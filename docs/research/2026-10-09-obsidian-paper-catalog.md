# Obsidian 论文目录首次入库：开源产品拆解

检索日期：2026-10-09。关联已有[知识库架构拆解](2026-10-04-obsidian-knowledge-vault.md)与[人工确认论文卡拆解](2026-10-05-vault-paper-index.md)。

## 用户问题

ResearchCopilot 已连接用户的 Obsidian Vault，但 Vault 没有正式笔记，因此 Obsidian 打开后仍是空的。现有逻辑要求先完成问答、写个人理解、核对证据、保存笔记，才允许创建论文卡。用户要先看到**已导入哪些论文**，再逐渐积累阅读笔记；不能为了填满目录而伪造 AI 结论或把未经确认的旧卡片冒充正式知识。

## 参考项目与一手资料

| 项目 | 官方资料与成熟做法 | 许可证和取舍 |
| --- | --- | --- |
| [Open Notebook](https://github.com/lfnovo/open-notebook/blob/main/docs/2-CORE-CONCEPTS/notebooks-sources-notes.md) | Source 与可修改 Note 是不同对象；来源进入资料库并不意味着已经有人工总结。 | [MIT](https://github.com/lfnovo/open-notebook/blob/main/LICENSE)；借鉴边界，不复制代码。 |
| [Zotero](https://www.zotero.org/support/pdf_reader) | PDF 在资料条目中先有位置，随后才把有来源链接的批注纳入笔记；笔记可回溯原文。 | [AGPLv3](https://github.com/zotero/zotero/blob/main/COPYING)；借鉴资料条目先于笔记的工作流，不复制代码。 |
| [PaperQA2](https://github.com/Future-House/paper-qa) | 文献原文是回答的证据来源，索引和问答产物不是经人确认的研究结论。 | [Apache-2.0](https://github.com/Future-House/paper-qa/blob/main/LICENSE)；只借鉴来源／证据分层，不新增依赖。 |
| [Obsidian Bases 官方语法](https://obsidian.md/help/bases/syntax)、[视图](https://obsidian.md/help/bases/views)、[Properties](https://obsidian.md/help/properties) | `.base` 是 YAML 视图定义；Markdown 属性是表格可筛选字段，Bases 默认面对整个 Vault，需显式过滤。 | 仅使用 Obsidian 内置功能；`.md` 没有 Obsidian 仍可读。 |

## 流程与设计取舍

| 维度 | 决定 |
| --- | --- |
| 交互 | 在已连接 Vault 的网页侧栏显示“预览论文目录入库”，列出将创建的来源条目；用户确认后一次创建。以后新导入 PDF 可再次执行，已存在文件不覆盖。 |
| 数据 | `Sources/<paper_uid>.md` 仅记录现有 `PaperSummary` 的稳定 UID、PDF SHA-256、文件名、页数、识别语言与待读状态；不生成摘要、作者、年份或未经核对的题目。`Papers/` 和 `Notes/` 继续承载经人确认的研究知识。 |
| 视图 | 首次创建根目录的 `ResearchCopilot 论文库.base`，只过滤 `Sources/`，以表格显示文件、文件名、阅读状态、页数、语言；不修改用户已有的 `.base`。 |
| 引用 | 来源条目只有论文身份和 PDF 指纹，不把 AI 回答或译文当作事实；后续正式笔记仍保存 PDF 原文页码。 |
| 隐私 | 全程本地，不调用 DeepSeek，不上传 PDF。Vault 中不存 Mac 绝对路径、API 密钥、向量索引或整篇抽取文本。PDF 原件继续留在 ResearchCopilot 本地库，Vault 目录不等于 PDF 备份。 |
| 失败 | 断开 Vault、PDF 身份/版本不稳定、重复 UID、无效 YAML、目标符号链接、预览后文件变化均停止；既有源条目绝不覆盖。分批创建中途失败可再次运行，已有文件保持原样。 |

选用单独 `Sources/` 而不是提前写 `Papers/`：后者现有语义是**至少一条已确认笔记的正式论文卡**，直接写入空卡会与后续人工确认流程冲突。来源目录与正式论文卡可能指向同一论文，但权威内容不同：前者只描述本机 PDF，后者只组织用户确认过的理解，不互相复制 AI 内容。

## 架构影响与兼容性

复用 `PaperLibrary`、`PaperSummary`、`paper_uid + pdf_sha256`、`ObsidianVaultStore` 的安全首次写入与 Vault 扫描，不新建 SQL 数据库或第二个身份系统。新增 `paper_source` 作为 Vault 文件种类；`VaultStatus` 可回读来源条目。一个轻量预览／确认 API 与现有 Vault 面板复用，不在 PDF 导入时暗中写用户 Vault。

| 情况 | 预期 |
| --- | --- |
| 当前／跨论文 | 一篇 PDF 一个来源条目；批量入库不产生跨论文总结。 |
| 原文／译文 | 来源指向原始 PDF 指纹；不把译文写作论文元数据。 |
| 不同会话 | 稳定 `paper_uid` 去重，不按聊天会话或文件显示名另建一份。 |
| 本地／云端 | 目录入库纯本地；DeepSeek 无调用。 |
| macOS／Windows | Vault 文件不含绝对 PDF 路径；Windows 仅同步 Vault 时仍能看来源信息，找不到 PDF 时不能假装能打开原文。 |

## 验收标准

1. 空的已连接 Vault：预览列出当前有效 PDF 和将创建的 `.base`；预览本身不写文件。确认后 Obsidian Bases 可见相应行。
2. 再次同步不改动既有 Markdown、Obsidian 人工编辑或 `.base`，也不重复创建；添加新 PDF 后只新增对应来源条目。
3. 仍无已确认笔记时，`Papers/` 不会出现假的正式论文卡，原有“至少一条确认笔记”的约束保持。
4. Vault 外部变化、坏 YAML、重复 UID、目标符号链接、PDF 版本变化时失败关闭，不覆盖任何用户文件。
5. 不调用 API，不复制 PDF 到 Vault，不写阅读历史；测试使用临时 Vault，不触碰用户真实 Vault。

## 暂不实现

自动从 PDF 猜测作者、年份、论文题目或结论；整篇 PDF 自动复制；自动为用户改阅读状态；无预览的导入时同步；跨设备自动同步或 Obsidian 社区插件。
