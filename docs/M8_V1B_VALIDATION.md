# M8.V1b：日常启动与 Obsidian Vault 只读连接

日期：2026-10-04。依据：[Obsidian 长期知识库蓝图](OBSIDIAN_KNOWLEDGE_VAULT_BLUEPRINT.md)与[开源产品拆解](research/2026-10-04-obsidian-knowledge-vault.md)。

## 本轮交付

- macOS 双击脚本优先使用项目已有 `.venv`，不依赖访达继承的 `uv` 路径；缺环境或网页构建时给出说明，避免窗口一闪而过。日常双击不需要 Codex 授权。
- 前端新增折叠的“Obsidian 知识库”入口；用户填写 Vault 完整路径后才连接，并可断开。连接路径仅存本机 `artifacts/obsidian_vault.json`，不进 Git，不进 Vault。
- 后端只读扫描 Vault 的 `Papers/` 与 `Notes/` Markdown；严格校验 YAML schema 类型、PDF 指纹、人工确认状态、UID 重复；跳过符号链接与超过 1 MB 的笔记，不创建或改写 Vault 内容。本机连接配置使用原子替换，笔记扫描顺序保持确定。
- 旧论文卡只显示待审核迁移候选数量，不把未确认的导出当作正式知识。

## 验证

- 全部后端测试：`165 passed`，仅保留已有的两个测试依赖弃用警告。
- 前端生产构建通过；仍有既有的大分块提示。
- 在本机临时启动新版服务，自动避开占用的 8000、8001，选择 8002；浏览器真实显示两篇 PDF 与新的 Obsidian 入口。测试服务随后关闭，未影响原有服务。
- 临时测试 Vault 验证连接、持久化、断开、坏 YAML、重复 UID、非 Vault 目录拒绝；测试文件连接前后字节不变。

## 未完成与边界

用户尚未安装 Obsidian、尚未创建 Vault，也没有给出真实 Vault 路径。因此本轮**没有连接或读取真实个人知识库**。下一步由用户从官方网站安装并创建 Vault，再在页面填入路径；之后需要用真实样本核对 schema、旧卡片迁移预览和缺失 PDF 提示。正式写入、Obsidian 外部编辑回读与双设备同步仍属于后续 M8.V2–V5，不应说成已经实现。
