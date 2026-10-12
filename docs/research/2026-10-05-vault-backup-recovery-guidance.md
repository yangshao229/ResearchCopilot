# Vault 备份与恢复指引：开源产品拆解

检索日期：2026-10-05。范围仅是把本地知识和草稿的备份边界讲清楚，不自动复制、上传、删除或恢复用户文件。

## 用户问题

ResearchCopilot 已能把人工确认知识保存到 Obsidian Vault，但“本地优先”也意味着磁盘故障、误删、同步冲突会直接影响知识。用户需要在第一次正式入库前知道哪些目录是权威内容、哪些是草稿或可重建缓存，以及 macOS/Windows 应使用什么独立备份机制。

## 参考项目与一手资料

| 一手来源 | 成熟做法 | 本项目取舍 |
| --- | --- | --- |
| [Obsidian 官方：Back up your Obsidian files](https://obsidian.md/help/backup) | 明确同步不等于备份；建议用单向、独立位置的备份，并在多设备场景选一台主设备负责备份。 | 页面直接提示“同步不是备份”，不把未来的跨设备同步包装成数据保护。 |
| [Obsidian 官方：How Obsidian stores data](https://obsidian.md/help/data-storage) | Vault 是本地普通 Markdown 文件夹，外部工具可管理；`.obsidian` 保存 Vault 配置，元数据缓存可重建。 | 建议备份整个 Vault，而不是只复制 `Notes/`；不把 Obsidian 缓存或应用数据库当知识权威。 |
| [Apple 官方：Back up your Mac with Time Machine](https://support.apple.com/en-us/104984) | Time Machine 可将文件自动备份到独立外置存储，并恢复历史版本。 | macOS 给出 Time Machine 官方入口，但不由应用代替用户配置备份盘。 |
| [Microsoft 官方：Backup and restore with File History](https://support.microsoft.com/en-us/windows/experience/backup-recovery/backup-and-restore-with-file-history) | File History 将个人文件定期复制到外置盘或网络位置，并可恢复旧版本。 | Windows 给出 File History 官方入口；提醒 Vault/PDF 所在文件夹必须实际被纳入保护范围。 |

这些来源均为官方产品文档。本阶段不复制任何项目代码、不引入依赖；许可证不会传递到本项目源代码。

## 流程、数据、隐私与失败处理

首次连接 Vault → 页面显示备份提醒 → 用户阅读本项目清单 → 在操作系统中配置独立备份 → 在正式入库后定期检查能否恢复一个测试文件。ResearchCopilot 只显示说明和官方链接，不检测备份盘、不读取 Time Machine/File History 状态，也不上传文件。

备份对象分层：

1. 用户知识权威：整个 Obsidian Vault（含 `Papers/`、`Notes/` 和需要保留的 `.obsidian/` 设置）。
2. 尚未入库的人工草稿与身份映射：`artifacts/reading_history/`、`artifacts/paper_identities/`。
3. 原始资料：`data/raw/`，除非 PDF 已在其他可靠位置保存。
4. 可重建项：`.venv/`、`web/dist/`、抽取 JSON、向量索引、模型缓存和页译文缓存，不作为最小知识备份集。
5. 私密项：`.env` 含密钥，不建议混入普通云同步；重建时应在新设备单独配置。

备份不可用、备份盘断开或同步冲突时，本项目不猜测“最近版本”并自动覆盖。恢复应先到新位置，核对 Markdown 与 PDF，再重新连接 Vault。

## 架构影响

- 只增加说明文档、Vault 面板中的静态提醒和官方入口；不增加领域对象、API、后台任务或文件权限。
- 继续保持 PDF 为论文事实权威、Vault 为人工知识权威、本地 JSON 为运行中草稿。
- 不读取系统备份配置，因此不会产生新的隐私面或平台权限请求。

## 兼容性矩阵

| 情况 | 行为 |
| --- | --- |
| 当前论文／跨论文 | 整个 Vault 与身份映射一起备份，不按当前论文拆分。 |
| 原文／译文 | 原始 PDF 建议保护；机器译文缓存可重建，不冒充知识权威。 |
| 不同会话 | 未入库的阅读记录整体备份，避免只保护最终卡片。 |
| 本地／云端 | 备份位置由用户选择；同步服务不被称为备份。 |
| macOS／Windows | 分别链接 Time Machine 与 File History；Vault 内容仍用普通 Markdown。 |

## 实现顺序

1. 写独立备份与恢复清单。
2. 在 Vault 面板提供简短提醒、清单入口和 macOS/Windows 官方链接。
3. 用前端生产构建验证双语文案与静态链接，不申请系统权限。

## 验收标准

1. 已连接或未连接 Vault 时都能看到“同步不是备份”和最小备份对象。
2. macOS 与 Windows 官方入口明确，且页面不会声称已经完成备份。
3. 文档明确列出权威、草稿、原始 PDF、可重建缓存和密钥边界。
4. 不新增 API、不读取备份状态、不修改 Vault、论文、阅读记录或缓存。

## 暂不实现

自动压缩、云端上传、定时复制、备份盘探测、一键恢复和跨设备同步。这些动作需要新的文件系统权限、保留策略和覆盖确认，不能由静态指引暗中扩大。
