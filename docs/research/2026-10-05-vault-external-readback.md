# Obsidian 外部编辑回读：开源产品拆解

检索日期：2026-10-05。功能边界：ResearchCopilot 只读显示 Vault 当前字节内容；不在网页内改写 Obsidian 文件。

## 用户问题

用户希望在 Obsidian 中长期整理自己的研究笔记，但如果 ResearchCopilot 保存后只保留旧预览，项目页面就会误把旧草稿当成最新理解。需要按稳定 UID 回读当前 Vault 文件，并清楚区分“我的笔记”和“论文原文”。

## 参考项目与一手资料

| 项目 | 成熟做法与风险 | 本项目决定 |
| --- | --- | --- |
| [Open Notebook：Working with Notes](https://github.com/lfnovo/open-notebook/blob/main/docs/3-USER-GUIDE/working-with-notes.md) | source 不变，note 可编辑并补充个人分析；笔记不是原始材料。 | 将 Vault Markdown 视为用户可修改的知识正文，PDF 仍为论文事实来源。MIT；只借鉴流程。 |
| [Zotero：PDF Reader and Note Editor](https://www.zotero.org/support/pdf_reader)及[外部批注说明](https://www.zotero.org/support/kb/annotations_in_database) | 笔记引用可回 PDF；外部批注默认只读，贸然双向写入可能造成冲突与重复。 | 回读阶段只显示，不自动反写阅读历史或 PDF，也不自动合并。AGPL；不复制实现。 |
| [Logseq 官方仓库](https://github.com/logseq/logseq)与[文件／DB 图模式说明](https://github.com/logseq/logseq/blob/master/libs/guides/db_properties_guide.md) | 本地知识库可有文件／数据库两种模式，底层权威必须清楚。 | 本项目坚持普通 Markdown 文件为唯一正式知识来源，不同时维护一份可写的 UI 副本。AGPL；不复制实现。 |
| [Obsidian 数据存储](https://obsidian.md/help/data-storage)及[Sync 冲突](https://obsidian.md/help/sync/troubleshoot) | Vault 是本地 Markdown 文件夹；外部编辑可被 Obsidian 看见；多设备合并仍可能出现重复或格式问题。 | 每次打开／刷新都读当前文件，显示文件哈希和路径；不缓存为权威，也不借助 Obsidian 私有数据库。Obsidian 是目标应用，非开源参考项目。 |

## 流程、数据结构、隐私与失败

当前论文 → 打开“总结” → 读取 Vault 扫描结果中同一 `paper_uid` 的卡片与笔记 → 按 UID 点开只读 Markdown → 在 Obsidian 外部编辑 → 返回页面点“重新读取”看到新内容。HTTP 请求只接受 UID，服务端从已连接 Vault 的校验结果中查找真实文件，不接受浏览器传任意绝对路径。返回 `VaultNote` 元数据、Markdown 原文及 SHA-256 内容指纹；不执行 Markdown 中的脚本，不调用模型。

文件被删除／改名、变为符号链接、YAML 损坏、UID 重复、内容超限、跨论文访问时明确失败或不再列出，绝不显示旧缓存冒充最新版本。读回内容是“我的笔记”，不能自动作为论文原文证据。云端问答不会因为回读而收到笔记全文。

## 架构影响与兼容性矩阵

复用 `VaultNote`、`ObsidianVaultStore` 的扫描和 `paper_uid`，只增加一个只读 DTO 与 GET 路由；不新增核心业务对象、索引数据库或第二套笔记存储。

| 情况 | 行为 |
| --- | --- |
| 单篇／跨论文 | 只显示当前论文 UID 的正式笔记；跨论文知识仍走独立流程。 |
| 原文／译文 | 回读是用户知识，不冒充 PDF 原文或译文。 |
| 多会话 | 正式笔记属于论文，记录内原会话 UID 保留。 |
| 本地／云端 | 纯本地读；不发送 DeepSeek。 |
| macOS／Windows | UID 与相对路径，不保存设备绝对路径在 Markdown；无本地 PDF 的跨设备浏览留待后续。 |

## 验收标准

1. 创建后可用 UID 读取原文 Markdown；Obsidian 修改文件后再读，返回最新内容与不同 SHA-256。
2. 访问另一篇论文的 UID、已删除或无效文件、符号链接、重复 UID 时不泄露正文。
3. 前端只用文本方式显示，不执行 Markdown HTML；刷新时清除旧内容，不把当前视图当写入草稿。
4. 全程不改 Vault 字节、不调用模型。

## 暂不实现

网页内编辑正式笔记、自动冲突合并、同步服务、缺 PDF 设备离线浏览。任何更新功能都必须另有文件版本校验和预览差异。
