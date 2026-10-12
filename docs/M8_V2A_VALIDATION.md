# M8.V2a：已确认阅读记录安全保存到 Obsidian

日期：2026-10-05。设计依据：[本轮开源产品拆解](research/2026-10-05-reviewed-note-to-vault.md)与[长期知识库蓝图](OBSIDIAN_KNOWLEDGE_VAULT_BLUEPRINT.md)。

## 本轮交付

- 用户已在 Obsidian 打开独立 Vault；ResearchCopilot 本机连接状态为 `connected=true`，当前 0 条正式笔记，未把私人路径写入 Git 跟踪文件。
- “笔记”中的单条已人工确认记录可以预览即将保存的 Markdown、目标相对路径及 PDF 原文页码，再由用户第二次点击确认，首次创建 `Notes/record-<id>.md`。
- 服务端从现有 `ReadingRecord`、稳定论文 UID 和 PDF 指纹重新生成内容，不接受浏览器提交的任意 Markdown 或文件名。正式笔记只含用户个人理解及引用，不复制 AI 回答。
- 保存要求已连接 Vault、当前 PDF 指纹未变化、记录已确认且有个人理解、非空来源问题和至少一条有效页码引用。预览摘要同时绑定目标 Vault 与 Markdown 内容；预览后切换 Vault、摘要过期、Vault 内已有无效 YAML/未知 UID、目标文件已存在或 Notes 被替换成符号链接时停止。首次写入采用同目录临时文件加排他硬链接，已有文件绝不被覆盖。
- 用户在页面保存成功后，左侧知识库数量即时刷新。尚未实现外部编辑回读或已有笔记更新。

## 验证

- 全部后端测试：`170 passed`；仅有既有的两个测试依赖弃用警告。
- 前端 TypeScript 与生产构建通过；仍有既有的大分块提示。
- 浏览器检查：新页面可打开，Obsidian 面板显示已连接且识别 0 条正式笔记；“笔记”页正常显示当前论文的阅读记录状态。
- 临时测试 Vault 验证：预览不产生文件、确认后只创建一条、重新扫描识别 UID 与论文身份、第二次保存拒绝覆盖；预览后切换 Vault、Vault 中已有无效文件、空来源问题、未确认记录、PDF 版本变化、无引文、跨论文记录与 Notes 符号链接均拒绝。
- **未向用户真实 Vault 写入笔记**：最终保存按钮需由用户阅读预览并亲自确认。没有调用 DeepSeek，也没有同步 Windows。

## 文件与后续

新增：`docs/research/2026-10-05-reviewed-note-to-vault.md`、本验收记录。扩展：`src/research_copilot/obsidian_vault.py`、`src/research_copilot/web_app.py`、`tests/test_obsidian_vault.py`、`web/src/api.ts`、`web/src/components/assistant/AssistantViews.tsx`、`web/src/components/VaultPanel.tsx`、两份语言文件与样式。

下一步 M8.V2b：从已确认记录预览并安全创建一篇论文的正式 `Papers/<paper_uid>.md`，与本轮的 `Notes/` 笔记建立链接；不能把旧 `artifacts/` 卡片直接冒充正式笔记。M8.V3 再做 Obsidian 外部编辑回读与版本冲突处理。

## 2026-10-06 来源版本锚点补充

- 新产生的搜索证据、回答引用和阅读记录会同时携带 `paper_uid + pdf_sha256 + PDF 文件页码`，不再只靠路径 ID 与页码推断来源版本。
- PDF 抽取缓存保存源文件 SHA-256；旧缓存缺少指纹或指纹不符时必须先重新抽取，不能把旧文本误标为当前 PDF 的证据。
- 正式笔记预览会拒绝属于另一版 PDF 的显式来源锚点；旧历史记录仍可读取，但不会凭空补造无法验证的来源版本。
- 回归覆盖当前版本来源、旧缓存重建、跨版本引用拒绝与旧 JSON 可读性。完整测试 `187 passed`，前端 TypeScript 与生产构建通过；没有写用户真实 Vault 或调用 DeepSeek。
