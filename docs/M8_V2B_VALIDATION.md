# M8.V2b：Obsidian 正式论文索引卡

日期：2026-10-05。依据：[开源产品拆解](research/2026-10-05-vault-paper-index.md)与[成品化路线](PRODUCT_COMPLETION_PLAN.md)。

## 交付

- “总结”页的主流程改为预览、确认创建 Obsidian 中的正式论文卡 `Papers/<paper_uid>.md`；旧导出 API 保留兼容，但不再充当主流程。
- 卡片只链接当前 Vault 内、相同 `paper_uid` 的已确认阅读笔记；原文短引和 PDF 页码仍保存在各条笔记中。不复制 AI 回答，不产生第二份知识正文。
- 预览只读；确认时重新检查 Vault、PDF 版本与笔记内容摘要。笔记被外部编辑、Vault 切换、目标文件已存在、无笔记或验证出错时失败关闭。首次创建采用已有排他创建路径。
- 正式卡与笔记共用 `VaultNote`/`VaultNotePreview`、扫描与安全写入逻辑；没有新增数据库、模型调用或独立卡片存储模型。

## 验证

- `tests/test_obsidian_vault.py`：无已保存笔记拒绝、单篇链接正确、无 AI 正文、首次保存后可扫描、重复保存不覆盖、预览后笔记修改失效、切换 Vault 失效、PDF 版本变化与跨篇隔离、HTTP 端到端。
- 全部测试 `174 passed`，前端 TypeScript 与生产构建通过；仍有原有的两个依赖弃用警告与大分块提示。
- 只向临时测试 Vault 写入。真实用户 Vault 仍需用户在页面核对并亲自确认，不自动入库。

## 文件与后续

新增：`docs/research/2026-10-05-vault-paper-index.md`、`docs/PRODUCT_COMPLETION_PLAN.md`、本验收记录。修改：`src/research_copilot/obsidian_vault.py`、`src/research_copilot/web_app.py`、`tests/test_obsidian_vault.py`、`web/src/api.ts`、`web/src/components/AssistantPanel.tsx`、`web/src/components/assistant/AssistantViews.tsx`、两份语言文件、`PROJECT.md`、`README.md` 与蓝图。

下一步 M8.V3：回读 Obsidian 外部编辑的卡片和笔记，清楚显示“我的笔记”与 PDF 原文的不同权威，并在任何更新前做文件版本检查；不要直接自动合并或覆盖。
