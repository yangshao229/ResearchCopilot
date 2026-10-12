# M8 共用原文来源契约：第一步

日期：2026-10-06。属于[产品蓝图](PRODUCT_BLUEPRINT.md)中“原文锚点”的底座收敛，不增加新按钮或模型，不改变证据充分性门槛。设计沿用此前对 Zotero、Open Notebook 与 PaperQA2 的开源拆解；此步只落实本项目的来源身份。

## 共用规则

- `SourceDocumentRef` = 稳定的 `paper_uid` + **当前 PDF 内容**的 SHA-256；`SourceAnchor` 再加从 1 开始的 PDF 文件页码。文件名、阅读器显示位置和译文都不能代替它。
- 新解析文本 JSON 记录源 PDF 的 SHA-256。检索前对照实际 PDF：无指纹的旧缓存或指纹不一致的缓存会重新解析；仅修改文件时间但不改内容不会无谓重建。PDF 在解析期间变化则拒绝保存结果。
- 新的单篇检索结果、问答证据、回答引用及持久化阅读记录使用同一来源锚点；页码不一致的数据模型会拒绝。选区译文缓存只复用同一 PDF 版本的有锚点记录。
- 已有阅读记录仍可读取。新记录在写入 Obsidian 前，逐条检查来源锚点是否等于当前论文及 PDF 版本；不匹配时拒绝入库，不自动改写原笔记。旧记录原本没有逐条锚点，继续依赖已有论文身份与 PDF 版本检查，后续迁移需单独设计。

## 涉及文件

- 领域契约：`src/research_copilot/domain.py`；PDF 指纹复用：`paper_identity.py`、`paper_library.py`。
- 解析缓存与使用：`pdf_importer.py`、`paper_search_service.py`、`reading_service.py`、`web_app.py`。
- 正式笔记入库校验：`obsidian_vault.py`；网页类型契约：`web/src/api.ts`。
- 回归：`tests/test_source_provenance.py`、`test_pdf_to_json.py`、`test_web_app.py`、`test_obsidian_vault.py`，以及因测试夹具新增 PDF 指纹而更新的资料库检索测试。

## 验证与边界

- 全部 Python 测试：`190 passed`，仅有两条测试依赖弃用警告；前端 TypeScript 与生产构建通过，仍有原有的大分块提示。
- 回归覆盖同一时间戳下 PDF 内容替换、无指纹旧缓存重建、来源页码不一致、旧版 PDF 引用不得写入 Vault。
- 这只保证“证据属于哪份 PDF 的哪一页”可核查，**不保证**检索找对页、该页足以回答问题，或公式／表格被正确解析。后续已完成[统一证据包](M8_EVIDENCE_SET_VALIDATION.md)与[已查看证据快照](M8_EVIDENCE_SNAPSHOT_VALIDATION.md)；重排与拒答候选仍按现有离线评测保持未上线。
- 未调用 DeepSeek、未下载模型、未改真实 PDF、阅读历史、译文缓存或用户 Vault。工作树既有未提交变更保留原状，本步未提交 Git。
