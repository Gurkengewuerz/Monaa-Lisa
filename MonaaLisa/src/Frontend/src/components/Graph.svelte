<!--
  Graph.svelte
  Sigma.js graph for displaying papers within a single subcategory.
  Papers are laid out in a phyllotaxis spiral (no tSNE needed).
  Clicking a node dispatches 'paperSelected' with the Paper object.
-->
<script lang="ts">
  import { createEventDispatcher, onMount } from 'svelte';
  import GraphLib from 'graphology';
  import Sigma from 'sigma';
  import type { Paper } from '$lib/types/paper';

  export let papers: Paper[] = [];
  export let selectedPaperId: string | null = null;
  export let categoryColor: string = '#4a9eff';

  let container: HTMLDivElement | null = null;
  let renderer: Sigma | null = null;
  let graph: GraphLib | null = null;
  let paperCache = new Map<string, Paper>();
  let hoverTimeout: number | null = null;
  let hoveredPaper: Paper | null = null;
  let selectedNode: string | null = null;

  const dispatch = createEventDispatcher();
  const GOLDEN_ANGLE = Math.PI * (3 - Math.sqrt(5));

  // ─── in-degree for node sizing ────────────────────────────────────
  function computeInDegree(ps: Paper[]): Map<string, number> {
    const deg = new Map<string, number>();
    const ids = new Set(ps.map(p => p.entry_id));
    ps.forEach(p => deg.set(p.entry_id, 0));
    ps.forEach(p => {
      p.citations.forEach(cid => {
        if (ids.has(cid)) deg.set(cid, (deg.get(cid) || 0) + 1);
      });
    });
    return deg;
  }

  // ─── reactively select node when prop changes ─────────────────────
  $: if (selectedPaperId && selectedPaperId !== selectedNode && graph && renderer) {
    highlightNode(selectedPaperId);
  }

  function highlightNode(nodeId: string) {
    if (!graph || !renderer || !graph.hasNode(nodeId)) return;
    graph.forEachNode(n => {
      graph!.setNodeAttribute(n, 'color', 'rgba(255,255,255,0.08)');
    });
    graph.edges().forEach(e => graph!.dropEdge(e));

    graph.setNodeAttribute(nodeId, 'color', '#00ff88');
    const paper = paperCache.get(nodeId);
    if (paper) {
      paper.citations.forEach(cid => {
        if (graph!.hasNode(cid)) {
          graph!.setNodeAttribute(cid, 'color', '#ffcc00');
          graph!.addEdge(nodeId, cid, { color: 'rgba(255,255,255,0.3)', size: 0.8 });
        }
      });
    }
    selectedNode = nodeId;
    renderer.refresh();
  }

  onMount(() => {
    if (!container) return;
    graph = new GraphLib();
    const deg = computeInDegree(papers);
    let maxDeg = 0;
    deg.forEach(v => { if (v > maxDeg) maxDeg = v; });

    papers.forEach((paper, i) => {
      const r = 6 * Math.sqrt(i + 1);
      const theta = i * GOLDEN_ANGLE;
      const x = r * Math.cos(theta);
      const y = r * Math.sin(theta);

      const d = deg.get(paper.entry_id) || 0;
      const size = 2 + (maxDeg > 0 ? (d / maxDeg) * 6 : 0);
      const alpha = 0.4 + (maxDeg > 0 ? (d / maxDeg) * 0.6 : 0.3);
      const rgb = hexToRgb(categoryColor);
      const color = `rgba(${rgb[0]},${rgb[1]},${rgb[2]},${alpha})`;

      graph!.addNode(paper.entry_id, {
        x, y, size, label: paper.title, color, originalColor: color,
      });
      paperCache.set(paper.entry_id, paper);
    });

    renderer = new Sigma(graph, container, {
      renderEdgeLabels: false,
      defaultNodeType: 'circle',
      defaultEdgeType: 'line',
      minCameraRatio: 0.01,
      maxCameraRatio: 50,
      renderLabels: false,
      labelRenderedSizeThreshold: 8,
    });

    renderer.on('enterNode', ({ node }) => {
      if (hoverTimeout) clearTimeout(hoverTimeout);
      hoverTimeout = setTimeout(() => {
        hoveredPaper = paperCache.get(node) || null;
      }, 150) as unknown as number;
    });
    renderer.on('leaveNode', () => {
      if (hoverTimeout) clearTimeout(hoverTimeout);
      hoveredPaper = null;
    });

    renderer.on('clickNode', ({ node }) => {
      const paper = paperCache.get(node);
      if (paper) dispatch('paperSelected', paper);
    });

    renderer.on('clickStage', () => {
      selectedNode = null;
      hoveredPaper = null;
      if (graph) {
        graph.forEachNode(n => {
          graph!.setNodeAttribute(n, 'color', graph!.getNodeAttribute(n, 'originalColor'));
        });
        graph.edges().forEach(e => graph!.dropEdge(e));
      }
      renderer!.refresh();
      dispatch('nodeDeselected');
    });

    return () => {
      if (hoverTimeout) clearTimeout(hoverTimeout);
      if (renderer) { renderer.kill(); renderer = null; }
      paperCache.clear();
    };
  });

  function hexToRgb(hex: string): [number, number, number] {
    const m = hex.match(/^#?([\da-f]{2})([\da-f]{2})([\da-f]{2})$/i);
    if (!m) return [74, 158, 255];
    return [parseInt(m[1], 16), parseInt(m[2], 16), parseInt(m[3], 16)];
  }
</script>

<div class="graph-wrapper">
  <div class="sigma-container" bind:this={container}></div>

  {#if hoveredPaper}
    <div class="tooltip">
      <h4>{hoveredPaper.title}</h4>
      <p class="meta">{hoveredPaper.authors}</p>
      <p class="meta">{hoveredPaper.published ? new Date(hoveredPaper.published).toLocaleDateString() : ''}</p>
      <p class="abstract">{hoveredPaper.abstract.slice(0, 200)}{hoveredPaper.abstract.length > 200 ? '…' : ''}</p>
      <p class="stats">Citations: {hoveredPaper.citations.length} | Non-arXiv: {hoveredPaper.non_arxiv_citation_count}</p>
    </div>
  {/if}
</div>

<style>
  .graph-wrapper {
    width: 100%;
    height: 100%;
    position: relative;
    background: var(--bg-primary, #0F1020);
  }
  .sigma-container {
    width: 100%;
    height: 100%;
  }
  .tooltip {
    position: absolute;
    top: 12px;
    right: 12px;
    max-width: 340px;
    background: var(--glass-bg, rgba(20, 22, 50, 0.55));
    border: 1px solid var(--border-subtle, rgba(147,51,234,0.18));
    border-radius: var(--radius-md, 12px);
    padding: 14px 16px;
    color: var(--text-primary, #f0f0f8);
    font-size: 13px;
    z-index: 10;
    pointer-events: none;
    backdrop-filter: blur(var(--glass-blur, 16px));
    box-shadow: var(--shadow-glow-sm);
  }
  .tooltip h4 {
    margin: 0 0 6px;
    font-size: 14px;
    color: var(--text-primary, #f0f0f8);
    line-height: 1.3;
    font-weight: 600;
  }
  .tooltip .meta {
    margin: 2px 0;
    color: var(--text-muted, #6b6b8d);
    font-size: 12px;
  }
  .tooltip .abstract {
    margin: 8px 0 4px;
    line-height: 1.4;
    color: var(--text-secondary, #a8a8c8);
  }
  .tooltip .stats {
    margin: 6px 0 0;
    color: var(--accent-cyan, #22d3ee);
    font-size: 11px;
    opacity: 0.8;
  }
</style>
