<!--
  Graph.svelte
  Written by Nick

  Renders a Sigma.js force-graph of papers in a single arXiv subcategory.
  Each node = one paper. Node size ≈ citation count. Colour comes from the category.

  The `authorHighlight` prop (string) lets GraphLayout tell this component to
  highlight all nodes whose authors contain that name — and add any missing ones
  by fetching from the API.
-->
<script lang="ts">
    import { createEventDispatcher, onMount } from "svelte";
    import GraphLib from "graphology";
    import Sigma from "sigma";
    import type { Paper } from "$lib/types/paper";

    export let papers: Paper[] = [];
    export let selectedPaperId: string | null = null;
    export let categoryColor: string = "#4a9eff";
    /** Author name to highlight in the graph. Empty string = no highlight. */
    export let authorHighlight: string = "";
    /** API base URL for fetching papers by author */
    export let apiBaseUrl: string = "http://localhost:3000";
    /** Current category ID for scoping author search */
    export let categoryId: string = "";
    /**
     * Full paper objects returned by the sidebar search.
     * When non-empty these take priority over authorHighlight:
     * matching nodes are highlighted with the category colour and
     * up to MAX_SEARCH_ADD missing papers are injected into the graph.
     */
    export let searchHighlightPapers: Paper[] = [];

    let container: HTMLDivElement | null = null;
    let renderer: Sigma | null = null;
    let graph: GraphLib | null = null;
    let paperCache = new Map<string, Paper>();
    let hoverTimeout: number | null = null;
    let hoveredPaper: Paper | null = null;
    let selectedNode: string | null = null;
    /** Track nodes added via author highlight so they can be removed on clear. */
    let authorAddedNodes: Set<string> = new Set();
    /** Track nodes added via search highlight so they can be removed on clear. */
    let searchAddedNodes: Set<string> = new Set();
    /** Maximum extra nodes that a search-highlight may inject into the graph.
     *  Prevents a broad search from flooding the view with thousands of nodes. */
    const MAX_SEARCH_ADD = 100;
    /** Stored globally so added nodes can be sized consistently with existing ones. */
    let maxCit = 0;

    const dispatch = createEventDispatcher();

    // ─── total citation count for node sizing ─────────────────────────
    function totalCitations(p: Paper): number {
        return (
            (p.citations?.length ?? 0) +
            (p.references?.length ?? 0) +
            (p.non_arxiv_citation_count ?? 0) +
            (p.non_arxiv_reference_count ?? 0)
        );
    }

    // ─── spread algorithm: push apart overlapping nodes ───────────────
    // ┌─ Overlap tuning knobs ─────────────────────────────────────────
    // │  MIN_DIST      – minimum pixel gap between any two node edges.
    // │                  Increase to spread nodes further apart.
    // │  MAX_DIST      – hard cap on how far a node may drift from the
    // │                  centroid (prevents nodes flying off-screen).
    // │  SPREAD_ITERS  – number of repulsion-relaxation passes; more =
    // │                  better separation but slower initial load.
    // │  REPEL_STRENGTH– [0-1] fraction of overlap moved per iteration.
    // └────────────────────────────────────────────────────────────────
    const MIN_DIST = 20; // minimum distance between any two nodes
    const MAX_DIST = 500; // maximum distance from centroid
    const SPREAD_ITERS = 20; //60;
    const REPEL_STRENGTH = 0.5;

    function applySpread(g: GraphLib) {
        const nodes = g.nodes();
        if (nodes.length < 2) return;

        for (let iter = 0; iter < SPREAD_ITERS; iter++) {
            // Compute centroid
            let cx = 0,
                cy = 0;
            nodes.forEach((n) => {
                cx += g.getNodeAttribute(n, "x");
                cy += g.getNodeAttribute(n, "y");
            });
            cx /= nodes.length;
            cy /= nodes.length;

            // Repel nodes that are too close (accounting for node sizes)
            for (let i = 0; i < nodes.length; i++) {
                let xi = g.getNodeAttribute(nodes[i], "x");
                let yi = g.getNodeAttribute(nodes[i], "y");
                const si = g.getNodeAttribute(nodes[i], "size") || 2;
                for (let j = i + 1; j < nodes.length; j++) {
                    let xj = g.getNodeAttribute(nodes[j], "x");
                    let yj = g.getNodeAttribute(nodes[j], "y");
                    const sj = g.getNodeAttribute(nodes[j], "size") || 2;
                    const dx = xj - xi;
                    const dy = yj - yi;
                    const dist = Math.sqrt(dx * dx + dy * dy) || 0.01;
                    // Dynamic min distance based on combined node radii
                    const minD = MIN_DIST + (si + sj) * 0.15;
                    if (dist < minD) {
                        const push = ((minD - dist) / 2) * REPEL_STRENGTH;
                        const ux = (dx / dist) * push;
                        const uy = (dy / dist) * push;
                        g.setNodeAttribute(nodes[i], "x", xi - ux);
                        g.setNodeAttribute(nodes[i], "y", yi - uy);
                        g.setNodeAttribute(nodes[j], "x", xj + ux);
                        g.setNodeAttribute(nodes[j], "y", yj + uy);
                    }
                }
            }

            // Clamp nodes that drifted beyond MAX_DIST from centroid
            nodes.forEach((n) => {
                let x = g.getNodeAttribute(n, "x");
                let y = g.getNodeAttribute(n, "y");
                const dx = x - cx;
                const dy = y - cy;
                const d = Math.sqrt(dx * dx + dy * dy);
                if (d > MAX_DIST) {
                    g.setNodeAttribute(n, "x", cx + (dx / d) * MAX_DIST);
                    g.setNodeAttribute(n, "y", cy + (dy / d) * MAX_DIST);
                }
            });
        }
    }

    // ─── reactively handle highlight changes ─────────────────────────
    // One reactive entry-point that decides which mode applies:
    //   1. searchHighlightPapers is non-empty  → search-result highlights (all params)
    //   2. authorHighlight string is set        → author-only highlights (legacy path)
    //   3. both empty                           → restore default node colours
    $: applyGraphHighlights(searchHighlightPapers, authorHighlight);

    function applyGraphHighlights(searchPapers: Paper[], authorQ: string) {
        if (searchPapers.length > 0) {
            applySearchHighlight(searchPapers);
        } else if (authorQ) {
            handleAuthorHighlight(authorQ);
        } else {
            restoreAllNodeColors();
        }
    }

    /** Restore all nodes to their original colours and remove any injected nodes. */
    function restoreAllNodeColors() {
        if (!graph || !renderer) return;
        // Remove author-added nodes
        for (const nid of authorAddedNodes) {
            if (graph.hasNode(nid)) {
                graph.edges(nid).forEach(e => graph!.dropEdge(e));
                graph.dropNode(nid);
            }
        }
        authorAddedNodes = new Set();
        // Remove search-added nodes
        for (const nid of searchAddedNodes) {
            if (graph.hasNode(nid)) {
                graph.edges(nid).forEach(e => graph!.dropEdge(e));
                graph.dropNode(nid);
            }
        }
        searchAddedNodes = new Set();
        // Restore original colours
        graph.forEachNode((n) => {
            graph!.setNodeAttribute(n, "color", graph!.getNodeAttribute(n, "originalColor"));
        });
        renderer.refresh();
    }

    /**
     * Highlight search results in the graph.
     * - Nodes matching a result entry_id get the category colour at full opacity.
     * - Non-matching nodes are dimmed.
     * - Papers missing from the graph are injected (up to MAX_SEARCH_ADD),
     *   sized using the same citation-count formula as regular nodes.
     */
    function applySearchHighlight(papers: Paper[]) {
        if (!graph || !renderer) return;

        // Remove previously injected search nodes before re-applying.
        for (const nid of searchAddedNodes) {
            if (graph.hasNode(nid)) {
                graph.edges(nid).forEach(e => graph!.dropEdge(e));
                graph.dropNode(nid);
            }
        }
        searchAddedNodes = new Set();
        // Also remove author-added nodes since search takes priority.
        for (const nid of authorAddedNodes) {
            if (graph.hasNode(nid)) {
                graph.edges(nid).forEach(e => graph!.dropEdge(e));
                graph.dropNode(nid);
            }
        }
        authorAddedNodes = new Set();

        const entryIds = new Set(papers.map(p => p.entry_id));
        const rgb = hexToRgb(categoryColor);
        // Full-opacity category colour for highlighted (found) nodes.
        const highlightColor = `rgba(${rgb[0]},${rgb[1]},${rgb[2]},1.0)`;

        // First pass: colour existing nodes.
        graph.forEachNode((n) => {
            if (entryIds.has(n)) {
                graph!.setNodeAttribute(n, "color", highlightColor);
            } else {
                graph!.setNodeAttribute(n, "color", "rgba(255,255,255,0.08)");
            }
        });

        // Second pass: inject missing papers (capped at MAX_SEARCH_ADD).
        let addedCount = 0;
        for (let i = 0; i < papers.length && addedCount < MAX_SEARCH_ADD; i++) {
            const p = papers[i];
            if (graph.hasNode(p.entry_id)) continue; // already shown

            // Size follows the same formula as regular nodes so proportions match.
            const cit = totalCitations(p);
            const size = 2 + (maxCit > 0 ? (cit / maxCit) * 8 : 2);

            // Prefer UMAP position; fall back to outward spiral around the graph.
            const hasUmap = p.tsne1 !== 0 || p.tsne2 !== 0;
            const spiralAngle = (papers.length + i) * Math.PI * (3 - Math.sqrt(5));
            const x = hasUmap
                ? p.tsne1
                : 6 * Math.sqrt(papers.length + i + 1) * Math.cos(spiralAngle);
            const y = hasUmap
                ? p.tsne2
                : 6 * Math.sqrt(papers.length + i + 1) * Math.sin(spiralAngle);

            graph.addNode(p.entry_id, {
                x, y,
                size,
                label: p.title,
                color: highlightColor,
                originalColor: highlightColor,
                zIndex: Math.ceil(size),
            });
            paperCache.set(p.entry_id, p);
            searchAddedNodes.add(p.entry_id);
            addedCount++;
        }

        renderer.refresh();
    }

    // Highlight existing graph nodes whose authors contain the search term;
    // then ALWAYS fetch from the API and add any matching papers not yet in the graph.
    async function handleAuthorHighlight(author: string) {
        if (!graph || !renderer) return;

        // Remove any nodes we previously added for author-highlight purposes
        for (const nid of authorAddedNodes) {
            if (graph.hasNode(nid)) {
                graph.edges(nid).forEach(e => graph!.dropEdge(e));
                graph.dropNode(nid);
            }
        }
        authorAddedNodes = new Set();

        if (!author) {
            // Empty author string = clear all highlights, restore original colors
            graph.forEachNode((n) => {
                graph!.setNodeAttribute(n, "color", graph!.getNodeAttribute(n, "originalColor"));
            });
            renderer.refresh();
            return;
        }

        const q = author.toLowerCase();
        // Resolve category colour to full-opacity rgba for highlighted nodes.
        const rgb = hexToRgb(categoryColor);
        const matchColor = `rgba(${rgb[0]},${rgb[1]},${rgb[2]},1.0)`;

        // First pass: highlight existing nodes or dim them
        graph.forEachNode((n) => {
            const p = paperCache.get(n);
            if (p && p.authors.toLowerCase().includes(q)) {
                // Category colour (full opacity) for matching nodes
                graph!.setNodeAttribute(n, "color", matchColor);
                graph!.setNodeAttribute(n, "size", Math.max(graph!.getNodeAttribute(n, "size"), 8));
            } else {
                // Dim non-matching nodes
                graph!.setNodeAttribute(n, "color", "rgba(255,255,255,0.08)");
            }
        });

        // Always fetch from the API to find ALL matching papers (not just the ones
        // already visible in the graph). We add every paper that isn't already a node.
        if (categoryId) {
            try {
                const params = new URLSearchParams();
                params.set("search", author);
                params.set("categories", categoryId);
                params.set("take", "50");  // fetch up to 50 matching papers
                params.set("skip", "0");
                const res = await fetch(`${apiBaseUrl}/papers?${params.toString()}`);
                if (res.ok) {
                    const payload = await res.json();
                    const items: any[] = Array.isArray(payload) ? payload : (payload?.items ?? []);
                    // Only keep papers whose author field actually matches the search term
                    const matching = items.filter((raw: any) => {
                        const authors = Array.isArray(raw.authors) ? raw.authors.join(", ") : (raw.authors ?? "");
                        return authors.toLowerCase().includes(q);
                    });
                    matching.forEach((raw: any, i: number) => {
                        if (graph!.hasNode(raw.entry_id)) {
                            // Already in the graph — make sure it's highlighted
                            graph!.setNodeAttribute(raw.entry_id, "color", matchColor);
                            graph!.setNodeAttribute(raw.entry_id, "size", 8);
                        } else {
                            // Not in the graph yet — add it at a computed position
                            const hasUmap = (raw.tsne1 || raw.tsne?.x);
                            const x = hasUmap
                                ? (raw.tsne?.x ?? raw.tsne1 ?? 0)
                                : 6 * Math.sqrt(papers.length + i + 1) * Math.cos((papers.length + i) * Math.PI * (3 - Math.sqrt(5)));
                            const y = hasUmap
                                ? (raw.tsne?.y ?? raw.tsne2 ?? 0)
                                : 6 * Math.sqrt(papers.length + i + 1) * Math.sin((papers.length + i) * Math.PI * (3 - Math.sqrt(5)));
                            const authors = Array.isArray(raw.authors) ? raw.authors.join(", ") : (raw.authors ?? "");
                            const newPaper: Paper = {
                                id: Number(raw.id ?? 0),
                                entry_id: raw.entry_id,
                                title: raw.title ?? raw.entry_id,
                                authors,
                                abstract: raw.abstract ?? "",
                                published: raw.published ?? null,
                                categories: raw.categories ?? null,
                                url: raw.url ?? null,
                                citations: Array.isArray(raw.citations) ? raw.citations : [],
                                references: [],
                                non_arxiv_citation_count: Number(raw.non_arxiv_citation_count ?? 0),
                                non_arxiv_reference_count: Number(raw.non_arxiv_reference_count ?? 0),
                                tsne1: x,
                                tsne2: y,
                                cluster: raw.categories ?? "U",
                            };
                            graph!.addNode(raw.entry_id, {
                                x, y,
                                // Size proportional to citations, same formula as regular nodes.
                                size: 2 + (maxCit > 0 ? totalCitations(newPaper) / maxCit * 8 : 2),
                                label: raw.title ?? raw.entry_id,
                                color: matchColor,
                                originalColor: matchColor,
                                zIndex: 10,
                            });
                            paperCache.set(raw.entry_id, newPaper);
                            authorAddedNodes.add(raw.entry_id);
                        }
                    });
                }
            } catch { /* ignore network errors silently */ }
        }

        renderer.refresh();
    }

    // ─── reactively select node when prop changes ─────────────────────
    $: if (
        selectedPaperId &&
        selectedPaperId !== selectedNode &&
        graph &&
        renderer
    ) {
        highlightNode(selectedPaperId);
    }

    function highlightNode(nodeId: string) {
        if (!graph || !renderer || !graph.hasNode(nodeId)) return;
        graph.forEachNode((n) => {
            graph!.setNodeAttribute(n, "color", "rgba(255,255,255,0.08)");
        });
        graph.edges().forEach((e) => graph!.dropEdge(e));

        graph.setNodeAttribute(nodeId, "color", "#00ff88");
        const paper = paperCache.get(nodeId);
        if (paper) {
            paper.citations.forEach((cid) => {
                if (graph!.hasNode(cid)) {
                    graph!.setNodeAttribute(cid, "color", "#ffcc00");
                    graph!.addEdge(nodeId, cid, {
                        color: "rgba(255,255,255,0.3)",
                        size: 0.8,
                    });
                }
            });
        }
        selectedNode = nodeId;
        renderer.refresh();
    }

    onMount(() => {
        if (!container) return;
        graph = new GraphLib();

        // Compute max total citations for node sizing (stored at module level
        // so that nodes added later for highlights use the same scale).
        maxCit = 0;
        papers.forEach((p) => {
            const c = totalCitations(p);
            if (c > maxCit) maxCit = c;
        });

        papers.forEach((paper, i) => {
            // Use UMAP coordinates (tsne1/tsne2) when available, fallback to spiral
            const hasUmap = paper.tsne1 !== 0 || paper.tsne2 !== 0;
            const x = hasUmap
                ? paper.tsne1
                : 6 *
                  Math.sqrt(i + 1) *
                  Math.cos(i * Math.PI * (3 - Math.sqrt(5)));
            const y = hasUmap
                ? paper.tsne2
                : 6 *
                  Math.sqrt(i + 1) *
                  Math.sin(i * Math.PI * (3 - Math.sqrt(5)));

            const cit = totalCitations(paper);
            const size = 2 + (maxCit > 0 ? (cit / maxCit) * 8 : 0);
            const alpha = 0.4 + (maxCit > 0 ? (cit / maxCit) * 0.6 : 0.3);
            const rgb = hexToRgb(categoryColor);
            const color = `rgba(${rgb[0]},${rgb[1]},${rgb[2]},${alpha})`;

            graph!.addNode(paper.entry_id, {
                x,
                y,
                size,
                label: paper.title,
                color,
                originalColor: color,
                zIndex: Math.ceil(size),
            });
            paperCache.set(paper.entry_id, paper);
        });

        // Apply spread to prevent overlapping nodes
        applySpread(graph);

        renderer = new Sigma(graph, container, {
            renderEdgeLabels: false,
            defaultNodeType: "circle",
            defaultEdgeType: "line",
            minCameraRatio: 0.08,
            maxCameraRatio: 5,
            renderLabels: false,
            labelRenderedSizeThreshold: 8,
            zIndex: true,
        });

        renderer.on("enterNode", ({ node }) => {
            if (hoverTimeout) clearTimeout(hoverTimeout);
            hoverTimeout = setTimeout(() => {
                hoveredPaper = paperCache.get(node) || null;
            }, 150) as unknown as number;
        });
        renderer.on("leaveNode", () => {
            if (hoverTimeout) clearTimeout(hoverTimeout);
            hoveredPaper = null;
        });

        renderer.on("clickNode", ({ node }) => {
            const paper = paperCache.get(node);
            if (paper) dispatch("paperSelected", paper);
        });

        renderer.on("clickStage", () => {
            selectedNode = null;
            hoveredPaper = null;
            if (graph) {
                graph.forEachNode((n) => {
                    graph!.setNodeAttribute(
                        n,
                        "color",
                        graph!.getNodeAttribute(n, "originalColor"),
                    );
                });
                graph.edges().forEach((e) => graph!.dropEdge(e));
            }
            renderer!.refresh();
            dispatch("nodeDeselected");
        });

        return () => {
            if (hoverTimeout) clearTimeout(hoverTimeout);
            if (renderer) {
                renderer.kill();
                renderer = null;
            }
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
            <p class="meta">
                {hoveredPaper.published
                    ? new Date(hoveredPaper.published).toLocaleDateString()
                    : ""}
            </p>
            <p class="abstract">
                {hoveredPaper.abstract.slice(0, 200)}{hoveredPaper.abstract
                    .length > 200
                    ? "…"
                    : ""}
            </p>
            <p class="stats">
                Citations: {hoveredPaper.citations.length} | References: {hoveredPaper
                    .references.length} | Non-arXiv: {(hoveredPaper.non_arxiv_citation_count ??
                    0) + (hoveredPaper.non_arxiv_reference_count ?? 0)}
            </p>
        </div>
    {/if}
</div>

<style>
    .graph-wrapper {
        width: 100%;
        height: 100%;
        position: relative;
        background: var(--bg-primary, #0f1020);
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
        border: 1px solid var(--border-subtle, rgba(147, 51, 234, 0.18));
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
