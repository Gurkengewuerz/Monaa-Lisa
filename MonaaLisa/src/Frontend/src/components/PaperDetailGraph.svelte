<!--
  PaperDetailGraph.svelte
  Sigma.js network view for a single paper + its citations & references.
  Center paper is highlighted; connected papers are fetched on mount.
  Non-arXiv links are shown as grey dummy nodes.
-->
<script lang="ts">
  import { createEventDispatcher, onMount } from 'svelte';
  import GraphLib from 'graphology';
  import Sigma from 'sigma';
  import type { Paper } from '$lib/types/paper';

  /** The paper whose neighbourhood we are visualising. */
  export let paper: Paper;
  /** NestJS backend base URL. */
  export let apiBaseUrl: string = 'http://localhost:3000';

  let container: HTMLDivElement | null = null;
  let renderer: Sigma | null = null;
  let graph: GraphLib | null = null;
  let loading = true;
  let errorMsg: string | null = null;

  const dispatch = createEventDispatcher();

  // ─── colours ──────────────────────────────────────────────────────
  const COLOR_CENTER   = '#00ff88';
  const COLOR_CITATION = '#ff6b6b';
  const COLOR_REFERENCE = '#4ecdc4';
  const COLOR_DUMMY    = '#555555';

  // ─── data fetching ────────────────────────────────────────────────
  interface CitationRow { belonging_paper_entry_id: string; cited_paper_entry_id: string }
  interface ReferenceRow { belonging_paper_entry_id: string; referenced_paper_entry_id: string }

  async function fetchNeighbourhood() {
    const [citRes, refRes] = await Promise.all([
      fetch(`${apiBaseUrl}/paper-citations/paper/${encodeURIComponent(paper.entry_id)}`),
      fetch(`${apiBaseUrl}/paper-references/paper/${encodeURIComponent(paper.entry_id)}`),
    ]);

    const citations: CitationRow[] = citRes.ok ? await citRes.json() : [];
    const references: ReferenceRow[] = refRes.ok ? await refRes.json() : [];

    const citedIds = citations.map(c => c.cited_paper_entry_id);
    const referencedIds = references.map(r => r.referenced_paper_entry_id);
    const allIds = [...new Set([...citedIds, ...referencedIds])];

    // Batch-fetch real paper data for connected nodes
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

  // ─── graph building ───────────────────────────────────────────────
  function buildGraph(data: Awaited<ReturnType<typeof fetchNeighbourhood>>) {
    const g = new GraphLib();

    // Center node
    g.addNode(paper.entry_id, {
      x: 0, y: 0, size: 14,
      label: paper.title,
      color: COLOR_CENTER,
    });

    const CITATION_LIMIT = 150;
    const REFERENCE_LIMIT = 150;

    // Citations – inner ring
    const citIds = [...new Set(data.citedIds)].slice(0, CITATION_LIMIT);
    const citAngleStep = citIds.length > 0 ? (Math.PI * 2) / citIds.length : 0;
    citIds.forEach((id, i) => {
      const angle = i * citAngleStep - Math.PI / 2;
      const r = 12;
      const real = data.realPapers[id];
      const label = real ? truncate(real.title, 50) : id.slice(0, 20);
      const color = real ? COLOR_CITATION : COLOR_DUMMY;
      const size = real ? 5 : 3;

      if (!g.hasNode(id)) {
        g.addNode(id, { x: r * Math.cos(angle), y: r * Math.sin(angle), size, label, color });
      }
      g.addEdge(paper.entry_id, id, { color: 'rgba(255,107,107,0.35)', size: 0.6, type: 'arrow' });
    });

    // References – outer ring
    const refIds = [...new Set(data.referencedIds)].filter(id => !citIds.includes(id)).slice(0, REFERENCE_LIMIT);
    const refAngleStep = refIds.length > 0 ? (Math.PI * 2) / refIds.length : 0;
    refIds.forEach((id, i) => {
      const angle = i * refAngleStep - Math.PI / 2;
      const r = 25;
      const real = data.realPapers[id];
      const label = real ? truncate(real.title, 50) : id.slice(0, 20);
      const color = real ? COLOR_REFERENCE : COLOR_DUMMY;
      const size = real ? 4.5 : 2.5;

      if (!g.hasNode(id)) {
        g.addNode(id, { x: r * Math.cos(angle), y: r * Math.sin(angle), size, label, color });
      }
      g.addEdge(id, paper.entry_id, { color: 'rgba(78,205,196,0.30)', size: 0.5, type: 'arrow' });
    });

    // Add dummy nodes for non-arXiv counts
    const dummyCitCount = Math.min(paper.non_arxiv_citation_count ?? 0, 60);
    const dummyRefCount = Math.min(paper.non_arxiv_reference_count ?? 0, 60);
    const dummyCitStep = dummyCitCount > 0 ? (Math.PI * 2) / dummyCitCount : 0;
    const dummyRefStep = dummyRefCount > 0 ? (Math.PI * 2) / dummyRefCount : 0;

    for (let i = 0; i < dummyCitCount; i++) {
      const angle = i * dummyCitStep;
      const id = `__dummy_cit_${i}`;
      g.addNode(id, {
        x: 18 * Math.cos(angle),
        y: 18 * Math.sin(angle),
        size: 1.5, label: '', color: COLOR_DUMMY,
      });
      g.addEdge(paper.entry_id, id, { color: 'rgba(85,85,85,0.15)', size: 0.3 });
    }

    for (let i = 0; i < dummyRefCount; i++) {
      const angle = i * dummyRefStep + 0.1;
      const id = `__dummy_ref_${i}`;
      g.addNode(id, {
        x: 35 * Math.cos(angle),
        y: 35 * Math.sin(angle),
        size: 1.5, label: '', color: COLOR_DUMMY,
      });
      g.addEdge(id, paper.entry_id, { color: 'rgba(85,85,85,0.12)', size: 0.3 });
    }

    return g;
  }

  function truncate(s: string, n: number): string {
    return s.length > n ? s.slice(0, n) + '…' : s;
  }

  // ─── lifecycle ────────────────────────────────────────────────────
  onMount(() => {
    fetchNeighbourhood()
      .then(data => {
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
      })
      .catch(err => {
        errorMsg = err instanceof Error ? err.message : String(err);
        loading = false;
      });

    return () => {
      if (renderer) { renderer.kill(); renderer = null; }
    };
  });
</script>

<div class="detail-wrapper">
  <!-- back button -->
  <button class="back-btn" on:click={() => dispatch('back')}>
    ← Back
  </button>

  <!-- paper info banner -->
  <div class="info-banner">
    <h3>{paper.title}</h3>
    <p class="meta">{paper.authors}</p>
    <p class="meta">
      {paper.published ? new Date(paper.published).toLocaleDateString() : ''}
      &nbsp;|&nbsp; {paper.categories ?? ''}
    </p>
    <p class="stats">
      arXiv citations: {paper.citations.length}
      &nbsp;·&nbsp; non-arXiv citations: {paper.non_arxiv_citation_count}
      &nbsp;·&nbsp; non-arXiv references: {paper.non_arxiv_reference_count}
    </p>
  </div>

  <!-- legend -->
  <div class="legend">
    <span class="legend-item"><span class="dot" style="background:{COLOR_CENTER}"></span> Selected</span>
    <span class="legend-item"><span class="dot" style="background:{COLOR_CITATION}"></span> Cites</span>
    <span class="legend-item"><span class="dot" style="background:{COLOR_REFERENCE}"></span> Referenced by</span>
    <span class="legend-item"><span class="dot" style="background:{COLOR_DUMMY}"></span> Non-arXiv / unknown</span>
  </div>

  {#if loading}
    <div class="overlay"><p>Loading citation network…</p></div>
  {:else if errorMsg}
    <div class="overlay error"><p>{errorMsg}</p></div>
  {/if}

  <div class="sigma-container" bind:this={container}></div>
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

  .back-btn {
    position: absolute;
    top: 12px;
    left: 12px;
    z-index: 20;
    background: var(--glass-bg, rgba(20, 22, 50, 0.55));
    border: 1px solid var(--border-subtle, rgba(147,51,234,0.18));
    color: var(--text-primary, #f0f0f8);
    border-radius: var(--radius-sm, 8px);
    padding: 8px 16px;
    cursor: pointer;
    font-size: 13px;
    backdrop-filter: blur(var(--glass-blur, 16px));
    transition: all var(--transition-smooth, 0.3s cubic-bezier(0.4,0,0.2,1));
    box-shadow: 0 0 10px rgba(147, 51, 234, 0.1);
  }
  .back-btn:hover {
    background: rgba(147, 51, 234, 0.2);
    border-color: rgba(147, 51, 234, 0.4);
    box-shadow: 0 0 20px rgba(147, 51, 234, 0.25);
  }

  .info-banner {
    position: absolute;
    top: 12px;
    left: 50%;
    transform: translateX(-50%);
    z-index: 15;
    background: var(--glass-bg, rgba(20, 22, 50, 0.55));
    border: 1px solid var(--border-subtle, rgba(147,51,234,0.18));
    border-radius: var(--radius-md, 12px);
    padding: 10px 20px;
    max-width: 600px;
    text-align: center;
    backdrop-filter: blur(var(--glass-blur, 16px));
    pointer-events: none;
    box-shadow: var(--shadow-glow-sm);
  }
  .info-banner h3 {
    margin: 0 0 4px;
    font-size: 15px;
    color: var(--text-primary, #f0f0f8);
    line-height: 1.3;
    font-weight: 600;
  }
  .info-banner .meta {
    margin: 2px 0;
    font-size: 12px;
    color: var(--text-muted, #6b6b8d);
  }
  .info-banner .stats {
    margin: 6px 0 0;
    font-size: 11px;
    color: var(--accent-cyan, #22d3ee);
    opacity: 0.7;
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
    pointer-events: none;
    backdrop-filter: blur(var(--glass-blur, 16px));
  }
  .legend-item { display: flex; align-items: center; gap: 5px; }
  .dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    display: inline-block;
    box-shadow: 0 0 6px currentColor;
  }

  .sigma-container {
    flex: 1;
    width: 100%;
  }

  .overlay {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 25;
    background: rgba(15, 16, 32, 0.7);
    color: var(--text-primary, #f0f0f8);
    font-size: 16px;
    backdrop-filter: blur(4px);
  }
  .overlay.error { color: #f56565; }
</style>
