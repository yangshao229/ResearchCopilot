import { useEffect, useState } from "react";

import {
  connectVault,
  disconnectVault,
  getVaultStatus,
  previewVaultCatalog,
  saveVaultCatalog,
  type VaultCatalogPreview,
  type VaultStatus,
} from "../api";
import { useI18n } from "../i18n-context";

export default function VaultPanel() {
  const { t, errorMessage } = useI18n();
  const [status, setStatus] = useState<VaultStatus | null>(null);
  const [path, setPath] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [catalogPreview, setCatalogPreview] = useState<VaultCatalogPreview | null>(null);

  useEffect(() => {
    const refresh = () => {
      void getVaultStatus().then(setStatus).catch((reason: unknown) => {
        setError(errorMessage(reason, "vault.loadError"));
      });
    };
    refresh();
    window.addEventListener("research-copilot:vault-changed", refresh);
    return () => window.removeEventListener("research-copilot:vault-changed", refresh);
  }, []);

  const handleConnect = async () => {
    if (!path.trim() || busy) return;
    setBusy(true);
    setError(null);
    try {
      setStatus(await connectVault(path.trim()));
      setCatalogPreview(null);
      setPath("");
    } catch (reason: unknown) {
      setError(errorMessage(reason, "vault.connectError"));
    } finally {
      setBusy(false);
    }
  };

  const handleDisconnect = async () => {
    setBusy(true);
    setError(null);
    try {
      setStatus(await disconnectVault());
      setCatalogPreview(null);
    } catch (reason: unknown) {
      setError(errorMessage(reason, "vault.disconnectError"));
    } finally {
      setBusy(false);
    }
  };

  const handleCatalogPreview = async () => {
    setBusy(true);
    setError(null);
    try {
      setCatalogPreview(await previewVaultCatalog());
    } catch (reason: unknown) {
      setError(errorMessage(reason, "vault.catalogPreviewError"));
    } finally {
      setBusy(false);
    }
  };

  const handleCatalogSave = async () => {
    if (!catalogPreview) return;
    setBusy(true);
    setError(null);
    try {
      setStatus(await saveVaultCatalog(catalogPreview.sha256));
      setCatalogPreview(null);
      window.dispatchEvent(new Event("research-copilot:vault-changed"));
    } catch (reason: unknown) {
      setCatalogPreview(null);
      setError(errorMessage(reason, "vault.catalogSaveError"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <details className="vault-panel">
      <summary>{t("vault.title")}</summary>
      <p className="muted">{t("vault.readOnly")}</p>
      {status?.connected ? (
        <>
          <p className="vault-path">{status.path}</p>
          <p>{t("vault.connected", {
            count: status.notes.filter((note) => note.kind !== "paper_source").length,
          })}</p>
          <p>{t("vault.sourceCount", {
            count: status.notes.filter((note) => note.kind === "paper_source").length,
          })}</p>
          <button type="button" disabled={busy} onClick={() => void handleCatalogPreview()}>
            {t("vault.previewCatalog")}
          </button>
          {catalogPreview && (
            <div className="vault-catalog-preview">
              <p>{t("vault.catalogSummary", {
                count: catalogPreview.new_sources.length,
                existing: catalogPreview.existing_count,
              })}</p>
              {catalogPreview.base_will_create && <p>{t("vault.catalogBase")}</p>}
              <ul>{catalogPreview.new_sources.map((source) => <li key={source}>{source}</li>)}</ul>
              {(catalogPreview.new_sources.length > 0 || catalogPreview.base_will_create) && (
                <button type="button" disabled={busy} onClick={() => void handleCatalogSave()}>
                  {t("vault.saveCatalog")}
                </button>
              )}
            </div>
          )}
          <button type="button" disabled={busy} onClick={() => void handleDisconnect()}>
            {t("vault.disconnect")}
          </button>
          <ul className="vault-notes">
            {status.notes.map((note) => (
              <li key={note.uid}>{note.title} <small>({note.path})</small></li>
            ))}
          </ul>
        </>
      ) : (
        <>
          <p className="muted">{t("vault.notConnected")}</p>
          <a href="https://obsidian.md/download" target="_blank" rel="noreferrer">
            {t("vault.download")}
          </a>
          <input
            aria-label={t("vault.pathLabel")}
            value={path}
            placeholder={t("vault.pathPlaceholder")}
            onChange={(event) => setPath(event.target.value)}
            onKeyDown={(event) => { if (event.key === "Enter") void handleConnect(); }}
          />
          <button type="button" disabled={busy || !path.trim()} onClick={() => void handleConnect()}>
            {busy ? t("vault.connecting") : t("vault.connect")}
          </button>
        </>
      )}
      {status && status.legacy_card_count > 0 && (
        <p className="muted">{t("vault.legacyCards", { count: status.legacy_card_count })}</p>
      )}
      {status && status.issues.length > 0 && (
        <div className="vault-issues">
          <strong>{t("vault.issues", { count: status.issues.length })}</strong>
          <ul>{status.issues.map((issue, index) => (
            <li key={`${issue.path}-${index}`}>{issue.path}: {issue.message}</li>
          ))}</ul>
        </div>
      )}
      {error && <p className="error">{error}</p>}
      <details className="vault-backup-guidance">
        <summary>{t("vault.backupTitle")}</summary>
        <p>{t("vault.backupSyncWarning")}</p>
        <ul>
          <li>{t("vault.backupVault")}</li>
          <li>{t("vault.backupDrafts")}</li>
          <li>{t("vault.backupPdfs")}</li>
        </ul>
        <p className="vault-backup-links">
          <a href="https://obsidian.md/help/backup" target="_blank" rel="noreferrer">
            {t("vault.backupObsidian")}
          </a>
          <a href="https://support.apple.com/en-us/104984" target="_blank" rel="noreferrer">
            {t("vault.backupMac")}
          </a>
          <a
            href="https://support.microsoft.com/en-us/windows/experience/backup-recovery/backup-and-restore-with-file-history"
            target="_blank"
            rel="noreferrer"
          >
            {t("vault.backupWindows")}
          </a>
        </p>
      </details>
    </details>
  );
}
