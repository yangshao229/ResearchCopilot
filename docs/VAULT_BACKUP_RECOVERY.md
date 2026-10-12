# ResearchCopilot 数据备份与恢复

ResearchCopilot 是本地优先工具。Obsidian 同步、iCloud、OneDrive 或 Git 可以帮助多设备保持文件一致，但同步本身不能替代独立备份：误删和错误修改也可能被同步到所有设备。

## 最小备份清单

按重要性保护以下内容：

1. **整个 Obsidian Vault**：这是人工确认知识的权威，包括 `Papers/`、`Notes/` 以及希望保留的 `.obsidian/` 设置。
2. **`artifacts/reading_history/`**：尚未正式入库的阅读记录和个人理解。
3. **`artifacts/paper_identities/`**：稳定论文 UID 与 PDF 指纹映射。
4. **`data/raw/`**：本地导入的原始 PDF；如果原文件已在其他可靠位置保存，可按自己的资料管理策略取舍。

`.venv/`、`web/dist/`、抽取结果、向量索引、模型缓存和页译文缓存都可以重建，不是最小知识备份集。`.env` 可能含 API 密钥，不要把它放进普通共享或公开备份；新设备应单独配置密钥。

## macOS

使用 Apple 的 [Time Machine](https://support.apple.com/en-us/104984) 或其他能保存历史版本的独立备份工具。确认 Vault、项目中的上述草稿目录和需要保留的 PDF 实际包含在备份范围内。备份目的地应与电脑内置磁盘分离。

## Windows

使用 Microsoft 的 [File History](https://support.microsoft.com/en-us/windows/experience/backup-recovery/backup-and-restore-with-file-history) 或其他能保存历史版本的独立备份工具。确认 Vault 和 ResearchCopilot 数据所在文件夹实际被纳入库或备份范围。

## 恢复演练

定期选择一条无敏感信息的测试笔记，恢复到新的临时文件夹，确认：

- Markdown 能正常打开；
- `paper_uid` 与 `pdf_sha256` 字段仍存在；
- 原始 PDF 可找到，页码引用可核对；
- 恢复副本没有直接覆盖当前 Vault。

需要正式恢复时，先停止编辑并恢复到新位置；核对文件后，再在 ResearchCopilot 中显式连接恢复后的 Vault。不要把两个不一致的 Vault 互相覆盖，也不要删除旧副本，直到检查完成。

更多原则见 Obsidian 官方的[备份说明](https://obsidian.md/help/backup)和[数据存储说明](https://obsidian.md/help/data-storage)。
