import { Component, StrictMode, type ErrorInfo, type ReactNode } from "react";
import { createRoot } from "react-dom/client";
import { pdfjs } from "react-pdf";

import App from "./App";
import "./styles.css";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";

type AsyncIterableReadableStream = ReadableStream<unknown> & {
  [Symbol.asyncIterator]?: () => AsyncGenerator<unknown, void, unknown>;
};

function ensureReadableStreamAsyncIteration() {
  const streamPrototype =
    ReadableStream.prototype as AsyncIterableReadableStream;
  if (streamPrototype[Symbol.asyncIterator]) {
    return;
  }

  Object.defineProperty(streamPrototype, Symbol.asyncIterator, {
    configurable: true,
    writable: true,
    value: async function* (this: ReadableStream<unknown>) {
      const reader = this.getReader();
      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) {
            return;
          }
          yield value;
        }
      } finally {
        reader.releaseLock();
      }
    },
  });
}

ensureReadableStreamAsyncIteration();

pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  "pdfjs-dist/build/pdf.worker.min.mjs",
  import.meta.url,
).toString();

type StartupErrorBoundaryProps = {
  children: ReactNode;
};

type StartupErrorBoundaryState = {
  error: Error | null;
  componentStack: string;
};

class StartupErrorBoundary extends Component<
  StartupErrorBoundaryProps,
  StartupErrorBoundaryState
> {
  state: StartupErrorBoundaryState = { error: null, componentStack: "" };

  static getDerivedStateFromError(error: Error): StartupErrorBoundaryState {
    return { error, componentStack: "" };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("ResearchCopilot rendering failed", error, errorInfo);
    this.setState({ componentStack: errorInfo.componentStack ?? "" });
  }

  render() {
    if (this.state.error) {
      return (
        <main className="startup-error">
          <h1>ResearchCopilot 启动失败</h1>
          <p>页面已连接本地服务，但一个界面组件运行失败。</p>
          <pre>
            {[
              this.state.error.message,
              this.state.error.stack,
              this.state.componentStack,
            ]
              .filter(Boolean)
              .join("\n\n")}
          </pre>
        </main>
      );
    }

    return this.props.children;
  }
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <StartupErrorBoundary>
      <App />
    </StartupErrorBoundary>
  </StrictMode>,
);
