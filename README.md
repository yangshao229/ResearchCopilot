# ResearchCopilot

ResearchCopilot 是一个本地优先、面向 AI 科研论文的深度阅读工作台。完整目标、阅读流程和开发阶段见 [产品蓝图](docs/PRODUCT_BLUEPRINT.md)。

第一次使用请按[完整使用说明书](docs/USER_GUIDE.md)操作；想在自己的电脑上从源码安装、参与公开自测，请看[开源自测指南](docs/SELF_HOSTED_BETA.md)。[LoRA 真实论文流程验收](docs/REAL_PAPER_ACCEPTANCE_2026-10-06.md)记录了已验证的步骤与仍需人工确认的边界。

当前是**单人本地软件**，不是带账号的云服务。它没有用户认证，默认只监听 `127.0.0.1`；不要直接暴露公网。源码采用 [Apache-2.0](LICENSE) 许可。公开测试时请用[反馈模板](.github/ISSUE_TEMPLATE/)并先阅读[安全边界](SECURITY.md)；PDF、Obsidian Vault、模型缓存和 API Key 不随源码发布。

## 运行本地阅读器

第一次在一台电脑上准备项目：

```bash
uv sync --locked
npm --prefix web ci
npm --prefix web run build
```

如果需要生成带引用的 AI 回答，把 `.env.example` 复制为 `.env`，只在本机填写：

