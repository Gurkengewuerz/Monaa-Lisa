<!--
  PaperDetailGraph.svelte
  Sigma.js network view for a single paper + its citations & references.
  Features:
    - Citation Graph view (sigma.js)  ·  Relation View (placeholder)
    - Expandable InfoView with full paper metadata
    - Filter controls: show/hide citations, references, non-arXiv
-->
<script lang="ts">
  import { createEventDispatcher, onMount, onDestroy } from 'svelte';
  import GraphLib from 'graphology';
  import Sigma from 'sigma';
  import type { Paper } from '$lib/types/paper';
  import { getSubcategoryName } from '../utils/arxivTaxonomy';

  /** The paper whose neighbourhood we are visualising. */
  export let paper: Paper;
  /** NestJS backend base URL. */
  export let apiBaseUrl: string = 'http://localhost:3000';

  let container: HTMLDivElement | null = null;
  let renderer: Sigma | null = null;
  let graph: GraphLib | null = null;
  let loading = true;
  let errorMsg: string | null = null;

  // ─── view mode ────────────────────────────────────────────────────
  /** 'graph' = Citation Network view  |  'relation' = Relation/Similarity view (future) */
  let viewMode: 'graph' | 'relation' = 'graph';

  // ─── info view ────────────────────────────────────────────────────
  let abstractExpanded = false;

  /** Format categories string: "cs.AI math.LG" → "Artificial Intelligence (cs.AI) · Machine Learning (cs.LG)" */
  function formatCategories(cats: string | null): string {
    if (!cats) return '';
    return cats.trim().split(/[\s,]+/)
      .filter(Boolean)
      .map(c => { const n = getSubcategoryName(c); return n !== c ? `${n} (${c})` : c; })
      .join(' · ');
  }

  // ─── filters ──────────────────────────────────────────────────────
  let showCitations = true;
  let showReferences = true;
  let showNonArxiv = true;

  const dispatch = createEventDispatcher<{
    back: void;
    'neighbourhoodLoaded': { citationCount: number; referenceCount: number };
    navigate: Paper;
  }>();

  // ─── colours ──────────────────────────────────────────────────────
  const COLOR_CENTER    = '#00ff88';
  const COLOR_CITATION  = '#ff6b6b';
  const COLOR_REFERENCE = '#4ecdc4';
  const COLOR_DUMMY     = '#555555';

  // ─── raw fetched data (cached for filter rebuilds) ────────────────
  interface CitationRow  { belonging_paper_entry_id: string; cited_paper_entry_id: string }
  interface ReferenceRow { belonging_paper_entry_id: string; referenced_paper_entry_id: string }
  interface FetchedData {
    citations:     CitationRow[];
    references:    ReferenceRow[];
    citedIds:      string[];
    referencedIds: string[];
    realPapers:    Record<string, any>;
  }

  let fetchedData: FetchedData | null = null;

  // ─── data fetching ────────────────────────────────────────────────
  async function fetchNeighbourhood() {
    const [citRes, refRes] = await Promise.all([
      fetch(`${apiBaseUrl}/paper-citations/paper/${encodeURIComponent(paper.entry_id)}`),
      fetch(`${apiBaseUrl}/paper-references/paper/${encodeURIComponent(paper.entry_id)}`),
    ]);

    const citations: CitationRow[]   = citRes.ok  ? await citRes.json()  : [];
    const references: ReferenceRow[] = refRes.ok  ? await refRes.json()  : [];

    const citedIds      = citations.map(c => c.cited_paper_entry_id);
    const referencedIds = references.map(r => r.referenced_paper_entry_id);
    const allIds = [...new Set([...citedIds, ...referencedIds])];

    let realPapers: Record<string, any> = {};
    if (allIds.length > 0) {
      const batchSize = 500;
      const batches: string[][] = [];
      for (let i = 0; i < allIds.length; i += batchSize) {
        batches.push(allIds.slice(i, i + batchSize));
      }
      const results = await Promise.all(
        batches.map(ids =>
          fetch(`${apiBaseUrl}/papers/batch`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ entryIds: ids }),
          }).then(r => r.ok ? r.json() : [])
        ),
      );
      results.flat().forEach((p: any) => { realPapers[p.entry_id] = p; });
    }

    return { citations, references, citedIds, referencedIds, realPapers };
  }

  // ─── graph building (filter-aware) ───────────────────────────────
  function buildGraph(data: FetchedData) {
    const g = new GraphLib();

    g.addNode(paper.entry_id, {
      x: 0, y: 0, size: 14,
      label: paper.title,
      color: COLOR_CENTER,
    });

    const CITATION_LIMIT  = 150;
    const REFERENCE_LIMIT = 150;

    if (showCitations) {
      const citIds = [...new Set(data.citedIds)].slice(0, CITATION_LIMIT);
      const step   = citIds.length > 0 ? (Math.PI * 2) / citIds.length : 0;
      citIds.forEach((id, i) => {
        const angle = i * step - Math.PI / 2;
        const real  = data.realPapers[id];
        const label = real ? truncate(real.title, 50) : id.slice(0, 20);
        const color = real ? COLOR_CITATION : COLOR_DUMMY;
        const size  = real ? 5 : 3;
        if (!g.hasNode(id)) {
          g.addNode(id, { x: 12 * Math.cos(angle), y: 12 * Math.sin(angle), size, label, color });
        }
        g.addEdge(paper.entry_id, id, { color: 'rgba(255,107,107,0.35)', size: 0.6, type: 'arrow' });
      });
    }

    if (showReferences) {
      const refIds = [...new Set(data.referencedIds)]
        .filter(id => !data.citedIds.includes(id))
        .slice(0, REFERENCE_LIMIT);
      const step = refIds.length > 0 ? (Math.PI * 2) / refIds.length : 0;
      refIds.forEach((id, i) => {
        const angle = i * step - Math.PI / 2;
        const real  = data.realPapers[id];
        const label = real ? truncate(real.title, 50) : id.slice(0, 20);
        const color = real ? COLOR_REFERENCE : COLOR_DUMMY;
        const size  = real ? 4.5 : 2.5;
        if (!g.hasNode(id)) {
          g.addNode(id, { x: 25 * Math.cos(angle), y: 25 * Math.sin(angle), size, label, color });
        }
        g.addEdge(id, paper.entry_id, { color: 'rgba(78,205,196,0.30)', size: 0.5, type: 'arrow' });
      });
    }

    if (showNonArxiv) {
      const dummyCit = Math.min(paper.non_arxiv_citation_count  ?? 0, 60);
      const dummyRef = Math.min(paper.non_arxiv_reference_count ?? 0, 60);
      for (let i = 0; i < dummyCit; i++) {
        const angle = i * ((Math.PI * 2) / Math.max(dummyCit, 1));
        const id = `__dummy_cit_${i}`;
        g.addNode(id, { x: 18 * Math.cos(angle), y: 18 * Math.sin(angle), size: 1.5, label: '', color: COLOR_DUMMY });
        g.addEdge(paper.entry_id, id, { color: 'rgba(85,85,85,0.15)', size: 0.3 });
      }
      for (let i = 0; i < dummyRef; i++) {
        const angle = i * ((Math.PI * 2) / Math.max(dummyRef, 1)) + 0.1;
        const id = `__dummy_ref_${i}`;
        g.addNode(id, { x: 35 * Math.cos(angle), y: 35 * Math.sin(angle), size: 1.5, label: '', color: COLOR_DUMMY });
        g.addEdge(id, paper.entry_id, { color: 'rgba(85,85,85,0.12)', size: 0.3 });
      }
    }

    return g;
  }

  function truncate(s: string, n: number): string {
    return s.length > n ? s.slice(0, n) + '…' : s;
  }

  // ─── rebuild renderer after filter change ────────────────────────
  function rebuildRenderer() {
    if (!fetchedData || !container) return;
    if (renderer) { renderer.kill(); renderer = null; }
    graph = buildGraph(fetchedData);
    renderer = new Sigma(graph, container, {
      renderEdgeLabels: false,
      defaultNodeType: 'circle',
      defaultEdgeType: 'line',
      minCameraRatio: 0.01,
      maxCameraRatio: 50,
      labelRenderedSizeThreshold: 6,
      labelColor: { color: '#ccc' },
    });
  }

  // reactive rebuilds when filters change (only in graph mode and after initial load)
  let filtersInitialized = false;
  $: if (fetchedData && !loading && viewMode === 'graph' && filtersInitialized) {
    rebuildRenderer();
  }

  // when switching back to citation graph, rebuild sigma (container was hidden)
  let prevViewMode: 'graph' | 'relation' = 'graph';
  $: if (viewMode !== prevViewMode) {
    prevViewMode = viewMode;
    if (viewMode === 'graph' && fetchedData && !loading) {
      // defer to next tick so the container is visible again
      setTimeout(() => rebuildRenderer(), 0);
    }
  }

  // ─── lifecycle ────────────────────────────────────────────────────
  onMount(() => {
    fetchNeighbourhood()
      .then(data => {
        fetchedData = data;
        dispatch('neighbourhoodLoaded', {
          citationCount:  [...new Set(data.citedIds)].length,
          referenceCount: [...new Set(data.referencedIds)].length,
        });
        if (!container) return;
        graph = buildGraph(data);
        renderer = new Sigma(graph, container, {
          renderEdgeLabels: false,
          defaultNodeType: 'circle',
          defaultEdgeType: 'line',
          minCameraRatio: 0.01,
          maxCameraRatio: 50,
          labelRenderedSizeThreshold: 6,
          labelColor: { color: '#ccc' },
        });
        loading = false;
        filtersInitialized = true;
      })
      .catch(err => {
        errorMsg = err instanceof Error ? err.message : String(err);
        loading = false;
        filtersInitialized = true;
      });
  });

  onDestroy(() => {
    if (renderer) { renderer.kill(); renderer = null; }
  });

  $: abstractSnippet = paper.abstract
    ? (paper.abstract.length > 300 ? paper.abstract.slice(0, 300) + '…' : paper.abstract)
    : 'No abstract available.';
