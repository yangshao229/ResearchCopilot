# ResearchCopilot

ResearchCopilot 是一个本地优先、面向 AI 科研论文的深度阅读工作台。完整目标、阅读流程和开发阶段见 [产品蓝图](docs/PRODUCT_BLUEPRINT.md)。

## 运行本地阅读器

第一次在一台电脑上准备项目：

```bash
uv sync
npm --prefix web install
npm --prefix web run build
```

如果需要生成带引用的 AI 回答，把 `.env.example` 复制为 `.env`，只在本机填写：

```text
DEEPSEEK_API_KEY=你的实际Key
DEEPSEEK_MODEL=deepseek-flash
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

`.env` 已被 Git 忽略，不要提交、截图或发送其中的 Key。系统先在本地检索，只把问题和少量命中证据发送给 DeepSeek，不上传整篇论文。

以后在 macOS 上可以直接双击项目根目录中的 `Start ResearchCopilot.command`。它会启动本地服务，并用系统默认浏览器打开阅读工作台。

也可以从项目根目录执行：

```bash
uv run research-copilot serve
```

命令默认自动打开浏览器；如果没有自动打开，再访问：

```text
http://127.0.0.1:8000
```

在网页左侧点击“导入 PDF”即可把论文加入本地资料库，不需要手动复制文件。本地论文实际保存在 `data/raw/`；同一份 PDF 不会重复导入。这个目录、前端构建结果、模型和索引都不会提交到 Git。

阅读区默认使用连续阅读和适合宽度模式，也可以切换单页、手动缩放，或收起资料库与 AI 助手给论文留出更多空间。选中 PDF 原文后，可直接选择“翻译”“解释”“公式”或“提问”。

阅读器右侧提供三种本地证据检索：

- 混合检索同时使用关键词与语义候选，再进行可解释的融合与重排序；它是默认推荐方式。
- 关键词检索适合英文术语、缩写和公式名称。
- 语义检索适合用中文问题查找英文原文。第一次使用时需要加载本地 Embedding 模型，可能会稍慢；论文原文不会因此上传到云端。

混合检索结果会显示关键词名次、语义名次以及是否被识别为参考文献类片段。点击任一证据卡片，可以让 PDF 阅读区跳转到对应的原文页码。

点击“生成带引用回答”后，系统会显示直接回答、解释、可点击的 PDF 页码引用和不确定性。服务器会校验模型返回的证据编号；无法对应到真实检索证据的引用不会展示。

每次成功回答都会保存在当前论文的“笔记”标签页。记录默认是 AI 草稿；你需要核对引用、填写自己的理解并选择论文卡片栏目，才能点击“核对完成，加入论文卡片”。只有确认后的记录才能导出 Markdown。阅读历史与导出文件保存在本机 `artifacts/reading_history/`，该目录不会提交到 Git，使用这一功能不需要安装 Obsidian。

确认记录时还可以选择它在论文卡片中的栏目。至少积累两条已确认记录后，“总结”标签页可以生成结构化 Markdown 预览。卡片只汇总用户确认过的内容，保留 PDF 页码和原文摘录；空白栏目显示 `TODO`。正式卡片保存在 `artifacts/paper_cards/`。再次导出时会先显示与已有卡片的差异，并保存为新版本，不会覆盖旧文件。

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
