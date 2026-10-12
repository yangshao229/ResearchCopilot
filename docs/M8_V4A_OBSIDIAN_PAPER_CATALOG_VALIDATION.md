# M8.V4a：Obsidian 论文来源目录验收

日期：2026-10-09。设计依据：[本轮开源产品拆解](research/2026-10-09-obsidian-paper-catalog.md)。目标是解决“已连接 Obsidian，但空 Vault 中看不到已导入论文”，不是自动生成研究结论。

## 实际结果

- ResearchCopilot 当前已导入的 BERT、LoRA、RAG 和练习 PDF 共 4 篇，在用户已连接的 `ResearchCopilot-Vault/Sources/` 各有一条来源记录；Obsidian 内置 Bases 表格 `ResearchCopilot 论文库.base` 显示 4 行。文件名暂作为未核实标题，用户可在 Obsidian 修改显示标题及阅读状态。
- `Sources/` 只保存稳定论文 UID、PDF SHA-256、原始文件名、页数、语言标记、初始“待读”状态。PDF 原件仍在 ResearchCopilot 本机 `data/raw/`；未复制 PDF、摘要、译文、问答或向量索引到 Vault。
- `Papers/` 正式卡片与 `Notes/` 阅读笔记仍由用户核对内容后显式保存；当前目录条目不意味着已经有 4 篇人工确认笔记。
- 用户原有的 `未命名.base` 保持原样。同步只在缺失时创建新来源和本项目专用 Base，不覆盖用户编辑后的来源文件或 Base。

## 故障发现与恢复

第一次真实写入时，直接构造网页应用与命令行启动曾使用不同的论文身份索引目录，造成 4 个来源记录使用了错误 UID。发现后先逐字节核验这些文件均由本轮程序生成、未被用户编辑，再把它们移入 Vault 的 `.researchcopilot-recovery/2026-10-09-identity-correction/`，随后以实际启动器使用的身份索引重建 4 条来源。旧文件保留可恢复，没有删除；用户的其他文件未移动。已加回归测试固定默认身份目录与启动器显式论文目录的一致性。当前服务的目录预览显示 4 条已存在、0 条待创建。

## 自动验证

- Python 全量：`225 passed`；含空 Vault 预览、首次创建、重复同步不覆盖、PDF/Vault 改变后拒绝、符号链接拒绝和 API 行为。
- 前端 TypeScript 与生产构建通过。构建器只提示现有大包体积警告，没有构建失败。
- Obsidian 原生界面曾打开 Base 并显示“4 个结果”；身份纠正后只读复核 `Sources/` 正好 4 个当前 UID 文件。最终界面二次查看时 Mac 处于锁屏，尚未再次视觉确认纠正后的行；用户解锁后可直接在 Obsidian 左侧打开 Base 验证。
- 本轮没有调用 DeepSeek 或下载模型。

## 使用与边界

在 ResearchCopilot 左侧“Obsidian 知识库”可预览并确认来源目录。新导入 PDF 后再次操作即可补入，不自动覆盖既有条目。Obsidian 中可筛选、编辑元数据；若需要在另一台电脑直接阅读 PDF，还必须另外规划 PDF 的同步或重新导入。Vault 不是 PDF 备份。
