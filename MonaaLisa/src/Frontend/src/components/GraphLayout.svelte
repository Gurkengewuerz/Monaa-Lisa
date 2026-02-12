<!--
  GraphLayout.svelte
  Navigation state machine for the hierarchical graph views:
    top → subcategory → papers → paper detail
-->
<script lang="ts">
  import ClusterGraph from './ClusterGraph.svelte';
  import Graph from './Graph.svelte';
  import PaperDetailGraph from './PaperDetailGraph.svelte';
  import Header from './Header.svelte';
  import Sidebar from './Sidebar.svelte';
  import type { ApiPaper, Paper, PapersResponse, ClusterNode, ViewState } from '$lib/types/paper';
  import { env as publicEnv } from '$env/dynamic/public';
  import clusterData from '../utils/arxiv_cluster_data.json';

  const API_BASE_URL = publicEnv.PUBLIC_API_BASE_URL || 'http://localhost:3000';
  const PAPER_LIMIT = 5000;

  // ─── navigation state ─────────────────────────────────────────────
  let view: ViewState = { level: 'top' };

  // paper data (only loaded at papers/detail level)
  let papers: Paper[] = [];
  let sidebarOpen = false;
  let selectedPaperId: string | null = null;
  let loading = false;
  let error: string | null = null;

  // colour of the current parent category (passed to subcategory + papers)
  let currentCategoryColor: string = '#4a9eff';

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
      const pId = v.level === 'sub' ? v.parentId : '';
      crumbs.push({
        label: pName,
        action: () => {
          const pid = clusterData.find((c: any) => c.name === pName)?.id ?? '';
          view = { level: 'sub', parentName: pName, parentId: pid };
          papers = []; error = null;
        },
      });
    }

    if (v.level === 'papers' || v.level === 'detail') {
      const cId = v.categoryId;
      const cName = v.categoryName;
      const pName = v.parentName;
      crumbs.push({
        label: cName,
        action: () => {
          view = { level: 'papers', categoryId: cId, categoryName: cName, parentName: pName };
          loadPapers(cId);
        },
      });
    }

    if (v.level === 'detail') {
      crumbs.push({ label: truncate(v.paper.title, 35), action: () => {} });
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
    view = {
      level: 'detail',
      paper: e.detail,
      categoryId: view.categoryId,
      categoryName: view.categoryName,
      parentName: view.parentName,
    };
  }

  function handleDetailBack() {
    if (view.level !== 'detail') return;
    view = {
      level: 'papers',
      categoryId: view.categoryId,
      categoryName: view.categoryName,
      parentName: view.parentName,
    };
  }

  function handleSidebarSelect(e: CustomEvent<Paper>) {
    // In papers view: navigate to detail
    if (view.level === 'papers') {
      view = {
        level: 'detail',
        paper: e.detail,
        categoryId: view.categoryId,
        categoryName: view.categoryName,
        parentName: view.parentName,
      };
    }
  }

  function handleToggleSidebar() {
    sidebarOpen = !sidebarOpen;
  }

  function handleNodeDeselected() {
    selectedPaperId = null;
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

      if (!papers.length) error = 'Keine Papers für diese Kategorie gefunden.';
    } catch (err) {
      error = err instanceof Error ? err.message : 'Fehler beim Laden.';
      papers = [];
    } finally {
      loading = false;
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
</script>

<!-- main app container -->
<div class="app-container">
  <Header />

  <!-- breadcrumb bar -->
  <nav class="breadcrumbs">
    {#each breadcrumbs as crumb, i}
      {#if i > 0}<span class="sep">›</span>{/if}
      {#if i < breadcrumbs.length - 1}
        <button class="crumb" on:click={crumb.action}>{crumb.label}</button>
      {:else}
        <span class="crumb current">{crumb.label}</span>
      {/if}
    {/each}
  </nav>

  <div class="main-content">
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
          <p>Lade Papers für {view.categoryName}…</p>
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
        <Sidebar
          {papers}
          isOpen={sidebarOpen}
          {selectedPaperId}
          on:toggle={handleToggleSidebar}
          on:selectPaper={handleSidebarSelect}
        />
      {/if}

    <!-- ── PAPER DETAIL VIEW ── -->
    {:else if view.level === 'detail'}
      <PaperDetailGraph
        paper={view.paper}
        apiBaseUrl={API_BASE_URL}
        on:back={handleDetailBack}
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
    background-color: #1e1e27;
    color: white;
    overflow: hidden;
  }

  .breadcrumbs {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 6px 16px;
    background: #252530;
    border-bottom: 1px solid #333;
    font-size: 13px;
    flex-shrink: 0;
  }

  .sep {
    color: #555;
    margin: 0 2px;
  }

  .crumb {
    background: none;
    border: none;
    color: #7aa8e8;
    cursor: pointer;
    padding: 2px 4px;
    border-radius: 4px;
    font-size: 13px;
  }
  .crumb:hover { background: rgba(74,158,255,0.15); }
  .crumb.current {
    color: #e0e6ed;
    cursor: default;
  }

  .main-content {
    flex: 1;
    position: relative;
    display: flex;
    overflow: hidden;
  }

  :global(.graph-wrapper),
  :global(.cluster-canvas),
  :global(.detail-wrapper) {
    width: 100% !important;
    height: 100% !important;
  }

  .status-card {
    margin: auto;
    padding: 2rem;
    border-radius: 1rem;
    border: 1px solid #27313a;
    background-color: #232b32;
    color: #e0e6ed;
    text-align: center;
    display: flex;
    flex-direction: column;
    gap: 1rem;
    min-width: 320px;
  }

  .status-card.error {
    border-color: #f56565;
  }

  .status-card button {
    align-self: center;
    background: #4a9eff;
    border: none;
    border-radius: 999px;
    color: white;
    cursor: pointer;
    padding: 0.5rem 1.5rem;
    font-weight: 600;
  }
</style>