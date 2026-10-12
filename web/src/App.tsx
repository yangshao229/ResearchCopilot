import { useEffect, useMemo, useRef, useState } from "react";

import {
  EXPECTED_API_SCHEMA,
  createLibraryCollection,
  collectResearchEvidence,
  deleteLibraryCollection,
  getApiHealth,
  importPaper,
  listLibraryCollections,
  listPapers,
  savePaperOrganization,
  type LibraryCollection,
  type LibrarySearchResponse,
  type PageLayout,
  type PageSourceRegion,
  type Paper,
  type ResearchEvidenceResponse,
  searchLibrary,
} from "./api";
import AssistantPanel from "./components/AssistantPanel";
import PdfReader, { type FocusedSourceRegion, type PdfSelection } from "./components/PdfReader";
import VaultPanel from "./components/VaultPanel";
import { useI18n, type UiLanguage } from "./i18n-context";


const SELECTED_PAPER_KEY = "research-copilot:selected-paper";
const RESEARCH_SET_KEY = "research-copilot:research-set";

function loadResearchPaperIds(): string[] {
  try {
    const saved = JSON.parse(window.localStorage.getItem(RESEARCH_SET_KEY) ?? "[]");
    return Array.isArray(saved)
      ? saved.filter((item): item is string => typeof item === "string").slice(0, 8)
      : [];
  } catch {
    return [];
  }
}

function savedPageKey(paperId: string): string {
  return `research-copilot:page:${paperId}`;
}

function loadSavedPage(paperId: string): number {
  const value = Number.parseInt(
    window.localStorage.getItem(savedPageKey(paperId)) ?? "1",
    10,
  );
  return Number.isFinite(value) && value > 0 ? value : 1;
}

