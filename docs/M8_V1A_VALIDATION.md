# M8.V1a 稳定论文身份验收

日期：2026-10-04。设计依据：[Obsidian 长期知识库开源拆解](research/2026-10-04-obsidian-knowledge-vault.md)与[详细蓝图](OBSIDIAN_KNOWLEDGE_VAULT_BLUEPRINT.md)。

## 本轮范围

- 新增本地 `PaperIdentityStore`，首次见到论文时生成不可变 `paper_uid`，并保存当前 `pdf_sha256`、旧路径哈希 ID 与相对路径别名。
- 论文改名或移动后，只要 PDF 字节未变，就由内容指纹恢复同一个 `paper_uid`，同时保留新旧别名。
- 同一路径的 PDF 字节发生变化时，保留原 `paper_uid`，但返回 `pdf_version_status: changed`；不会静默接受新指纹或让旧页码引用冒充已核对。
- 现有路径哈希 `id` 继续作为全部旧 API、阅读记录和组织元数据的兼容键。本轮不迁移旧记录、不连接或写入用户 Vault。

## 自动回归

- 改名/移动后的稳定 UID、版本变化拒绝静默更新、重复旧 ID 失败关闭均有单元测试。
- `/api/papers` 新增可选的 `paper_uid`、`pdf_sha256`、`pdf_version_status`，旧前端与旧路径 ID 流程保持兼容。
- 完整后端测试：`157 passed`，仅保留既有的两个依赖弃用警告。
- 前端生产构建通过；仅保留既有的大分块提示。

## 本地真实 PDF 只读验收

在临时身份目录中读取 `data/raw` 的两篇真实论文，两次扫描得到相同的两个 `paper_uid`，版本状态均为 `current`；扫描前后两份 PDF 的 SHA-256 均未改变。临时身份数据未写入项目或用户 Vault，未调用 DeepSeek，也未修改阅读记录、译文缓存或论文文件。

## 已知边界与下一步

- 当前只建立本机身份映射；跨设备共享将在 Vault 只读接入后以 Vault 中的 UID 为准，不能靠设备绝对路径。
- PDF 版本变化只报告冲突，不提供“确认新版本”按钮；确认前旧引用仍绑定已登记指纹。
- 下一步 M8.V1 需要用户明确选择一个 Vault 或独立测试 Vault，然后才能做只读 schema 校验、重复 UID/坏 YAML 检测与旧导出迁移预览。任何写入仍留到 M8.V2，并要求人工确认与差异预览。
