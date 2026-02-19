<!--
  GraphLayout.svelte
  Navigation state machine for the hierarchical graph views:
    top → subcategory → papers → paper detail
-->
<script lang="ts">
  import { onMount } from 'svelte';
  import ClusterGraph from './ClusterGraph.svelte';
  import Graph from './Graph.svelte';
  import PaperDetailGraph from './PaperDetailGraph.svelte';
  import Header from './Header.svelte';
  import Sidebar from './Sidebar.svelte';
  import PaperSidebar from './PaperSidebar.svelte';
  import MetricCards from './MetricCards.svelte';
  import Dashboard from './Dashboard.svelte';
  import type { ApiPaper, Paper, PapersResponse, ClusterNode, ViewState, PaperSession } from '$lib/types/paper';
  import { env as publicEnv } from '$env/dynamic/public';
  import clusterData from '../utils/arxiv_cluster_data.json';
  import { SUBCATEGORY_TO_TOPLEVEL, getSubcategoryName, getTopLevelCategory } from '../utils/arxivTaxonomy';

  const API_BASE_URL = publicEnv.PUBLIC_API_BASE_URL || 'http://localhost:3000';
  const PAPER_LIMIT  = 5000;
  const SIDEBAR_SAMPLE = 50;   // papers shown in sidebar at cluster levels
  const MAX_HISTORY  = 5;
  const HISTORY_KEY  = 'monaalisa_paper_sessions_v1';

  // ─── navigation state ─────────────────────────────────────────────
  let view: ViewState = { level: 'top' };
  /** View to return to when pressing back from detail */
  let previousView: ViewState = { level: 'top' };

  // paper data (only loaded at papers/detail level)
  let papers: Paper[] = [];
  // sample papers for sidebar in cluster views (top / sub)
  let sidebarSamplePapers: Paper[] = [];

  let sidebarOpen = false;
  let selectedPaperId: string | null = null;
  let loading = false;
  let error: string | null = null;

  // ─── dashboard ────────────────────────────────────────────────────
  let dashboardOpen = false;
  let dashboardRef: Dashboard;
  /** Incremented whenever favorites change forces re-evaluation of isFavorite */
  let favoritesVersion = 0;

  function openDashboard()   { dashboardOpen = true; }
  function closeDashboard()  { dashboardOpen = false; }

  function handleFavoritePaper(e: CustomEvent<Paper>) {
    if (dashboardRef) dashboardRef.toggleFavorite(e.detail);
    favoritesVersion += 1; // trigger reactive re-render
  }

  // colour of the current parent category (passed to subcategory + papers)
  let currentCategoryColor: string = '#4a9eff';

  // ─── arXiv neighbourhood counts (from PaperDetailGraph) ──────────
  let arxivCitationCount: number | undefined = undefined;
  let arxivReferenceCount: number | undefined = undefined;

  // ─── paper browsing history (localStorage) ────────────────────────
  let sessions: PaperSession[] = loadSessions();

  function loadSessions(): PaperSession[] {
    try {
      const raw = typeof localStorage !== 'undefined' ? localStorage.getItem(HISTORY_KEY) : null;
      return raw ? JSON.parse(raw) : [];
    } catch { return []; }
  }

  function saveSessions(list: PaperSession[]) {
    try {
      if (typeof localStorage !== 'undefined') {
        localStorage.setItem(HISTORY_KEY, JSON.stringify(list));
      }
    } catch {}
  }

  function addSession(paper: Paper) {
    const newSession: PaperSession = {
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
      mainPaper: { entry_id: paper.entry_id, title: paper.title, authors: paper.authors },
      startedAt: Date.now(),
    };
    sessions = [newSession, ...sessions.filter(s => s.mainPaper.entry_id !== paper.entry_id)].slice(0, MAX_HISTORY);
    saveSessions(sessions);
    return newSession.id;
  }

  function deleteSessionById(sessionId: string) {
    sessions = sessions.filter(s => s.id !== sessionId);
    saveSessions(sessions);
  }

  // ─── category prefix for sub-level sidebar loading ────────────────
  const CLUSTER_CAT_PREFIX: Record<string, string> = {
    computer_science:       'cs.',
    mathematics:            'math.',
    statistics:             'stat.',
    electrical_engineering: 'eess.',
    quantitative_biology:   'q-bio.',
    quantitative_finance:   'q-fin.',
    economics:              'econ.',
    physics:                'physics.',
  };

  /**
   * Given a paper's primary category (e.g. "cs.AI"), derive the full
   * ViewState detail fields so breadcrumbs show the proper hierarchy.
   */
  function resolveDetailContext(paper: Paper): { categoryId: string; categoryName: string; parentName: string } {
    const firstCat = (paper.categories ?? '').trim().split(/[\s,]+/)[0] ?? '';
    if (!firstCat) return { categoryId: '', categoryName: '', parentName: '' };
    // subcategory name e.g. "Artificial Intelligence"
    const subName = getSubcategoryName(firstCat);
    // top-level name e.g. "Computer Science"
    const topName = getTopLevelCategory(firstCat);
    return {
      categoryId: firstCat,
      categoryName: subName !== firstCat ? subName : firstCat,
      parentName: topName !== 'Other' ? topName : '',
    };
  }

  // reactive cluster count for metric cards
  $: currentClusterCount = (() => {
    if (view.level === 'top') return topClusters.length;
    if (view.level === 'sub') return getSubclusters(view.parentId).length;
    return 0;
  })();

  // ─── top-level cluster data from static JSON ──────────────────────
  const CATEGORY_COLORS: Record<string, string> = {
    physics:                '#4361ee',
    computer_science:       '#f72585',
    mathematics:            '#4cc9f0',
    statistics:             '#7209b7',
    electrical_engineering: '#ff7a18',
    quantitative_biology:   '#2ec4b6',
    quantitative_finance:   '#ffd166',
    economics:              '#e71d36',
  };

  const topClusters: ClusterNode[] = clusterData.map((cat: any) => ({
    id: cat.id,
    name: cat.name,
    count: cat.total_count,
  }));

  function getSubclusters(parentId: string): ClusterNode[] {
    const parent = clusterData.find((c: any) => c.id === parentId);
    return (parent?.children ?? []).map((sub: any) => ({
      id: sub.id,
      name: sub.name,
      count: sub.value,
    }));
  }

  // ─── breadcrumbs ──────────────────────────────────────────────────
  interface Crumb { label: string; action: () => void }

  $: breadcrumbs = buildCrumbs(view);

  function buildCrumbs(v: ViewState): Crumb[] {
    const crumbs: Crumb[] = [
      { label: 'All Categories', action: () => { view = { level: 'top' }; papers = []; error = null; } },
    ];

    if (v.level === 'sub' || v.level === 'papers' || v.level === 'detail') {
      const pName = v.parentName;
      if (!pName) return crumbs; // avoid empty/clickable-but-empty crumbs
      const pId = v.level === 'sub' ? v.parentId : '';
      crumbs.push({
        label: pName,
        action: () => {
          const pid = clusterData.find((c: any) => c.name === pName)?.id ?? '';
          if (!pid) return; // guard: no matching cluster, don't crash
          view = { level: 'sub', parentName: pName, parentId: pid };
          papers = []; error = null;
          loadSamplePapers('sub', pid);
        },
      });
    }

    if (v.level === 'papers' || v.level === 'detail') {
      const cId = v.categoryId;
      const cName = v.categoryName;
      const pName = v.parentName;
      if (!cId && !cName) return crumbs; // guard: empty category context
      crumbs.push({
        label: cName || cId,
        action: () => {
          if (!cId) return;
          view = { level: 'papers', categoryId: cId, categoryName: cName, parentName: pName };
          loadPapers(cId);
        },
      });
    }

    if (v.level === 'detail') {
      crumbs.push({ label: v.paper.title, action: () => {} });
    }

    return crumbs;
  }

  function truncate(s: string, n: number): string {
    return s.length > n ? s.slice(0, n) + '…' : s;
  }

  // ─── navigation handlers ──────────────────────────────────────────
  function handleTopClusterClick(e: CustomEvent<{ id: string; name: string; color: string }>) {
    currentCategoryColor = e.detail.color;
    view = { level: 'sub', parentName: e.detail.name, parentId: e.detail.id };
    papers = [];
    error = null;
    loadSamplePapers('sub', e.detail.id);
  }

  function handleSubClusterClick(e: CustomEvent<{ id: string; name: string; color: string }>) {
    if (view.level !== 'sub') return;
    currentCategoryColor = e.detail.color;
    view = {
      level: 'papers',
      categoryId: e.detail.id,
      categoryName: e.detail.name,
      parentName: view.parentName,
    };
    loadPapers(e.detail.id);
  }

  function handlePaperSelected(e: CustomEvent<Paper>) {
    if (view.level !== 'papers') return;
    const paper = e.detail;
    arxivCitationCount  = undefined;
    arxivReferenceCount = undefined;
    previousView = view;
    addSession(paper);
    view = {
      level: 'detail',
      paper,
      categoryId: view.categoryId,
      categoryName: view.categoryName,
      parentName: view.parentName,
    };
    if (dashboardRef) dashboardRef.addToHistory(paper);
  }

  function handleDetailBack() {
    if (view.level !== 'detail') return;
    arxivCitationCount  = undefined;
    arxivReferenceCount = undefined;
    // Return to wherever we came from (papers, sub, or top)
    view = previousView;
  }

  function handleSidebarSelect(e: CustomEvent<Paper>) {
    const paper = e.detail;
    arxivCitationCount  = undefined;
    arxivReferenceCount = undefined;
    previousView = view;
    addSession(paper);
    // Always derive proper category hierarchy from the paper itself
    const ctx = resolveDetailContext(paper);
    const catId   = ctx.categoryId   || ((view.level === 'papers' || view.level === 'detail') ? view.categoryId   : '');
    const catName = ctx.categoryName || ((view.level === 'papers' || view.level === 'detail') ? view.categoryName : '');
    const parName = ctx.parentName   || ((view.level !== 'top') ? (view as any).parentName ?? '' : '');
    view = { level: 'detail', paper, categoryId: catId, categoryName: catName, parentName: parName };
    if (dashboardRef) dashboardRef.addToHistory(paper);
  }

  /** Called when PaperDetailGraph emits navigate (click on a graph node) */
  function handleGraphNavigate(e: CustomEvent<Paper>) {
    if (view.level !== 'detail') return;
    const paper = e.detail;
    arxivCitationCount  = undefined;
    arxivReferenceCount = undefined;
    previousView = view;
    addSession(paper);
    view = {
      level: 'detail',
      paper,
      categoryId: view.categoryId,
      categoryName: view.categoryName,
      parentName: view.parentName,
    };
    if (dashboardRef) dashboardRef.addToHistory(paper);
  }

  /** Called when PaperSidebar emits navigate (click on a citation/reference) */
  function handlePaperSidebarNavigate(e: CustomEvent<Paper>) {
    if (view.level !== 'detail') return;
    const paper = e.detail;
    arxivCitationCount  = undefined;
    arxivReferenceCount = undefined;
    previousView = view;
    view = {
      level: 'detail',
      paper,
      categoryId: view.categoryId,
      categoryName: view.categoryName,
      parentName: view.parentName,
    };
    if (dashboardRef) dashboardRef.addToHistory(paper);
  }

  function handleToggleSidebar() {
    sidebarOpen = !sidebarOpen;
  }

  function handleNodeDeselected() {
    selectedPaperId = null;
  }

  function handleNeighbourhoodLoaded(e: CustomEvent<{ citationCount: number; referenceCount: number }>) {
    arxivCitationCount  = e.detail.citationCount;
    arxivReferenceCount = e.detail.referenceCount;
  }

  function handleDeleteSession(e: CustomEvent<string>) {
    deleteSessionById(e.detail);
  }

  async function handleRestoreSession(e: CustomEvent<PaperSession>) {
    const session = e.detail;
    // Try to find the paper in the currently loaded set first (fast path)
    let paper: Paper | null =
      papers.find(p => p.entry_id === session.mainPaper.entry_id) ??
      sidebarSamplePapers.find(p => p.entry_id === session.mainPaper.entry_id) ??
      null;

    if (!paper) {
      // Try dedicated single-paper endpoint
      try {
        const res = await fetch(`${API_BASE_URL}/papers/${encodeURIComponent(session.mainPaper.entry_id)}`);
        if (res.ok) {
          const raw: ApiPaper = await res.json();
          paper = normalizePaper(raw, 0, 1);
        }
      } catch { /* fall through */ }
    }

    if (!paper) {
      // Fall back to title search
      try {
        const res = await fetch(
          `${API_BASE_URL}/papers?search=${encodeURIComponent(session.mainPaper.title.slice(0, 80))}&take=10`
        );
        if (res.ok) {
          const payload = await res.json();
          const rawItems: ApiPaper[] = Array.isArray(payload) ? payload : payload?.items ?? [];
          const found = rawItems.find(p => p.entry_id === session.mainPaper.entry_id);
          if (found) paper = normalizePaper(found, 0, 1);
        }
      } catch { /* ignore */ }
    }

    if (paper) {
      arxivCitationCount  = undefined;
      arxivReferenceCount = undefined;
      previousView = view;
      // Always derive proper category hierarchy from the paper itself
      const ctx = resolveDetailContext(paper);
      const catId   = ctx.categoryId   || (view.level === 'papers' ? view.categoryId   : '');
      const catName = ctx.categoryName || (view.level === 'papers' ? view.categoryName : '');
      const parName = ctx.parentName   || (view.level === 'papers' ? view.parentName   : '');
      view = { level: 'detail', paper, categoryId: catId, categoryName: catName, parentName: parName };
      if (dashboardRef) dashboardRef.addToHistory(paper);
    }
  }

  // ─── data loading ─────────────────────────────────────────────────
  async function loadPapers(categoryId: string) {
    loading = true;
    error = null;
    papers = [];
    try {
      const url = `${API_BASE_URL}/papers?categories=${encodeURIComponent(categoryId)}&take=${PAPER_LIMIT}&skip=0&sort=citations`;
      const response = await fetch(url);
      if (!response.ok) throw new Error(`Backend ${response.status}`);

      const payload = (await response.json()) as Partial<PapersResponse> | ApiPaper[];
      const rawItems = Array.isArray(payload) ? payload : payload?.items ?? [];

      papers = rawItems
        .map((item, i, a) => normalizePaper(item as ApiPaper, i, a.length))
        .filter((p): p is Paper => Boolean(p));

      // sidebar shows all the loaded papers in papers-level view
      sidebarSamplePapers = papers;

      if (!papers.length) error = 'Keine Papers für diese Kategorie gefunden.';
    } catch (err) {
      error = err instanceof Error ? err.message : 'Fehler beim Laden.';
      papers = [];
    } finally {
      loading = false;
    }
  }

  /**
   * Load a sample of papers for the sidebar in top / sub cluster views.
   * @param level  'top' or 'sub'
   * @param parentId  cluster id (for sub level); unused at top level
   */
  async function loadSamplePapers(level: 'top' | 'sub', parentId?: string) {
    try {
      let categoryParam = '';
      if (parentId) {
        const prefix = CLUSTER_CAT_PREFIX[parentId] ?? '';
        categoryParam = prefix ? `&categories=${encodeURIComponent(prefix)}` : '';
      }
      const url = `${API_BASE_URL}/papers?take=${SIDEBAR_SAMPLE}&skip=0&sort=citations${categoryParam}`;
      const res = await fetch(url);
      if (!res.ok) return;
      const payload = (await res.json()) as Partial<PapersResponse> | ApiPaper[];
      const rawItems = Array.isArray(payload) ? payload : payload?.items ?? [];
      sidebarSamplePapers = rawItems
        .map((item, i, a) => normalizePaper(item as ApiPaper, i, a.length))
        .filter((p): p is Paper => Boolean(p));
    } catch {
      sidebarSamplePapers = [];
    }
  }

  // ─── paper normalisation (carried over) ───────────────────────────
  function normalizePaper(raw: ApiPaper, index: number, total: number): Paper | null {
    if (!raw?.entry_id || !raw?.title) return null;
    return {
      id: Number(raw.id ?? index),
      entry_id: raw.entry_id,
      title: raw.title,
      authors: formatAuthors(raw.authors),
      abstract: raw.abstract ?? '',
      published: raw.published ?? null,
      categories: raw.categories ?? null,
      url: raw.url ?? null,
      citations: deriveStringArray(raw.citations),
      references: deriveStringArray(raw.references),
      non_arxiv_citation_count: raw.non_arxiv_citation_count ?? 0,
      non_arxiv_reference_count: raw.non_arxiv_reference_count ?? 0,
      tsne1: 0,
      tsne2: 0,
      cluster: raw.categories ?? 'U',
    };
  }

  function formatAuthors(a: ApiPaper['authors']): string {
    if (!a) return '';
    return Array.isArray(a) ? a.join(', ') : a;
  }

  function deriveStringArray(value: unknown): string[] {
    if (!value) return [];
    if (Array.isArray(value)) {
      return value
        .map(item => {
          if (typeof item === 'string') return item;
          if (typeof item === 'number') return item.toString();
          if (item && typeof item === 'object' && 'entry_id' in item) return (item as any).entry_id ?? '';
          return '';
        })
        .filter(Boolean);
    }
    if (typeof value === 'string') return value.split(',').map(s => s.trim()).filter(Boolean);
    return [];
  }

  // ─── load initial sample papers for top-level sidebar ────────────  // sidebar label: human-readable name for the current view level
  $: sidebarLabel = (() => {
    if (view.level === 'top')    return 'ArXiv';
    if (view.level === 'sub')    return view.parentName;
    if (view.level === 'papers') return view.categoryName;
    if (view.level === 'detail') return view.categoryName || view.parentName || 'Paper';
    return 'ArXiv';
  })();
  onMount(() => {
    // Don't load papers at top level by default
  });
