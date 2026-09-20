# ResearchCopilot

ResearchCopilot 是一个本地优先、面向 AI 科研论文的深度阅读工作台。完整目标、阅读流程和开发阶段见 [产品蓝图](docs/PRODUCT_BLUEPRINT.md)。

## 运行本地阅读器

第一次在一台电脑上准备项目：

```bash
uv sync
npm --prefix web install
npm --prefix web run build
```

以后从项目根目录启动：

```bash
uv run research-copilot serve
```

然后在浏览器打开：

```text
http://127.0.0.1:8000
```

本地论文默认放在 `data/raw/`。这个目录、前端构建结果、模型和索引都不会提交到 Git。

## 开发模式

开发前端时分别启动后端和 Vite：

```bash
uv run research-copilot serve
npm --prefix web run dev
```

开发页面位于 `http://127.0.0.1:5173`，Vite 会把 `/api` 请求转发给本地 Python 后端。
