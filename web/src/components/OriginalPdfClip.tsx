import { useEffect, useRef, useState } from "react";
import { pdfjs } from "react-pdf";

import { paperFileUrl, type PdfClipRegion } from "../api";
import { useI18n } from "../i18n-context";

export default function OriginalPdfClip({
  paperId,
  region,
  kind,
}: {
  paperId: string;
  region: PdfClipRegion;
  kind: "formula" | "table";
}) {
  const { t } = useI18n();
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let active = true;
    setFailed(false);
    const task = pdfjs.getDocument({ url: paperFileUrl(paperId) });
    let renderTask: { cancel: () => void; promise: Promise<void> } | null = null;

    async function draw() {
      try {
        const document = await task.promise;
        const page = await document.getPage(region.source_page);
        if (!active || !canvasRef.current) return;
        const scale = 2;
        const canvas = canvasRef.current;
        canvas.width = Math.ceil(region.width * scale);
        canvas.height = Math.ceil(region.height * scale);
        const context = canvas.getContext("2d");
        if (!context) throw new Error("Canvas unavailable");
        renderTask = page.render({
          canvas,
          canvasContext: context,
          viewport: page.getViewport({ scale }),
          transform: [1, 0, 0, 1, -region.left * scale, -region.top * scale],
        });
        await renderTask.promise;
      } catch (error) {
        if (active && !(error instanceof Error && error.name === "RenderingCancelledException")) {
          setFailed(true);
        }
      }
    }
    void draw();
    return () => {
      active = false;
      renderTask?.cancel();
      void task.destroy();
    };
  }, [paperId, region.height, region.left, region.source_page, region.top, region.width]);

  const caption = kind === "formula" ? "translation.originalFormula" : "translation.originalTable";
  const aria = kind === "formula" ? "translation.originalFormulaAria" : "translation.originalTableAria";
  return (
    <figure className={`original-pdf-clip original-pdf-clip-${kind}`}>
      <figcaption>{t(caption, { page: region.source_page })}</figcaption>
      {kind === "table" && <small>{t("translation.tableScrollHint")}</small>}
      {failed ? (
        <p role="alert">{t("translation.originalPreviewFailed")}</p>
      ) : (
        <canvas ref={canvasRef} role="img" aria-label={t(aria)} />
      )}
    </figure>
  );
}