```text
DEEPSEEK_API_KEY=你的实际Key
DEEPSEEK_MODEL=deepseek-flash
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

`.env` 已被 Git 忽略，不要提交、截图或发送其中的 Key。系统先在本地检索，只把问题和少量命中证据发送给 DeepSeek，不上传整篇论文。

以后在 macOS 上打开项目文件夹，直接双击 `Start ResearchCopilot.command`。它优先使用本项目的 `.venv`，不用每次让 Codex 授权，也不用每次重装依赖。它会等本地服务就绪后用系统默认浏览器打开阅读工作台。请保持弹出的终端窗口运行；关闭窗口就会停止本地服务。若首次双击被 macOS 阻止，可在访达中右键该文件选择“打开”，按系统提示确认一次。启动失败时窗口会保留错误说明。

也可以从项目根目录执行：

```bash
uv run research-copilot serve
```

命令默认自动打开浏览器。终端会打印实际地址；如果 8000 端口已有旧服务，它会自动选择 8001–8019 中的空闲端口。请打开终端打印的地址，不要沿用旧的 `127.0.0.1:8000` 标签页。例如端口空闲时是：

```text
http://127.0.0.1:8000
```

如果浏览器显示“无法连接”，先看启动窗口是否仍在运行，并使用其中打印的**完整地址**；`127.0.0.1` 是你本机，不是公网。使用代理/VPN 时，若它拦截本机地址，请在代理设置中让 `127.0.0.1` 绕过代理。Codex 开发沙盒测试服务时可能单独申请网络权限；你在自己的 Mac 上双击启动不需要为此反复授权。

页面会检查本地 API 契约。若浏览器标签仍连接旧版服务，会显示版本提醒；关闭旧启动窗口并重新双击当前项目的 `Start ResearchCopilot.command`，再使用新窗口打印的地址。服务暂不可用时，页面不会把错误冒充成空资料库，可直接点击“重新检查”。真正空库时，中央区域可直接导入第一篇 PDF。

阅读器已为窄窗口与 Safari/WebKit 做基础兼容：顶部操作会换行，工作区使用动态视口高度，PDF 和助手各自滚动；旧浏览器缺少 `ResizeObserver` 时也会退化为窗口尺寸监听。PDF 本身仍是二维页面，在很窄的窗口中可在阅读区内缩放或滚动，不会强制重排论文内容。

## Obsidian 知识库（已确认笔记的预览入库）

ResearchCopilot 已提供“Obsidian 知识库”入口，但不会自动安装 Obsidian、创建 Vault 或改写旧笔记。先从 [Obsidian 官网](https://obsidian.md/download)安装，并在 Obsidian 中创建或打开一个由你自己选定的 Vault；不要把 Vault 建在本项目文件夹里面。Obsidian 的 Vault 本质是本机 Markdown 文件夹，故不安装应用也不影响 ResearchCopilot 阅读 PDF。

有了 Vault 后，展开阅读器左侧的“Obsidian 知识库”，填入 Vault 文件夹的完整路径并点击“连接并检查”。路径只保存在本机被 Git 忽略的 `artifacts/obsidian_vault.json`。页面检查 `Sources/`、`Papers/` 和 `Notes/` 中符合项目 schema 的 Markdown，列出已识别笔记与格式问题。已导入论文可经预览和确认写入 `Sources/` 及论文库 Base；这只是来源目录，不是正式知识。旧 `artifacts/paper_cards/` 只计为待审核迁移候选，不会自动进入 Vault。单条已确认阅读记录可在“笔记”页预览并再次点击确认，首次保存为 `Notes/` 中的正式笔记；随后可在“总结”页预览并确认创建 `Papers/` 中的正式论文卡。卡片只链接已入库笔记，不复制 AI 回答；已有文件绝不覆盖。在 Obsidian 外部编辑后，回到“总结”页重新读取即可看到 Vault 当前 Markdown 与内容指纹；回读是只读的，不会改写阅读记录或把个人笔记发送给模型。跨设备同步仍在后续阶段。

本地优先不等于已经备份。同步服务会传播删除和错误修改，不能替代独立备份。正式入库前请阅读[数据备份与恢复说明](docs/VAULT_BACKUP_RECOVERY.md)，至少保护整个 Vault、尚未入库的阅读记录、论文身份映射，以及没有其他可靠副本的原始 PDF。

在网页左侧点击“导入 PDF”即可把论文加入本地资料库，不需要手动复制文件。本地论文实际保存在 `data/raw/`；同一份 PDF 不会重复导入。这个目录、前端构建结果、模型和索引都不会提交到 Git。

阅读区默认使用连续阅读和适合宽度模式，也可以切换单页、手动缩放，或收起资料库与 AI 助手给论文留出更多空间。选中 PDF 原文后，可直接选择“翻译”“解释”“公式”或“提问”。

阅读器右侧提供三种本地证据检索：

- 混合检索同时使用关键词与语义候选，再进行可解释的融合与重排序；它是默认推荐方式。
- 关键词检索适合英文术语、缩写和公式名称。
- 语义检索适合用中文问题查找英文原文。它只使用本机已经缓存的 Embedding 模型，不会因普通提问自动联网下载；模型缺失时页面会提示改用关键词检索。论文原文不会因此上传到云端。

混合检索结果会显示关键词名次、语义名次以及是否被识别为参考文献类片段。点击任一证据卡片，可以让 PDF 阅读区跳转到对应的原文页码。

点击“生成带引用回答”后，系统会显示直接回答、解释、可点击的 PDF 页码引用和不确定性。服务器会校验模型返回的证据编号；无法对应到真实检索证据的引用不会展示。

每次成功回答都会保存在当前论文的“笔记”标签页。记录默认是 AI 草稿；你需要核对引用、填写自己的理解并选择分类，才能点击“核对完成，确认这条记录”。确认后仍不会自动写入 Vault：需要单独预览 Markdown 并点击“保存到 Obsidian”。只有确认后的记录才能导出 Markdown。阅读历史与旧导出文件保存在本机 `artifacts/reading_history/`，该目录不会提交到 Git，使用基础阅读功能不需要安装 Obsidian。

确认记录时还可以选择类别，供阅读历史筛选。正式论文卡是已保存笔记的索引：先将至少一条已确认且带原文页码的个人理解保存到 Obsidian，再打开“总结”页预览并确认建立卡片。旧 `artifacts/paper_cards/` 的结构化导出仍保留 API 兼容，但它只是候选快照，不与 Vault 正式卡并列为知识权威。

运行固定问题集的离线检索评测：

```bash
uv run python scripts/evaluate_retrieval.py data/processed/你的论文数据.json
```

## 开发模式

开发前端时分别启动后端和 Vite：

```bash
uv run research-copilot serve
npm --prefix web run dev
```

开发页面位于 `http://127.0.0.1:5173`，Vite 会把 `/api` 请求转发给本地 Python 后端。
