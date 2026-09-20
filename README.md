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

以后从项目根目录启动：

```bash
uv run research-copilot serve
```

然后在浏览器打开：

```text
http://127.0.0.1:8000
```

本地论文默认放在 `data/raw/`。这个目录、前端构建结果、模型和索引都不会提交到 Git。

阅读器右侧提供两种本地证据检索：

- 关键词检索适合英文术语、缩写和公式名称。
- 语义检索适合用中文问题查找英文原文。第一次使用时需要加载本地 Embedding 模型，可能会稍慢；论文原文不会因此上传到云端。

点击任一证据卡片，可以让 PDF 阅读区跳转到对应的原文页码。

点击“生成带引用回答”后，系统会显示直接回答、解释、可点击的 PDF 页码引用和不确定性。服务器会校验模型返回的证据编号；无法对应到真实检索证据的引用不会展示。

## 开发模式

开发前端时分别启动后端和 Vite：

```bash
uv run research-copilot serve
npm --prefix web run dev
```

开发页面位于 `http://127.0.0.1:5173`，Vite 会把 `/api` 请求转发给本地 Python 后端。