export default function App() {
  const { language, setLanguage, t, errorMessage } = useI18n();
  const [papers, setPapers] = useState<Paper[]>([]);
  const [collections, setCollections] = useState<LibraryCollection[]>([]);
  const [selectedPaperId, setSelectedPaperId] = useState<string | null>(null);
  const [selectedCollectionId, setSelectedCollectionId] = useState("");
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [collectionDraft, setCollectionDraft] = useState("");
  const [organizationCollectionIds, setOrganizationCollectionIds] = useState<string[]>([]);
  const [tagDraft, setTagDraft] = useState("");
  const [organizationMessage, setOrganizationMessage] = useState<string | null>(null);
  const [isSavingOrganization, setIsSavingOrganization] = useState(false);
  const [libraryQuery, setLibraryQuery] = useState("");
  const [librarySearch, setLibrarySearch] = useState<LibrarySearchResponse | null>(null);
  const [librarySearchError, setLibrarySearchError] = useState<string | null>(null);
  const [isSearchingLibrary, setIsSearchingLibrary] = useState(false);
  const librarySearchVersion = useRef(0);
  const [researchPaperIds, setResearchPaperIds] = useState<string[]>(loadResearchPaperIds);
  const [researchQuery, setResearchQuery] = useState("");
  const [researchEvidence, setResearchEvidence] = useState<ResearchEvidenceResponse | null>(null);
  const [researchEvidenceError, setResearchEvidenceError] = useState<string | null>(null);
  const [isCollectingEvidence, setIsCollectingEvidence] = useState(false);
  const [pagesByPaper, setPagesByPaper] = useState<Record<string, number>>({});
  const [selection, setSelection] = useState<PdfSelection | null>(null);
  const [focusedSourceRegion, setFocusedSourceRegion] = useState<FocusedSourceRegion | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [collectionError, setCollectionError] = useState<string | null>(null);
  const [compatibilityWarning, setCompatibilityWarning] = useState<string | null>(null);
  const [loadAttempt, setLoadAttempt] = useState(0);
  const [isImporting, setIsImporting] = useState(false);
  const [importMessage, setImportMessage] = useState<string | null>(null);
  const [libraryOpen, setLibraryOpen] = useState(
    () => window.innerWidth > 1050,
  );
  const [assistantOpen, setAssistantOpen] = useState(
    () => window.innerWidth > 720,
  );

  useEffect(() => {
    setIsLoading(true);
    setError(null);
    setCollectionError(null);
    setCompatibilityWarning(null);
    Promise.allSettled([getApiHealth(), listPapers(), listLibraryCollections()])
      .then(([healthResult, paperResult, collectionResult]) => {
        if (
          healthResult.status === "rejected" ||
          healthResult.value.api_schema !== EXPECTED_API_SCHEMA
        ) {
          setCompatibilityWarning(t("app.compatibilityWarning"));
        }
        if (paperResult.status === "rejected") {
          setError(errorMessage(paperResult.reason, "app.errorPaperList"));
          return;
        }
        const loadedPapers = paperResult.value;
        setPapers(loadedPapers);
        if (collectionResult.status === "fulfilled") {
          setCollections(collectionResult.value);
        } else {
          setCollectionError(t("app.errorCollectionList"));
        }
        setResearchPaperIds((current) =>
          current.filter((paperId) => loadedPapers.some((paper) => paper.id === paperId)),
        );
        const previousPaper = window.localStorage.getItem(SELECTED_PAPER_KEY);
        const selectedPaper = loadedPapers.find(
          (paper) => paper.id === previousPaper,
        );
        setSelectedPaperId(selectedPaper?.id ?? loadedPapers[0]?.id ?? null);
      })
      .finally(() => setIsLoading(false));
  }, [loadAttempt]);

  useEffect(() => {
    if (selectedPaperId) {
      window.localStorage.setItem(SELECTED_PAPER_KEY, selectedPaperId);
    }
  }, [selectedPaperId]);

  useEffect(() => {
    window.localStorage.setItem(RESEARCH_SET_KEY, JSON.stringify(researchPaperIds));
    setResearchEvidence(null);
    setResearchEvidenceError(null);
  }, [researchPaperIds]);

  const selectedPaper = useMemo(
    () => papers.find((paper) => paper.id === selectedPaperId) ?? null,
    [papers, selectedPaperId],
  );

  const allTags = useMemo(
    () =>
      Array.from(new Set(papers.flatMap((paper) => paper.tags))).sort((left, right) =>
        left.localeCompare(right),
      ),
    [papers],
  );

  const visiblePapers = useMemo(
    () =>
      papers.filter(
        (paper) =>
          (!selectedCollectionId || paper.collection_ids.includes(selectedCollectionId)) &&
          selectedTags.every((tag) =>
            paper.tags.some((paperTag) => paperTag.toLocaleLowerCase() === tag.toLocaleLowerCase()),
          ),
      ),
    [papers, selectedCollectionId, selectedTags],
  );

  useEffect(() => {
    librarySearchVersion.current += 1;
    setLibrarySearch(null);
    setLibrarySearchError(null);
    setIsSearchingLibrary(false);
  }, [visiblePapers]);

  useEffect(() => {
    setOrganizationCollectionIds(selectedPaper?.collection_ids ?? []);
    setTagDraft(selectedPaper?.tags.join(", ") ?? "");
    setOrganizationMessage(null);
  }, [selectedPaperId]);

  const pageNumber = selectedPaper
    ? (pagesByPaper[selectedPaper.id] ?? loadSavedPage(selectedPaper.id))
    : 1;

  const changePage = (nextPage: number) => {
    if (!selectedPaper) {
      return;
    }

    setFocusedSourceRegion((current) =>
      current?.paperId === selectedPaper.id && current.source_page === nextPage
        ? current
        : null,
    );

    setPagesByPaper((currentPages) => ({
      ...currentPages,
      [selectedPaper.id]: nextPage,
    }));
    window.localStorage.setItem(
      savedPageKey(selectedPaper.id),
      String(nextPage),
    );
  };

  const choosePaper = (paperId: string) => {
    setSelectedPaperId(paperId);
    setSelection(null);
    setFocusedSourceRegion(null);
  };

  const focusSourceRegion = (layout: PageLayout, region: PageSourceRegion) => {
    if (!selectedPaper) return;
    changePage(region.source_page);
    setFocusedSourceRegion({
      ...region,
      paperId: selectedPaper.id,
      pageWidth: layout.page_width,
      pageHeight: layout.page_height,
    });
  };

  const handlePdfImport = async (file: File | undefined) => {
    if (!file || isImporting) {
      return;
    }

    setIsImporting(true);
    setError(null);
    setImportMessage(null);
    try {
      const result = await importPaper(file);
      const loadedPapers = await listPapers();
      setPapers(loadedPapers);
      setSelectedPaperId(result.paper.id);
      setSelection(null);
      setFocusedSourceRegion(null);
      setLibraryOpen(true);
      setImportMessage(
        result.imported ? t("app.importSuccess") : t("app.importDuplicate"),
      );
    } catch (reason: unknown) {
      setError(errorMessage(reason, "app.errorImportPdf"));
    } finally {
      setIsImporting(false);
    }
  };

  const handleCreateCollection = async () => {
    if (!collectionDraft.trim()) return;
    setOrganizationMessage(null);
    try {
      const collection = await createLibraryCollection(collectionDraft);
      setCollections((current) =>
        [...current, collection].sort((left, right) => left.name.localeCompare(right.name)),
      );
      setCollectionDraft("");
    } catch (reason: unknown) {
      setOrganizationMessage(errorMessage(reason, "app.errorCollectionCreate"));
    }
  };

  const handleDeleteCollection = async (collection: LibraryCollection) => {
    if (!window.confirm(t("app.deleteCollectionConfirm", { name: collection.name }))) return;
    setOrganizationMessage(null);
    try {
      await deleteLibraryCollection(collection.id);
      const [loadedPapers, loadedCollections] = await Promise.all([
        listPapers(),
        listLibraryCollections(),
      ]);
      setPapers(loadedPapers);
      setCollections(loadedCollections);
      setOrganizationCollectionIds((current) =>
        current.filter((collectionId) => collectionId !== collection.id),
      );
      if (selectedCollectionId === collection.id) setSelectedCollectionId("");
    } catch (reason: unknown) {
      setOrganizationMessage(errorMessage(reason, "app.errorCollectionDelete"));
    }
  };

  const handleSaveOrganization = async () => {
    if (!selectedPaper || isSavingOrganization) return;
    setIsSavingOrganization(true);
    setOrganizationMessage(null);
    try {
      const organization = await savePaperOrganization(selectedPaper.id, {
        collection_ids: organizationCollectionIds,
        tags: tagDraft.split(/[,，\n]/).map((tag) => tag.trim()).filter(Boolean),
      });
      setPapers((current) =>
        current.map((paper) =>
          paper.id === selectedPaper.id ? { ...paper, ...organization } : paper,
        ),
      );
      setOrganizationCollectionIds(organization.collection_ids);
      setTagDraft(organization.tags.join(", "));
      setOrganizationMessage(t("app.organizationSaved"));
    } catch (reason: unknown) {
      setOrganizationMessage(errorMessage(reason, "app.errorOrganizationSave"));
    } finally {
      setIsSavingOrganization(false);
    }
  };

  const handleLibrarySearch = async () => {
    if (!libraryQuery.trim() || isSearchingLibrary) return;
    const requestVersion = ++librarySearchVersion.current;
    setIsSearchingLibrary(true);
    setLibrarySearchError(null);
    try {
      const results = await searchLibrary(
        libraryQuery,
        visiblePapers.map((paper) => paper.id),
      );
      if (requestVersion === librarySearchVersion.current) setLibrarySearch(results);
    } catch (reason: unknown) {
      if (requestVersion === librarySearchVersion.current) {
        setLibrarySearch(null);
        setLibrarySearchError(errorMessage(reason, "app.errorLibrarySearch"));
      }
    } finally {
      if (requestVersion === librarySearchVersion.current) setIsSearchingLibrary(false);
    }
  };

  const openLibrarySearchResult = (paperId: string, sourcePage: number) => {
    setSelectedPaperId(paperId);
    setSelection(null);
    setFocusedSourceRegion(null);
    setPagesByPaper((current) => ({ ...current, [paperId]: sourcePage }));
    window.localStorage.setItem(savedPageKey(paperId), String(sourcePage));
  };

  const toggleResearchPaper = (paperId: string) => {
    if (isCollectingEvidence) return;
    setResearchPaperIds((current) => {
      if (current.includes(paperId)) return current.filter((item) => item !== paperId);
      return current.length < 8 ? [...current, paperId] : current;
    });
  };

  const handleCollectResearchEvidence = async () => {
    if (
      researchPaperIds.length < 2 ||
      !researchQuery.trim() ||
      isCollectingEvidence
    ) return;
    setIsCollectingEvidence(true);
    setResearchEvidenceError(null);
    try {
      setResearchEvidence(await collectResearchEvidence(researchQuery, researchPaperIds));
    } catch (reason: unknown) {
      setResearchEvidence(null);
      setResearchEvidenceError(errorMessage(reason, "app.errorResearchEvidence"));
    } finally {
      setIsCollectingEvidence(false);
    }
  };

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">{t("app.workspaceEyebrow")}</p>
          <h1>ResearchCopilot</h1>
        </div>
        <div className="topbar-actions">
          <button type="button" onClick={() => setLibraryOpen((open) => !open)}>
            {libraryOpen ? t("app.collapseLibrary") : t("app.openLibrary")}
          </button>
          <button
            type="button"
            disabled={!selectedPaper}
            onClick={() => setAssistantOpen((open) => !open)}
          >
            {assistantOpen ? t("app.collapseAssistant") : t("app.openAssistant")}
          </button>
          <label className="ui-language-picker">
            <span>{t("app.interfaceLanguage")}</span>
            <select
              aria-label={t("app.interfaceLanguage")}
              value={language}
              onChange={(event) => setLanguage(event.target.value as UiLanguage)}
            >
              <option value="zh-CN">{t("app.languageChinese")}</option>
              <option value="en">{t("app.languageEnglish")}</option>
            </select>
          </label>
          <div className="milestone-badge">{t("app.milestone")}</div>
        </div>
      </header>

      <div
        className={`workspace${libraryOpen ? "" : " library-collapsed"}${
          assistantOpen ? "" : " assistant-collapsed"
        }`}
      >
        <aside className="library-panel">
          <div className="panel-heading">
            <p className="eyebrow">{t("app.libraryEyebrow")}</p>
            <h2>{t("app.papers")}</h2>
            <span>{t("app.paperCount", { count: papers.length })}</span>
          </div>

          <label className="import-paper-button">
            <input
              type="file"
              accept="application/pdf,.pdf"
              disabled={isImporting}
              onChange={(event) => {
                void handlePdfImport(event.target.files?.[0]);
                event.currentTarget.value = "";
              }}
            />
            {isImporting ? t("app.importing") : t("app.importPdf")}
          </label>
          {importMessage && <p className="import-message">{importMessage}</p>}
          {compatibilityWarning && (
            <div className="compatibility-warning panel-message">
              <p>{compatibilityWarning}</p>
              <button type="button" onClick={() => setLoadAttempt((value) => value + 1)}>
                {t("app.retryConnection")}
              </button>
            </div>
          )}
          {collectionError && <p className="error panel-message">{collectionError}</p>}
          <VaultPanel />

          {papers.length > 0 && (
            <section className="library-search" aria-label={t("app.librarySearchAria")}>
              <div className="library-search-row">
                <input
                  value={libraryQuery}
                  placeholder={t("app.librarySearchPlaceholder")}
                  onChange={(event) => {
                    librarySearchVersion.current += 1;
                    setLibraryQuery(event.target.value);
                    setLibrarySearch(null);
                    setLibrarySearchError(null);
                    setIsSearchingLibrary(false);
                  }}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") void handleLibrarySearch();
                  }}
                />
                <button
                  type="button"
                  disabled={isSearchingLibrary || !libraryQuery.trim()}
                  onClick={() => void handleLibrarySearch()}
                >
                  {isSearchingLibrary ? t("app.librarySearching") : t("app.librarySearch")}
                </button>
              </div>
              <small>
                {t("app.librarySearchScope", {
                  count: librarySearch?.requested_paper_count ?? visiblePapers.length,
                })}
              </small>
              {(librarySearch || librarySearchError) && (
                <button
                  type="button"
                  className="clear-library-search"
                  onClick={() => {
                    librarySearchVersion.current += 1;
                    setLibraryQuery("");
                    setLibrarySearch(null);
                    setLibrarySearchError(null);
                    setIsSearchingLibrary(false);
                  }}
                >
                  {t("app.clearLibrarySearch")}
                </button>
              )}
              {librarySearchError && <p className="error library-search-message">{librarySearchError}</p>}
              {librarySearch && (
                <div className="library-search-results">
                  <p>{t("app.librarySearchResultCount", { count: librarySearch.results.length })}</p>
                  {librarySearch.skipped_paper_count > 0 && (
                    <p className="muted">
                      {t("app.librarySearchSkipped", { count: librarySearch.skipped_paper_count })}
                    </p>
                  )}
                  {librarySearch.results.length === 0 ? (
                    <p className="muted">{t("app.librarySearchEmpty")}</p>
                  ) : (
                    librarySearch.results.map((result, index) => (
                      <button
                        type="button"
                        key={`${result.paper_id}-${result.source_page}-${index}`}
                        onClick={() => openLibrarySearchResult(result.paper_id, result.source_page)}
                      >
                        <strong>{result.paper_name}</strong>
                        <small>{t("app.librarySearchPage", { page: result.source_page })}</small>
                        <span>{result.text}</span>
                      </button>
                    ))
                  )}
                </div>
              )}
            </section>
          )}

          {papers.length > 0 && (
            <section className="library-filters" aria-label={t("app.libraryFiltersAria")}>
              <label>
                <span>{t("app.collectionFilter")}</span>
                <select
                  value={selectedCollectionId}
                  onChange={(event) => setSelectedCollectionId(event.target.value)}
                >
                  <option value="">{t("app.allCollections")}</option>
                  {collections.map((collection) => (
                    <option key={collection.id} value={collection.id}>{collection.name}</option>
                  ))}
                </select>
              </label>
              {allTags.length > 0 && (
                <div className="tag-filter">
                  <span>{t("app.tagFilter")}</span>
                  <div className="tag-chip-list">
                    {allTags.map((tag) => (
                      <button
                        type="button"
                        key={tag}
                        className={selectedTags.includes(tag) ? "active" : ""}
                        onClick={() => setSelectedTags((current) =>
                          current.includes(tag)
                            ? current.filter((item) => item !== tag)
                            : [...current, tag],
                        )}
                      >
                        {tag}
                      </button>
                    ))}
                  </div>
                </div>
              )}
              {(selectedCollectionId || selectedTags.length > 0) && (
                <button
                  type="button"
                  className="clear-library-filters"
                  onClick={() => {
                    setSelectedCollectionId("");
                    setSelectedTags([]);
                  }}
                >
                  {t("app.clearFilters")}
                </button>
              )}
              <small>{t("app.filteredPaperCount", { visible: visiblePapers.length, total: papers.length })}</small>
            </section>
          )}

          {papers.length > 0 && (
            <details className="research-set-panel">
              <summary>
                {t("app.researchSet", { count: researchPaperIds.length })}
              </summary>
              <p className="research-set-help">{t("app.researchSetHelp")}</p>
              {researchPaperIds.length > 0 && (
                <div className="research-set-selected">
                  {researchPaperIds.map((paperId) => {
                    const paper = papers.find((item) => item.id === paperId);
                    if (!paper) return null;
                    return (
                      <div key={paperId}>
                        <span>{paper.name}</span>
                        <button
                          type="button"
                          aria-label={t("app.removeResearchPaperAria", { name: paper.name })}
                          disabled={isCollectingEvidence}
                          onClick={() => toggleResearchPaper(paperId)}
                        >
                          ×
                        </button>
                      </div>
                    );
                  })}
                </div>
              )}
              <p className="organizer-label">{t("app.chooseVisiblePapers")}</p>
              <div className="research-paper-choices">
                {visiblePapers.map((paper) => {
                  const checked = researchPaperIds.includes(paper.id);
                  return (
                    <label key={paper.id}>
                      <input
                        type="checkbox"
                        checked={checked}
                        disabled={
                          isCollectingEvidence ||
                          (!checked && researchPaperIds.length >= 8)
                        }
                        onChange={() => toggleResearchPaper(paper.id)}
                      />
                      <span>{paper.name}</span>
                    </label>
                  );
                })}
              </div>
              {researchPaperIds.length > 0 && (
                <button
                  type="button"
                  className="clear-research-set"
                  disabled={isCollectingEvidence}
                  onClick={() => setResearchPaperIds([])}
                >
                  {t("app.clearResearchSet")}
                </button>
              )}
              <div className="research-query-row">
                <input
                  value={researchQuery}
                  placeholder={t("app.researchEvidencePlaceholder")}
                  disabled={isCollectingEvidence}
                  onChange={(event) => {
                    setResearchQuery(event.target.value);
                    setResearchEvidence(null);
                    setResearchEvidenceError(null);
                  }}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") void handleCollectResearchEvidence();
                  }}
                />
                <button
                  type="button"
                  disabled={
                    researchPaperIds.length < 2 ||
                    !researchQuery.trim() ||
                    isCollectingEvidence
                  }
                  onClick={() => void handleCollectResearchEvidence()}
                >
                  {isCollectingEvidence
                    ? t("app.collectingResearchEvidence")
                    : t("app.collectResearchEvidence")}
                </button>
              </div>
              {researchPaperIds.length < 2 && (
                <p className="muted research-set-message">{t("app.researchSetMinimum")}</p>
              )}
              {researchEvidenceError && (
                <p className="error research-set-message">{researchEvidenceError}</p>
              )}
              {researchEvidence && (
                <div className="research-evidence-results">
                  <p>{t("app.researchEvidenceOnly")}</p>
                  {researchEvidence.papers.map((paper) => (
                    <section key={paper.paper_id}>
                      <strong>{paper.paper_name}</strong>
                      <small>{t(`app.researchStatus.${paper.status}`)}</small>
                      {paper.hits.map((hit, index) => (
                        <button
                          type="button"
                          key={`${hit.source_page}-${index}`}
                          onClick={() => openLibrarySearchResult(hit.paper_id, hit.source_page)}
                        >
                          <span>{t("app.librarySearchPage", { page: hit.source_page })}</span>
                          <span>{hit.text}</span>
                        </button>
                      ))}
                    </section>
                  ))}
                </div>
              )}
            </details>
          )}

          {selectedPaper && (
            <details className="library-organizer">
              <summary>{t("app.organizePaper")}</summary>
              <div className="collection-create-row">
                <input
                  aria-label={t("app.newCollectionPlaceholder")}
                  placeholder={t("app.newCollectionPlaceholder")}
                  value={collectionDraft}
                  onChange={(event) => setCollectionDraft(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") void handleCreateCollection();
                  }}
                />
                <button type="button" onClick={() => void handleCreateCollection()}>
                  {t("app.createCollection")}
                </button>
              </div>
              <p className="organizer-label">{t("app.collectionMemberships")}</p>
              {collections.length === 0 ? (
                <p className="muted organizer-empty">{t("app.noCollections")}</p>
              ) : (
                <div className="collection-memberships">
                  {collections.map((collection) => (
                    <div key={collection.id}>
                      <label>
                        <input
                          type="checkbox"
                          checked={organizationCollectionIds.includes(collection.id)}
                          onChange={(event) => setOrganizationCollectionIds((current) =>
                            event.target.checked
                              ? [...current, collection.id]
                              : current.filter((id) => id !== collection.id),
                          )}
                        />
                        <span>{collection.name}</span>
                      </label>
                      <button
                        type="button"
                        aria-label={t("app.deleteCollectionAria", { name: collection.name })}
                        onClick={() => void handleDeleteCollection(collection)}
                      >
                        ×
                      </button>
                    </div>
                  ))}
                </div>
              )}
              <label className="tag-editor">
                <span>{t("app.tags")}</span>
                <input
                  value={tagDraft}
                  placeholder={t("app.tagsPlaceholder")}
                  onChange={(event) => setTagDraft(event.target.value)}
                />
              </label>
              <button
                type="button"
                className="save-organization"
                disabled={isSavingOrganization}
                onClick={() => void handleSaveOrganization()}
              >
                {isSavingOrganization ? t("app.savingOrganization") : t("app.saveOrganization")}
              </button>
              {organizationMessage && <p className="organization-message">{organizationMessage}</p>}
            </details>
          )}

          {isLoading && <p className="muted panel-message">{t("app.scanning")}</p>}
          {error && <p className="error panel-message">{error}</p>}
          {!isLoading && !error && papers.length === 0 && (
            <div className="panel-message empty-library">
              <strong>{t("app.emptyLibraryTitle")}</strong>
              <p>{t("app.emptyLibraryBody")}</p>
            </div>
          )}

          {!isLoading && papers.length > 0 && visiblePapers.length === 0 && (
            <p className="muted panel-message">{t("app.noFilteredPapers")}</p>
          )}

          <nav className="paper-list" aria-label={t("app.localPapersAria")}>
            {visiblePapers.map((paper) => (
              <button
                type="button"
                key={paper.id}
                className={paper.id === selectedPaperId ? "selected" : ""}
                onClick={() => choosePaper(paper.id)}
              >
                <span className="paper-icon">PDF</span>
                <span className="paper-details">
                  <strong>{paper.name}</strong>
                  <small>
                    {paper.page_count === null
                      ? t("app.pageCountFailed")
                      : t("app.pageCount", { count: paper.page_count })}
                  </small>
                  {paper.tags.length > 0 && (
                    <span className="paper-tags">{paper.tags.slice(0, 2).join(" · ")}</span>
                  )}
                </span>
              </button>
            ))}
          </nav>
        </aside>

        {selectedPaper ? (
          <>
            <PdfReader
              paper={selectedPaper}
              pageNumber={pageNumber}
              onPageChange={changePage}
              onTextSelection={setSelection}
              focusedSourceRegion={focusedSourceRegion}
            />
            {assistantOpen && (
              <AssistantPanel
                key={selectedPaper.id}
                paper={selectedPaper}
                pageNumber={pageNumber}
                selection={selection}
                onClearSelection={() => setSelection(null)}
                onNavigateToPage={changePage}
                onFocusSourceRegion={focusSourceRegion}
              />
            )}
          </>
        ) : isLoading ? (
          <section className="welcome-state">
            <h2>{t("app.scanning")}</h2>
          </section>
        ) : error ? (
          <section className="welcome-state startup-recovery">
            <h2>{t("app.serverUnavailableTitle")}</h2>
            <p>{t("app.serverUnavailableBody")}</p>
            <button type="button" onClick={() => setLoadAttempt((value) => value + 1)}>
              {t("app.retryConnection")}
            </button>
          </section>
        ) : (
          <section className="welcome-state">
            <h2>{t("app.welcomeTitle")}</h2>
            <p>{t("app.welcomeBody")}</p>
            <ol className="welcome-steps">
              <li>{t("app.welcomeStepImport")}</li>
              <li>{t("app.welcomeStepRead")}</li>
              <li>{t("app.welcomeStepVerify")}</li>
              <li>{t("app.welcomeStepSave")}</li>
            </ol>
            <label className="import-paper-button welcome-import-button">
              <input
                type="file"
                accept="application/pdf,.pdf"
                disabled={isImporting}
                onChange={(event) => {
                  void handlePdfImport(event.target.files?.[0]);
                  event.currentTarget.value = "";
                }}
              />
              {isImporting ? t("app.importing") : t("app.importFirstPdf")}
            </label>
          </section>
        )}
      </div>
    </main>
  );
}