</script>

<div class="detail-wrapper">

  <!-- ── top controls bar ── -->
  <div class="top-bar">
    <button class="back-btn" on:click={() => dispatch('back')}>← Back</button>

    <div class="view-tabs">
      <button class="tab-btn" class:active={viewMode === 'graph'}    on:click={() => (viewMode = 'graph')}>
        Citation Graph
      </button>
      <button class="tab-btn" class:active={viewMode === 'relation'} on:click={() => (viewMode = 'relation')}>
        Relation View
      </button>
    </div>


  </div>

  <!-- ── main view area ── -->

  <!-- Graph view elements: always in DOM so sigma container is preserved -->
  <div class="legend" style="display:{viewMode === 'graph' ? 'flex' : 'none'}">
    <span class="legend-item legend-static">
      <span class="dot" style="background:{COLOR_CENTER}"></span> Selected
    </span>
    <button class="legend-item legend-toggle" class:muted={!showCitations}
      on:click={() => { showCitations = !showCitations; }}
      title="Click to show/hide citations">
      <span class="dot" style="background:{COLOR_CITATION};opacity:{showCitations ? 1 : 0.3}"></span>
      Cites
    </button>
    <button class="legend-item legend-toggle" class:muted={!showReferences}
      on:click={() => { showReferences = !showReferences; }}
      title="Click to show/hide cited-by">
      <span class="dot" style="background:{COLOR_REFERENCE};opacity:{showReferences ? 1 : 0.3}"></span>
      Cited by
    </button>
    <button class="legend-item legend-toggle" class:muted={!showNonArxiv}
      on:click={() => { showNonArxiv = !showNonArxiv; }}
      title="Click to show/hide non-arXiv nodes">
      <span class="dot" style="background:{COLOR_DUMMY};opacity:{showNonArxiv ? 1 : 0.3}"></span>
      Non-arXiv
    </button>
  </div>

  {#if viewMode === 'graph'}
    {#if loading}
      <div class="overlay"><div class="spinner"></div><p>Loading citation network…</p></div>
    {:else if errorMsg}
      <div class="overlay error"><p>{errorMsg}</p></div>
    {/if}
  {/if}

  <!-- sigma container: always rendered so Sigma keeps its WebGL context -->
  <div class="sigma-container" style="display:{viewMode === 'graph' ? 'block' : 'none'}" bind:this={container}></div>

  {#if viewMode === 'relation'}
    <div class="relation-placeholder">
      <h3>Relation View</h3>
      <p>This view will display the selected paper alongside 100 semantically related papers based on embedding similarity.</p>
      <p class="placeholder-hint">Coming soon.</p>
    </div>
  {/if}

</div>

<style>
  .detail-wrapper {
    width: 100%;
    height: 100%;
    position: relative;
    background: var(--bg-primary, #0F1020);
    display: flex;
    flex-direction: column;
  }

  /* ── top bar ── */
  .top-bar {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 12px;
    border-bottom: 1px solid var(--glass-border, rgba(255,255,255,0.08));
    background: var(--bg-secondary, #141530);
    flex-shrink: 0;
    flex-wrap: wrap;
  }

  .back-btn {
    background: var(--glass-bg, rgba(20, 22, 50, 0.55));
    border: 1px solid var(--border-subtle, rgba(147,51,234,0.18));
    color: var(--text-primary, #f0f0f8);
    border-radius: var(--radius-sm, 8px);
    padding: 5px 14px;
    cursor: pointer;
    font-size: 13px;
    transition: all var(--transition-smooth, 0.3s ease);
  }
  .back-btn:hover {
    background: rgba(147, 51, 234, 0.2);
    border-color: rgba(147, 51, 234, 0.4);
  }

  .view-tabs {
    display: flex;
    gap: 2px;
    background: rgba(0,0,0,0.3);
    border-radius: var(--radius-sm, 8px);
    padding: 3px;
    border: 1px solid var(--glass-border, rgba(255,255,255,0.08));
  }

  .tab-btn {
    background: none;
    border: none;
    color: var(--text-muted, #6b6b8d);
    border-radius: 6px;
    padding: 5px 14px;
    cursor: pointer;
    font-size: 12px;
    font-weight: 500;
    transition: all var(--transition-fast, 0.15s ease);
  }
  .tab-btn.active {
    background: linear-gradient(135deg, rgba(147,51,234,0.35), rgba(232,57,160,0.25));
    color: var(--text-primary, #f0f0f8);
    box-shadow: 0 0 12px rgba(147,51,234,0.2);
  }
  .tab-btn:hover:not(.active) {
    background: rgba(255,255,255,0.05);
    color: var(--text-secondary, #a8a8c8);
  }

  .top-actions { display: none; }

  .sigma-container {
    flex: 1;
    width: 100%;
  }

  .legend {
    position: absolute;
    bottom: 14px;
    left: 14px;
    z-index: 15;
    background: var(--glass-bg, rgba(20, 22, 50, 0.55));
    border: 1px solid var(--glass-border, rgba(255,255,255,0.08));
    border-radius: var(--radius-sm, 8px);
    padding: 8px 14px;
    display: flex;
    gap: 14px;
    font-size: 12px;
    color: var(--text-secondary, #a8a8c8);
    pointer-events: auto;
    backdrop-filter: blur(var(--glass-blur, 16px));
  }
  .legend-item { display: flex; align-items: center; gap: 5px; }
  .legend-static { cursor: default; user-select: none; }
  .legend-toggle {
    background: none;
    border: none;
    color: var(--text-secondary, #a8a8c8);
    cursor: pointer;
    font-size: 12px;
    padding: 0;
    display: flex;
    align-items: center;
    gap: 5px;
    transition: color 0.15s ease;
    border-radius: 4px;
  }
  .legend-toggle:hover { color: var(--text-primary, #f0f0f8); }
  .legend-toggle.muted  { color: var(--text-muted, #6b6b8d); }
  .dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    display: inline-block;
    box-shadow: 0 0 5px currentColor;
    flex-shrink: 0;
  }

  .overlay {
    position: absolute;
    inset: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    z-index: 25;
    background: rgba(15, 16, 32, 0.7);
    color: var(--text-primary, #f0f0f8);
    font-size: 16px;
    backdrop-filter: blur(4px);
    gap: 12px;
  }
  .overlay.error { color: #f56565; }
  .spinner {
    width: 28px;
    height: 28px;
    border: 3px solid rgba(147, 51, 234, 0.2);
    border-top-color: var(--accent-cyan, #22d3ee);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }

  .relation-placeholder {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 12px;
    color: var(--text-secondary, #a8a8c8);
    text-align: center;
    padding: 2rem;
  }
  .placeholder-icon { font-size: 48px; }
  .relation-placeholder h3 {
    margin: 0;
    font-size: 20px;
    color: var(--text-primary, #f0f0f8);
  }
  .relation-placeholder p {
    margin: 0;
    max-width: 440px;
    font-size: 14px;
    line-height: 1.5;
  }
  .placeholder-hint {
    color: var(--text-muted, #6b6b8d) !important;
    font-size: 12px !important;
    margin-top: 4px !important;
  }
</style>