</script>

<!-- main app container -->
<div class="app-container">

  <!-- Dashboard slide-in panel -->
  <Dashboard
    bind:this={dashboardRef}
    isOpen={dashboardOpen}
    on:close={closeDashboard}
    on:navigate={(e) => {
      // Navigate to a paper from the dashboard
      const item = e.detail;
      const paper: Paper = {
        id: 0, entry_id: item.entry_id, title: item.title, authors: item.authors,
        abstract: '', published: item.published, categories: item.categories,
        url: null, citations: [], references: [],
        non_arxiv_citation_count: 0, non_arxiv_reference_count: 0,
        tsne1: 0, tsne2: 0, cluster: item.categories ?? 'U',
      };
      previousView = view;
      const ctx = resolveDetailContext(paper);
      view = { level: 'detail', paper,
        categoryId: ctx.categoryId, categoryName: ctx.categoryName, parentName: ctx.parentName };
      dashboardOpen = false;
    }}
  />

  <Header />

  <!-- metric cards row -->
  <MetricCards
    {view}
    paperCount={papers.length}
    clusterCount={currentClusterCount}
    {arxivCitationCount}
    {arxivReferenceCount}
  />

  <!-- breadcrumb bar -->
  <nav class="breadcrumbs">
    <button class="db-toggle-btn" on:click={openDashboard} title="Open Dashboard">
      &#9776; Dashboard
    </button>
    <span class="crumb-sep-line"></span>
    {#each breadcrumbs as crumb, i}
      {#if i > 0}<span class="sep">›</span>{/if}
      {#if i < breadcrumbs.length - 1}
        <button class="crumb" on:click={crumb.action}>{crumb.label}</button>
      {:else}
        <!-- Last crumb: full paper title (truncated to keep breadcrumb manageable) -->
        <span class="crumb current" title={crumb.label}>
          {crumb.label.length > 80 ? crumb.label.slice(0, 80) + '…' : crumb.label}
        </span>
      {/if}
    {/each}
  </nav>

  <div class="main-content">
    <!-- ── graph panel (central area) ── -->
    <div class="graph-panel">
      <!-- ── TOP-LEVEL CLUSTERS ── -->
      {#if view.level === 'top'}
        <ClusterGraph
          clusters={topClusters}
          parentColor={null}
          on:clusterClick={handleTopClusterClick}
        />

      <!-- ── SUBCATEGORY CLUSTERS ── -->
      {:else if view.level === 'sub'}
        <ClusterGraph
          clusters={getSubclusters(view.parentId)}
          parentColor={CATEGORY_COLORS[view.parentId] ?? '#4a9eff'}
          on:clusterClick={handleSubClusterClick}
        />

      <!-- ── PAPERS VIEW ── -->
      {:else if view.level === 'papers'}
        {#if loading}
          <div class="status-card">
            <div class="status-spinner"></div>
            <p>Fetching Papers for {view.categoryName}…</p>
          </div>
        {:else if error}
          <div class="status-card error">
            <p>{error}</p>
            <button on:click={() => loadPapers(view.categoryId)}>Erneut versuchen</button>
          </div>
        {:else}
          <Graph
            {papers}
            {selectedPaperId}
            categoryColor={currentCategoryColor}
            on:paperSelected={handlePaperSelected}
            on:nodeDeselected={handleNodeDeselected}
          />
        {/if}

      <!-- ── PAPER DETAIL VIEW ── -->
      {:else if view.level === 'detail'}
        {#key view.paper.entry_id}
        <PaperDetailGraph
          paper={view.paper}
          apiBaseUrl={API_BASE_URL}
          on:back={handleDetailBack}
          on:neighbourhoodLoaded={handleNeighbourhoodLoaded}
          on:navigate={handleGraphNavigate}
        />
        {/key}
      {/if}
    </div>

    <!-- ── right sidebar panel ── -->
    {#if view.level === 'detail'}
      <!-- Paper sidebar with citations, references, history -->
      {#key view.paper.entry_id}
      <PaperSidebar
        paper={view.paper}
        apiBaseUrl={API_BASE_URL}
        isOpen={sidebarOpen}
        isFavorite={favoritesVersion >= 0 && dashboardRef ? dashboardRef.isFavorite(view.paper.entry_id) : false}
        on:toggle={handleToggleSidebar}
        on:navigate={handlePaperSidebarNavigate}
        on:favorite={handleFavoritePaper}
      />
      {/key}
    {:else}
      <!-- Category sidebar with paper list -->
      <Sidebar
        papers={view.level === 'papers' ? papers : sidebarSamplePapers}
        isOpen={sidebarOpen}
        {selectedPaperId}
        categoryFilter={view.level === 'papers' || view.level === 'detail' ? view.categoryId : view.level === 'sub' ? (CLUSTER_CAT_PREFIX[(view as any).parentId] ?? '') : ''}
        categoryLabel={sidebarLabel}
        apiBaseUrl={API_BASE_URL}
        on:toggle={handleToggleSidebar}
        on:selectPaper={handleSidebarSelect}
      />
    {/if}
  </div>
</div>

<style>
  .app-container {
    width: 100vw;
    height: 100vh;
    display: flex;
    flex-direction: column;
    background-color: var(--bg-primary, #0F1020);
    color: var(--text-primary, #f0f0f8);
    overflow: hidden;
  }

  .breadcrumbs {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 5px 16px;
    background: var(--bg-secondary, #141530);
    border-bottom: 1px solid var(--glass-border, rgba(255,255,255,0.08));
    font-size: 12px;
    flex-shrink: 0;
  }

  .db-toggle-btn {
    background: none;
    border: 1px solid rgba(255,255,255,0.10);
    color: var(--text-secondary, #a8a8c8);
    font-size: 11px;
    padding: 3px 10px;
    border-radius: var(--radius-sm, 8px);
    cursor: pointer;
    transition: all 0.15s ease;
    flex-shrink: 0;
    white-space: nowrap;
  }
  .db-toggle-btn:hover {
    background: rgba(147,51,234,0.15);
    color: var(--text-primary, #f0f0f8);
    border-color: rgba(147,51,234,0.35);
  }

  .crumb-sep-line {
    width: 1px;
    height: 14px;
    background: var(--glass-border, rgba(255,255,255,0.12));
    flex-shrink: 0;
    margin: 0 4px;
  }

  .sep {
    color: var(--text-muted, #6b6b8d);
    margin: 0 2px;
  }

  .crumb {
    background: none;
    border: none;
    color: var(--accent-cyan, #22d3ee);
    cursor: pointer;
    padding: 2px 6px;
    border-radius: var(--radius-sm, 8px);
    font-size: 12px;
    transition: all var(--transition-fast, 0.15s ease);
  }
  .crumb:hover {
    background: rgba(34, 211, 238, 0.12);
    color: #fff;
  }
  .crumb.current {
    color: var(--text-primary, #f0f0f8);
    cursor: default;
  }

  .main-content {
    flex: 1;
    position: relative;
    display: flex;
    overflow: hidden;
  }

  .graph-panel {
    flex: 1;
    position: relative;
    display: flex;
    overflow: hidden;
    border-radius: var(--radius-md, 12px);
    margin: 0 4px 4px 4px;
    border: 1px solid var(--glass-border, rgba(255,255,255,0.08));
    background: var(--bg-primary, #0F1020);
  }

  :global(.graph-wrapper),
  :global(.cluster-canvas),
  :global(.cluster-container),
  :global(.detail-wrapper) {
    width: 100% !important;
    height: 100% !important;
  }

  .status-card {
    margin: auto;
    padding: 2rem 3rem;
    border-radius: var(--radius-lg, 16px);
    border: 1px solid var(--border-subtle, rgba(147,51,234,0.18));
    background: var(--glass-bg, rgba(20, 22, 50, 0.55));
    backdrop-filter: blur(var(--glass-blur, 16px));
    color: var(--text-primary, #f0f0f8);
    text-align: center;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 1rem;
    min-width: 320px;
    box-shadow: var(--shadow-glow-sm);
  }

  .status-spinner {
    width: 28px;
    height: 28px;
    border: 3px solid rgba(147, 51, 234, 0.2);
    border-top-color: var(--accent-cyan, #22d3ee);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  .status-card.error {
    border-color: rgba(245, 101, 101, 0.4);
    box-shadow: 0 0 20px rgba(245, 101, 101, 0.15);
  }

  .status-card button {
    align-self: center;
    background: linear-gradient(135deg, var(--accent-purple), var(--accent-magenta));
    border: none;
    border-radius: 999px;
    color: white;
    cursor: pointer;
    padding: 0.5rem 1.5rem;
    font-weight: 600;
    transition: all var(--transition-smooth);
    box-shadow: 0 0 15px rgba(147, 51, 234, 0.3);
  }

  .status-card button:hover {
    transform: translateY(-1px);
    box-shadow: 0 0 25px rgba(147, 51, 234, 0.5);
  }
</style>