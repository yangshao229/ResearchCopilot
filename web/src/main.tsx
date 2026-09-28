import { Component, StrictMode, type ErrorInfo, type ReactNode } from "react";
import { createRoot } from "react-dom/client";
import { pdfjs } from "react-pdf";

import App from "./App";
import { I18nProvider, useI18n } from "./i18n-context";
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
        <StartupErrorView
          error={this.state.error}
          componentStack={this.state.componentStack}
        />
      );
    }

    return this.props.children;
  }
}

function StartupErrorView({
  error,
  componentStack,
}: {
  error: Error;
  componentStack: string;
}) {
  const { t } = useI18n();
  return (
    <main className="startup-error">
      <h1>{t("startup.title")}</h1>
      <p>{t("startup.body")}</p>
      <pre>
        {[error.message, error.stack, componentStack]
          .filter(Boolean)
          .join("\n\n")}
      </pre>
    </main>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <I18nProvider>
      <StartupErrorBoundary>
        <App />
      </StartupErrorBoundary>
    </I18nProvider>
  </StrictMode>,
);
