<!--
  PaperDetailGraph.svelte
  Sigma.js network view for a single paper + its citations & references.
  Features:
    - Citation Graph view (sigma.js) with UMAP coordinates
    - Relation View with draggable paper cards (top-20 related papers)
    - Non-arXiv shown as single aggregate node with tooltip
    - Filter controls: show/hide citations, references, non-arXiv
-->
<script lang="ts">
    import { createEventDispatcher, onMount, onDestroy, tick } from "svelte";
    import GraphLib from "graphology";
    import Sigma from "sigma";
    import type { Paper } from "$lib/types/paper";
    import { getSubcategoryName } from "../utils/arxivTaxonomy";

    /** The paper whose neighbourhood we are visualising. */
    export let paper: Paper;
    /** NestJS backend base URL. */
    export let apiBaseUrl: string = "http://localhost:3000";
    /** Maximum total nodes (citations + references). 0 = unlimited. */
    export let nodeLimit: number = 5000;

    let container: HTMLDivElement | null = null;
    let renderer: Sigma | null = null;
    let graph: GraphLib | null = null;
    let loading = true;
    let errorMsg: string | null = null;

    // ─── view mode ────────────────────────────────────────────────────
    let viewMode: "graph" | "relation" = "graph";

    // ─── info view ────────────────────────────────────────────────────
    let abstractExpanded = false;

    function formatCategories(cats: string | null): string {
        if (!cats) return "";
        return cats
            .trim()
            .split(/[\s,]+/)
            .filter(Boolean)
            .map((c) => {
                const n = getSubcategoryName(c);
                return n !== c ? `${n} (${c})` : c;
            })
            .join(" · ");
    }

    // ─── filters ──────────────────────────────────────────────────────
    let showCitations = true;
    let showReferences = true;
    let showNonArxiv = true;

    function toggleFilter(filter: "citations" | "references" | "nonArxiv") {
        if (filter === "citations") showCitations = !showCitations;
        else if (filter === "references") showReferences = !showReferences;
        else if (filter === "nonArxiv") showNonArxiv = !showNonArxiv;
        if (
            filtersInitialized &&
            fetchedData &&
            !loading &&
            viewMode === "graph"
        ) {
            rebuildRenderer();
        }
    }

    const dispatch = createEventDispatcher<{
        back: void;
        neighbourhoodLoaded: { citationCount: number; referenceCount: number };
        navigate: Paper;
    }>();

    // ─── colours ──────────────────────────────────────────────────────
    const COLOR_CENTER = "#00ff88";
    const COLOR_CITATION = "#ff6b6b";
    const COLOR_REFERENCE = "#4ecdc4";
    const COLOR_DUMMY = "#555555";

    // ─── raw fetched data (cached for filter rebuilds) ────────────────
    interface CitationRow {
        belonging_paper_entry_id: string;
        cited_paper_entry_id: string;
    }
    interface ReferenceRow {
        belonging_paper_entry_id: string;
        referenced_paper_entry_id: string;
    }
    interface FetchedData {
        citations: CitationRow[];
        references: ReferenceRow[];
        citedIds: string[];
        referencedIds: string[];
        realPapers: Record<string, any>;
    }

    let fetchedData: FetchedData | null = null;

    // ─── tooltip state for non-arXiv aggregate node ───────────────────
    let hoveredPaper: any | null = null;
    let tooltipText: string | null = null;
    let tooltipPos = { x: 0, y: 0 };

    // ─── helper: parse tsne JSON field from API ───────────────────────
    function parseTsne(tsne: unknown): [number, number] {
        if (!tsne) return [0, 0];
        let obj: any = tsne;
        if (typeof obj === "string") {
            try {
                obj = JSON.parse(obj);
            } catch {
                return [0, 0];
            }
        }
        if (
            obj &&
            typeof obj === "object" &&
            typeof obj.x === "number" &&
            typeof obj.y === "number"
        ) {
            return [obj.x, obj.y];
        }
        return [0, 0];
    }

    // ─── data fetching ────────────────────────────────────────────────
    async function fetchNeighbourhood() {
        const [citRes, refRes] = await Promise.all([
            fetch(
                `${apiBaseUrl}/paper-citations/paper/${encodeURIComponent(paper.entry_id)}`,
            ),
            fetch(
                `${apiBaseUrl}/paper-references/paper/${encodeURIComponent(paper.entry_id)}`,
            ),
        ]);

        const citations: CitationRow[] = citRes.ok ? await citRes.json() : [];
        const references: ReferenceRow[] = refRes.ok ? await refRes.json() : [];

        const citedIds = citations.map((c) => c.cited_paper_entry_id);
        const referencedIds = references.map(
            (r) => r.referenced_paper_entry_id,
        );
        const allIds = [...new Set([...citedIds, ...referencedIds])];

        let realPapers: Record<string, any> = {};
        if (allIds.length > 0) {
            const batchSize = 500;
            const batches: string[][] = [];
            for (let i = 0; i < allIds.length; i += batchSize) {
                batches.push(allIds.slice(i, i + batchSize));
            }
            const results = await Promise.all(
                batches.map((ids) =>
                    fetch(`${apiBaseUrl}/papers/batch`, {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ entryIds: ids }),
                    }).then((r) => (r.ok ? r.json() : [])),
                ),
            );
            results.flat().forEach((p: any) => {
                realPapers[p.entry_id] = p;
            });
        }

        return { citations, references, citedIds, referencedIds, realPapers };
    }

    // ─── spread algorithm: push apart overlapping nodes ───────────────
    const MIN_DIST = 2.5;
    const MAX_DIST = 50000;
    const SPREAD_ITERS = 40;
    const REPEL_STRENGTH = 0.5;

    function applySpread(g: GraphLib) {
        const nodes = g.nodes();
        if (nodes.length < 2) return;
        const centerNode = paper.entry_id;

        for (let iter = 0; iter < SPREAD_ITERS; iter++) {
            // Compute centroid (excluding center which stays at 0,0)
            let cx = 0,
                cy = 0;
            nodes.forEach((n) => {
                cx += g.getNodeAttribute(n, "x");
                cy += g.getNodeAttribute(n, "y");
            });
            cx /= nodes.length;
            cy /= nodes.length;

            // Repel nodes that are too close
            for (let i = 0; i < nodes.length; i++) {
                let xi = g.getNodeAttribute(nodes[i], "x");
                let yi = g.getNodeAttribute(nodes[i], "y");
                for (let j = i + 1; j < nodes.length; j++) {
                    let xj = g.getNodeAttribute(nodes[j], "x");
                    let yj = g.getNodeAttribute(nodes[j], "y");
                    const dx = xj - xi;
                    const dy = yj - yi;
                    const dist = Math.sqrt(dx * dx + dy * dy) || 0.01;
                    if (dist < MIN_DIST) {
                        const push = ((MIN_DIST - dist) / 2) * REPEL_STRENGTH;
                        const ux = (dx / dist) * push;
                        const uy = (dy / dist) * push;
                        // Don't move the center node
                        if (nodes[i] !== centerNode) {
                            g.setNodeAttribute(nodes[i], "x", xi - ux);
                            g.setNodeAttribute(nodes[i], "y", yi - uy);
                        }
                        if (nodes[j] !== centerNode) {
                            g.setNodeAttribute(nodes[j], "x", xj + ux);
                            g.setNodeAttribute(nodes[j], "y", yj + uy);
                        }
                    }
                }
            }

            // Clamp nodes that drifted beyond MAX_DIST from centroid (skip center)
            nodes.forEach((n) => {
                if (n === centerNode) return;
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

    // ─── graph building (filter-aware, UMAP coords) ──────────────────
    function buildGraph(data: FetchedData) {
        const g = new GraphLib();

        // Center paper at origin
        g.addNode(paper.entry_id, {
            x: 0,
            y: 0,
            size: 14,
            label: paper.title,
            color: COLOR_CENTER,
            type: "circle",
        });

        const halfLimit = nodeLimit > 0 ? Math.floor(nodeLimit / 2) : Infinity;
        const CITATION_LIMIT = halfLimit;
        const REFERENCE_LIMIT = halfLimit;

        if (showCitations) {
            const citIds = [...new Set(data.citedIds)].slice(0, CITATION_LIMIT);
            citIds.forEach((id, i) => {
                const real = data.realPapers[id];
                const label = real ? truncate(real.title, 50) : id.slice(0, 20);
                const color = real ? COLOR_CITATION : COLOR_DUMMY;
                const size = real ? 5 : 3;

                // Use UMAP coords relative to center, fallback to circular layout
                let x: number, y: number;
                if (real) {
                    const [tx, ty] = parseTsne(real.tsne);
                    if (tx !== 0 || ty !== 0) {
                        x = tx - paper.tsne1;
                        y = ty - paper.tsne2;
                    } else {
                        const step =
                            citIds.length > 0
                                ? (Math.PI * 2) / citIds.length
                                : 0;
                        const angle = i * step - Math.PI / 2;
                        x = 12 * Math.cos(angle);
                        y = 12 * Math.sin(angle);
                    }
                } else {
                    const step =
                        citIds.length > 0 ? (Math.PI * 2) / citIds.length : 0;
                    const angle = i * step - Math.PI / 2;
                    x = 12 * Math.cos(angle);
                    y = 12 * Math.sin(angle);
                }

                if (!g.hasNode(id)) {
                    g.addNode(id, { x, y, size, label, color });
                }
                g.addEdge(paper.entry_id, id, {
                    color: "rgba(255,107,107,0.35)",
                    size: 0.6,
                    type: "arrow",
                });
            });
        }

        if (showReferences) {
            const refIds = [...new Set(data.referencedIds)]
                .filter((id) => !data.citedIds.includes(id))
                .slice(0, REFERENCE_LIMIT);
            refIds.forEach((id, i) => {
                const real = data.realPapers[id];
                const label = real ? truncate(real.title, 50) : id.slice(0, 20);
                const color = real ? COLOR_REFERENCE : COLOR_DUMMY;
                const size = real ? 4.5 : 2.5;

                let x: number, y: number;
                if (real) {
                    const [tx, ty] = parseTsne(real.tsne);
                    if (tx !== 0 || ty !== 0) {
                        x = tx - paper.tsne1;
                        y = ty - paper.tsne2;
                    } else {
                        const step =
                            refIds.length > 0
                                ? (Math.PI * 2) / refIds.length
                                : 0;
                        const angle = i * step - Math.PI / 2;
                        x = 25 * Math.cos(angle);
                        y = 25 * Math.sin(angle);
                    }
                } else {
                    const step =
                        refIds.length > 0 ? (Math.PI * 2) / refIds.length : 0;
                    const angle = i * step - Math.PI / 2;
                    x = 25 * Math.cos(angle);
                    y = 25 * Math.sin(angle);
                }

                if (!g.hasNode(id)) {
                    g.addNode(id, { x, y, size, label, color });
                }
                g.addEdge(id, paper.entry_id, {
                    color: "rgba(78,205,196,0.30)",
                    size: 0.5,
                    type: "arrow",
                });
            });
        }

        // Non-arXiv: single aggregate node below center
        if (showNonArxiv) {
            const nonArxivCit = paper.non_arxiv_citation_count ?? 0;
            const nonArxivRef = paper.non_arxiv_reference_count ?? 0;
            const totalNonArxiv = nonArxivCit + nonArxivRef;
            if (totalNonArxiv > 0) {
                const nodeSize = Math.min(
                    6 + Math.sqrt(totalNonArxiv) * 1.5,
                    30,
                );
                const dummyId = "__non_arxiv_aggregate";
                g.addNode(dummyId, {
                    x: 0,
                    y: 20,
                    size: nodeSize,
                    label: `${totalNonArxiv} Non-arXiv`,
                    color: COLOR_DUMMY,
                    nonArxivCitations: nonArxivCit,
                    nonArxivReferences: nonArxivRef,
                });
                if (nonArxivCit > 0) {
                    g.addEdge(paper.entry_id, dummyId, {
                        color: "rgba(85,85,85,0.25)",
                        size: 0.6,
                    });
                }
                if (nonArxivRef > 0 && nonArxivCit === 0) {
                    g.addEdge(dummyId, paper.entry_id, {
                        color: "rgba(85,85,85,0.25)",
                        size: 0.6,
                    });
                }
            }
        }

        // Apply spread to prevent overlapping nodes
        applySpread(g);

        return g;
    }

    function truncate(s: string, n: number): string {
        return s.length > n ? s.slice(0, n) + "…" : s;
    }

    // ─── rebuild renderer after filter change ────────────────────────
    function rebuildRenderer() {
        if (!fetchedData || !container) return;
        destroySigma();
        graph = buildGraph(fetchedData);
        renderer = new Sigma(graph, container, {
            renderEdgeLabels: false,
            defaultNodeType: "circle",
            defaultEdgeType: "line",
            minCameraRatio: 0.01,
            maxCameraRatio: 50,
            labelRenderedSizeThreshold: 18,
            labelColor: { color: "#ccc" },
        });
        attachSigmaEvents();
    }

    function destroySigma() {
        if (renderer) {
            renderer.kill();
            renderer = null;
        }
    }

    function attachSigmaEvents() {
        if (!renderer || !graph) return;
        renderer.on("enterNode", ({ node }) => {
            if (!graph) return;
            const attrs = graph.getNodeAttributes(node);
            if (node === "__non_arxiv_aggregate") {
                const cit = attrs.nonArxivCitations ?? 0;
                const ref = attrs.nonArxivReferences ?? 0;
                tooltipText = `Non-arXiv Citations: ${cit}\nNon-arXiv References: ${ref}\nTotal: ${cit + ref}`;
                hoveredPaper = null;
            } else if (node === paper.entry_id) {
                // Show tooltip for center paper
                hoveredPaper = {
                    title: paper.title,
                    authors: paper.authors,
                    published: paper.published,
                    abstract: paper.abstract,
                    citations: paper.citations,
                    references: paper.references,
                    non_arxiv_citation_count: paper.non_arxiv_citation_count,
                    non_arxiv_reference_count: paper.non_arxiv_reference_count,
                };
                tooltipText = null;
            } else if (fetchedData?.realPapers[node]) {
                const rp = fetchedData.realPapers[node];
                hoveredPaper = {
                    title: rp.title ?? node,
                    authors: Array.isArray(rp.authors)
                        ? rp.authors.join(", ")
                        : (rp.authors ?? ""),
                    published: rp.published ?? null,
                    abstract: rp.abstract ?? "",
                    citations: Array.isArray(rp.citations) ? rp.citations : [],
                    references: Array.isArray(rp.references)
                        ? rp.references
                        : [],
                    non_arxiv_citation_count: rp.non_arxiv_citation_count ?? 0,
                    non_arxiv_reference_count:
                        rp.non_arxiv_reference_count ?? 0,
                };
                tooltipText = null;
            }
            // Pointer cursor for clickable nodes
            if (node !== paper.entry_id && node !== "__non_arxiv_aggregate") {
                if (container) container.style.cursor = "pointer";
            }
        });
        renderer.on("leaveNode", () => {
            tooltipText = null;
            hoveredPaper = null;
            if (container) container.style.cursor = "";
        });
        renderer.getMouseCaptor().on("mousemovebody", (e: any) => {
            tooltipPos = { x: e.x + 14, y: e.y - 10 };
        });

        // Clickable citation/reference nodes → navigate to that paper
        renderer.on("clickNode", ({ node }) => {
            // Don't navigate for center paper or aggregate node
            if (node === paper.entry_id || node === "__non_arxiv_aggregate")
                return;
            if (!fetchedData) return;
            const raw = fetchedData.realPapers[node];
            if (!raw) return;
            // Build a Paper-like object from the raw API data
            const [tx, ty] = parseTsne(raw.tsne);
            const target: Paper = {
                id: raw.id ?? 0,
                entry_id: raw.entry_id,
                title: raw.title ?? node,
                authors: Array.isArray(raw.authors)
                    ? raw.authors.join(", ")
                    : (raw.authors ?? ""),
                abstract: raw.abstract ?? "",
                published: raw.published ?? null,
                categories: raw.categories ?? null,
                url: raw.url ?? null,
                citations: Array.isArray(raw.citations)
                    ? raw.citations.map((c: any) =>
                          typeof c === "string"
                              ? c
                              : (c.cited_paper_entry_id ?? c.entry_id ?? ""),
                      )
                    : [],
                references: Array.isArray(raw.references)
                    ? raw.references.map((r: any) =>
                          typeof r === "string"
                              ? r
                              : (r.referenced_paper_entry_id ??
                                r.entry_id ??
                                ""),
                      )
                    : [],
                non_arxiv_citation_count: raw.non_arxiv_citation_count ?? 0,
                non_arxiv_reference_count: raw.non_arxiv_reference_count ?? 0,
                tsne1: tx,
                tsne2: ty,
                cluster: raw.cluster ?? "",
            };
            dispatch("navigate", target);
        });
    }

    // reactive rebuilds when filters change
    let filtersInitialized = false;

    // ─── Relation View ────────────────────────────────────────────────
    let relatedPapers: any[] = [];
    let relatedLoading = false;
    let relatedError: string | null = null;
    let relationCanvas: HTMLDivElement | null = null;

    // card positions and drag state
    interface CardPos {
        x: number;
        y: number;
    }
    let cardPositions: Record<string, CardPos> = {};
    let cardScales: Record<string, number> = {};
    let expandedAbstracts = new Set<string>();
    let dragTarget: string | null = null;
    let dragOffset = { x: 0, y: 0 };

    // resize drag state
    let resizeTarget: string | null = null;
    let resizeStartY = 0;
    let resizeStartScale = 1;

    // zoom/pan state for relation canvas
    let canvasScale = 1;
    let canvasTranslate = { x: 0, y: 0 };
    let isPanning = false;
    let panStart = { x: 0, y: 0 };
    let panTranslateStart = { x: 0, y: 0 };

    function getStorageKey(): string {
        return `relation_layout_${paper.entry_id}`;
    }

    function savePositions() {
        try {
            localStorage.setItem(
                getStorageKey(),
                JSON.stringify({
                    positions: cardPositions,
                    scales: cardScales,
                }),
            );
        } catch {
            /* ignore */
        }
    }

    function loadPositions(): {
        positions: Record<string, CardPos>;
        scales: Record<string, number>;
    } | null {
        try {
            const raw = localStorage.getItem(getStorageKey());
            if (raw) {
                const parsed = JSON.parse(raw);
                // Support old format (plain positions object)
                if (parsed && parsed.positions) return parsed;
                if (parsed && typeof parsed === "object" && !parsed.positions) {
                    return { positions: parsed, scales: {} };
                }
            }
        } catch {
            /* ignore */
        }
        return null;
    }

    function defaultTreeLayout(papers: any[]): Record<string, CardPos> {
        const pos: Record<string, CardPos> = {};
        // Selected paper at top center
        pos[paper.entry_id] = { x: -155, y: 0 };
        // Related papers in rows below
        const cols = Math.min(papers.length, 4);
        const cardW = 330;
        const cardH = 220;
        const gapX = 20;
        const gapY = 30;
        const totalW = cols * cardW + (cols - 1) * gapX;
        const startX = -totalW / 2;
        papers.forEach((p, i) => {
            const row = Math.floor(i / cols);
            const col = i % cols;
            pos[p.entry_id] = {
                x: startX + col * (cardW + gapX),
                y: 280 + row * (cardH + gapY),
            };
        });
        return pos;
    }

    async function loadRelatedPapers() {
        if (relatedPapers.length > 0) return; // already loaded
        relatedLoading = true;
        relatedError = null;
        try {
            // Fetch the main paper to get related_arxiv_ids
            const res = await fetch(
                `${apiBaseUrl}/papers/${encodeURIComponent(paper.entry_id)}`,
            );
            if (!res.ok)
                throw new Error(`Failed to fetch paper: ${res.status}`);
            const mainPaper = await res.json();

            let relatedIds: string[] = [];
            if (mainPaper.related_arxiv_ids) {
                let ids = mainPaper.related_arxiv_ids;
                if (typeof ids === "string") {
                    try {
                        ids = JSON.parse(ids);
                    } catch {
                        ids = [];
                    }
                }
                if (Array.isArray(ids)) relatedIds = ids.slice(0, 20);
            }

            if (relatedIds.length === 0) {
                relatedPapers = [];
                relatedLoading = false;
                return;
            }

            // Batch fetch the related papers
            const batchRes = await fetch(`${apiBaseUrl}/papers/batch`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ entryIds: relatedIds }),
            });
            if (!batchRes.ok)
                throw new Error(
                    `Failed to fetch related papers: ${batchRes.status}`,
                );
            const batchPapers = await batchRes.json();

            // Sort by the order in related_arxiv_ids
            const orderMap = new Map(relatedIds.map((id, i) => [id, i]));
            relatedPapers = batchPapers
                .filter(
                    (p: any) => p.title && p.title !== "[STUB] Pending Fetch",
                )
                .sort(
                    (a: any, b: any) =>
                        (orderMap.get(a.entry_id) ?? 999) -
                        (orderMap.get(b.entry_id) ?? 999),
                );

            // Load saved positions or generate default layout
            const saved = loadPositions();
            if (saved && Object.keys(saved.positions).length > 0) {
                cardPositions = saved.positions;
                cardScales = saved.scales ?? {};
                // Ensure all papers have a position
                relatedPapers.forEach((p, i) => {
                    if (!cardPositions[p.entry_id]) {
                        cardPositions[p.entry_id] = {
                            x: -160 + (i % 4) * 350,
                            y: 280 + Math.floor(i / 4) * 250,
                        };
                    }
                });
            } else {
                cardPositions = defaultTreeLayout(relatedPapers);
                cardScales = {};
            }
        } catch (e) {
            relatedError = e instanceof Error ? e.message : String(e);
        } finally {
            relatedLoading = false;
        }
    }

    // ─── relation view drag handlers ──────────────────────────────────
    function onCardMouseDown(e: MouseEvent, entryId: string) {
        e.stopPropagation();
        e.preventDefault();
        dragTarget = entryId;
        dragOffset = {
            x:
                e.clientX / canvasScale -
                (cardPositions[entryId]?.x ?? 0) -
                canvasTranslate.x,
            y:
                e.clientY / canvasScale -
                (cardPositions[entryId]?.y ?? 0) -
                canvasTranslate.y,
        };
        window.addEventListener("mousemove", onDragMove);
        window.addEventListener("mouseup", onDragEnd);
    }

    function onDragMove(e: MouseEvent) {
        if (!dragTarget) return;
        cardPositions[dragTarget] = {
            x: e.clientX / canvasScale - dragOffset.x - canvasTranslate.x,
            y: e.clientY / canvasScale - dragOffset.y - canvasTranslate.y,
        };
        cardPositions = { ...cardPositions };
    }

    function onDragEnd() {
        if (dragTarget) savePositions();
        dragTarget = null;
        window.removeEventListener("mousemove", onDragMove);
        window.removeEventListener("mouseup", onDragEnd);
    }

    // ─── card resize handlers ─────────────────────────────────────────
    function onResizeMouseDown(e: MouseEvent, entryId: string) {
        e.stopPropagation();
        e.preventDefault();
        resizeTarget = entryId;
        resizeStartY = e.clientY;
        resizeStartScale = cardScales[entryId] ?? 1;
        window.addEventListener("mousemove", onResizeMove);
        window.addEventListener("mouseup", onResizeEnd);
    }

    function onResizeMove(e: MouseEvent) {
        if (!resizeTarget) return;
        const dy = e.clientY - resizeStartY;
        // Dragging down = increase scale, up = decrease. 200px = 1.0 scale unit
        const newScale = Math.max(
            0.5,
            Math.min(2.0, resizeStartScale + dy / 200),
        );
        cardScales[resizeTarget] = newScale;
        cardScales = { ...cardScales };
    }

    function onResizeEnd() {
        if (resizeTarget) savePositions();
        resizeTarget = null;
        window.removeEventListener("mousemove", onResizeMove);
        window.removeEventListener("mouseup", onResizeEnd);
    }

    // ─── canvas pan handlers ──────────────────────────────────────────
    function onCanvasMouseDown(e: MouseEvent) {
        if (dragTarget) return;
        isPanning = true;
        panStart = { x: e.clientX, y: e.clientY };
        panTranslateStart = { ...canvasTranslate };
        window.addEventListener("mousemove", onPanMove);
        window.addEventListener("mouseup", onPanEnd);
    }

    function onPanMove(e: MouseEvent) {
        if (!isPanning) return;
        canvasTranslate = {
            x: panTranslateStart.x + (e.clientX - panStart.x) / canvasScale,
            y: panTranslateStart.y + (e.clientY - panStart.y) / canvasScale,
        };
    }

    function onPanEnd() {
        isPanning = false;
        window.removeEventListener("mousemove", onPanMove);
        window.removeEventListener("mouseup", onPanEnd);
    }

    function onCanvasWheel(e: WheelEvent) {
        e.preventDefault();
        const delta = e.deltaY > 0 ? 0.9 : 1.1;
        canvasScale = Math.max(0.2, Math.min(3, canvasScale * delta));
    }

    function toggleAbstract(entryId: string) {
        if (expandedAbstracts.has(entryId)) expandedAbstracts.delete(entryId);
        else expandedAbstracts.add(entryId);
        expandedAbstracts = new Set(expandedAbstracts);
    }

    function displayAuthors(
        authors: string | string[] | null | undefined,
        limit = 3,
    ): string {
        if (!authors) return "";
        const str = Array.isArray(authors) ? authors.join(", ") : authors;
        const parts = str
            .split(",")
            .map((s: string) => s.trim())
            .filter(Boolean);
        if (parts.length <= limit) return str;
        return parts.slice(0, limit).join(", ") + ` et al. (${parts.length})`;
    }

    function getFirstCategory(cats: string | null | undefined): string {
        if (!cats) return "N/A";
        return cats.trim().split(/[\s,]+/)[0] ?? cats;
    }

    function categoryFullName(cats: string | null | undefined): string {
        const cat = getFirstCategory(cats);
        const fullName = getSubcategoryName(cat);
        return fullName && fullName !== cat ? `${fullName} (${cat})` : cat;
    }

    // ─── view mode switching ──────────────────────────────────────────
    function switchToGraph() {
        viewMode = "graph";
        // Force rebuild on next tick after DOM is visible
        tick().then(() => {
            if (fetchedData && !loading) {
                rebuildRenderer();
            }
        });
    }

    function switchToRelation() {
        viewMode = "relation";
        // Kill sigma to free resources
        destroySigma();
        loadRelatedPapers();
    }

    // ─── lifecycle ────────────────────────────────────────────────────
    onMount(() => {
        fetchNeighbourhood()
            .then((data) => {
                fetchedData = data;
                dispatch("neighbourhoodLoaded", {
                    citationCount: [...new Set(data.citedIds)].length,
                    referenceCount: [...new Set(data.referencedIds)].length,
                });
                if (!container) return;
                graph = buildGraph(data);
                renderer = new Sigma(graph, container, {
                    renderEdgeLabels: false,
                    defaultNodeType: "circle",
                    defaultEdgeType: "line",
                    minCameraRatio: 0.01,
                    maxCameraRatio: 50,
                    labelRenderedSizeThreshold: 18,
                    labelColor: { color: "#ccc" },
                });
                attachSigmaEvents();
                loading = false;
                filtersInitialized = true;
            })
            .catch((err) => {
                errorMsg = err instanceof Error ? err.message : String(err);
                loading = false;
                filtersInitialized = true;
            });
    });

    onDestroy(() => {
        destroySigma();
        window.removeEventListener("mousemove", onDragMove);
        window.removeEventListener("mouseup", onDragEnd);
        window.removeEventListener("mousemove", onResizeMove);
        window.removeEventListener("mouseup", onResizeEnd);
        window.removeEventListener("mousemove", onPanMove);
        window.removeEventListener("mouseup", onPanEnd);
    });

    $: abstractSnippet = paper.abstract
        ? paper.abstract.length > 300
            ? paper.abstract.slice(0, 300) + "…"
            : paper.abstract
        : "No abstract available.";
</script>

<div class="detail-wrapper">
    <!-- ── top controls bar ── -->
    <div class="top-bar">
        <button class="back-btn" on:click={() => dispatch("back")}
            >← Back</button
        >

        <div class="view-tabs">
            <button
                class="tab-btn"
                class:active={viewMode === "graph"}
                on:click={switchToGraph}
            >
                Citation Graph
            </button>
            <button
                class="tab-btn"
                class:active={viewMode === "relation"}
                on:click={switchToRelation}
            >
                Relation View
            </button>
        </div>
    </div>

    <!-- ── Citation Graph view ── -->
    {#if viewMode === "graph"}
        <div class="legend">
            <span class="legend-item legend-static">
                <span class="dot" style="background:{COLOR_CENTER}"></span> Selected
            </span>
            <button
                class="legend-item legend-toggle"
                class:muted={!showCitations}
                on:click={() => toggleFilter("citations")}
                title="Click to show/hide citations"
            >
                <span
                    class="dot"
                    style="background:{COLOR_CITATION};opacity:{showCitations
                        ? 1
                        : 0.3}"
                ></span>
                Cites
            </button>
            <button
                class="legend-item legend-toggle"
                class:muted={!showReferences}
                on:click={() => toggleFilter("references")}
                title="Click to show/hide cited-by"
            >
                <span
                    class="dot"
                    style="background:{COLOR_REFERENCE};opacity:{showReferences
                        ? 1
                        : 0.3}"
                ></span>
                Cited by
            </button>
            <button
                class="legend-item legend-toggle"
                class:muted={!showNonArxiv}
                on:click={() => toggleFilter("nonArxiv")}
                title="Click to show/hide non-arXiv aggregate"
            >
                <span
                    class="dot"
                    style="background:{COLOR_DUMMY};opacity:{showNonArxiv
                        ? 1
                        : 0.3}"
                ></span>
                Non-arXiv
            </button>
        </div>

        {#if loading}
            <div class="overlay">
                <div class="spinner"></div>
                <p>Loading citation network…</p>
            </div>
        {:else if errorMsg}
            <div class="overlay error"><p>{errorMsg}</p></div>
        {/if}

        <div class="sigma-container" bind:this={container}></div>

        {#if tooltipText}
            <div
                class="graph-tooltip"
                style="left:{tooltipPos.x}px;top:{tooltipPos.y}px"
            >
                {#each tooltipText.split("\n") as line}
                    <div>{line}</div>
                {/each}
            </div>
        {/if}

        {#if hoveredPaper}
            <div class="hover-tooltip">
                <h4>{hoveredPaper.title}</h4>
                <p class="meta">{hoveredPaper.authors}</p>
                <p class="meta">
                    {hoveredPaper.published
                        ? new Date(hoveredPaper.published).toLocaleDateString()
                        : ""}
                </p>
                <p class="abstract">
                    {(hoveredPaper.abstract ?? "").slice(0, 200)}{(
                        hoveredPaper.abstract ?? ""
                    ).length > 200
                        ? "…"
                        : ""}
                </p>
                <p class="stats">
                    Citations: {hoveredPaper.citations?.length ?? 0} | References:
                    {hoveredPaper.references?.length ?? 0} | Non-arXiv: {(hoveredPaper.non_arxiv_citation_count ??
                        0) + (hoveredPaper.non_arxiv_reference_count ?? 0)}
                </p>
            </div>
        {/if}
    {/if}

    <!-- ── Relation View ── -->
    {#if viewMode === "relation"}
        {#if relatedLoading}
            <div class="overlay">
                <div class="spinner"></div>
                <p>Loading related papers…</p>
            </div>
        {:else if relatedError}
            <div class="overlay error"><p>{relatedError}</p></div>
        {:else if relatedPapers.length === 0}
            <div class="relation-empty">
                <h3>No Related Papers</h3>
                <p>No semantically related papers found for this paper.</p>
            </div>
        {:else}
            <!-- svelte-ignore a11y-no-static-element-interactions -->
            <div
                class="relation-canvas"
                bind:this={relationCanvas}
                on:mousedown={onCanvasMouseDown}
                on:wheel|preventDefault={onCanvasWheel}
            >
                <div
                    class="relation-transform"
                    style="transform: scale({canvasScale}) translate({canvasTranslate.x}px, {canvasTranslate.y}px)"
                >
                    <!-- Connecting lines from selected to related (SVG behind cards) -->
                    <svg
                        class="relation-lines"
                        xmlns="http://www.w3.org/2000/svg"
                    >
                        {#each relatedPapers as rp (rp.entry_id)}
                            {@const sx =
                                (cardPositions[paper.entry_id]?.x ?? 0) + 155}
                            {@const sy =
                                (cardPositions[paper.entry_id]?.y ?? 0) + 200}
                            {@const ex =
                                (cardPositions[rp.entry_id]?.x ?? 0) + 155}
                            {@const ey = cardPositions[rp.entry_id]?.y ?? 0}
                            <line
                                x1={sx}
                                y1={sy}
                                x2={ex}
                                y2={ey}
                                stroke="rgba(147,51,234,0.15)"
                                stroke-width="1"
                            />
                        {/each}
                    </svg>

                    <!-- Selected paper card (anchored at top) -->
                    <div
                        class="rel-card rel-card-selected"
                        style="left:{cardPositions[paper.entry_id]?.x ??
                            0}px;top:{cardPositions[paper.entry_id]?.y ??
                            0}px;transform:scale({cardScales[paper.entry_id] ??
                            1});transform-origin:top left"
                        on:mousedown={(e) => onCardMouseDown(e, paper.entry_id)}
                    >
                        <div class="rel-card-header">
                            <span class="rel-card-badge selected">SELECTED</span
                            >
                        </div>
                        <h4 class="rel-card-title">{paper.title}</h4>
                        <p class="rel-card-authors">
                            {displayAuthors(paper.authors)}
                        </p>
                        <div class="rel-card-meta-row">
                            <span class="rel-card-year"
                                >{paper.published
                                    ? new Date(paper.published).getFullYear()
                                    : "—"}</span
                            >
                            <span class="rel-card-category"
                                >{categoryFullName(paper.categories)}</span
                            >
                        </div>
                        <div
                            class="rel-card-abstract"
                            class:expanded={expandedAbstracts.has(
                                paper.entry_id,
                            )}
                        >
                            {#if expandedAbstracts.has(paper.entry_id)}
                                <p>
                                    {paper.abstract || "No abstract available."}
                                </p>
                            {:else}
                                <p>
                                    {paper.abstract
                                        ? truncate(paper.abstract, 150)
                                        : "No abstract available."}
                                </p>
                            {/if}
                            {#if paper.abstract && paper.abstract.length > 150}
                                <button
                                    class="abstract-toggle"
                                    on:click|stopPropagation={() =>
                                        toggleAbstract(paper.entry_id)}
                                >
                                    {expandedAbstracts.has(paper.entry_id)
                                        ? "Show less"
                                        : "Show more"}
                                </button>
                            {/if}
                        </div>
                        <div class="rel-card-footer">
                            <span class="rel-stat"
                                >{paper.citations?.length ?? 0} Citations</span
                            >
                            <span class="rel-stat"
                                >{paper.references?.length ?? 0} References</span
                            >
                            {#if (paper.non_arxiv_citation_count ?? 0) + (paper.non_arxiv_reference_count ?? 0) > 0}
                                <span class="rel-stat non-arxiv"
                                    >{(paper.non_arxiv_citation_count ?? 0) +
                                        (paper.non_arxiv_reference_count ?? 0)} Non-arXiv</span
                                >
                            {/if}
                            {#if paper.url}
                                <a
                                    class="rel-arxiv-link"
                                    href={paper.url}
                                    target="_blank"
                                    rel="noopener"
                                    on:click|stopPropagation
                                >
                                    arXiv ↗
                                </a>
                            {/if}
                        </div>
                        <!-- svelte-ignore a11y-no-static-element-interactions -->
                        <div
                            class="resize-handle"
                            on:mousedown={(e) =>
                                onResizeMouseDown(e, paper.entry_id)}
                            title="Drag to resize"
                        ></div>
                    </div>

                    <!-- Related paper cards -->
                    {#each relatedPapers as rp (rp.entry_id)}
                        <!-- svelte-ignore a11y-no-static-element-interactions -->
                        <div
                            class="rel-card"
                            style="left:{cardPositions[rp.entry_id]?.x ??
                                0}px;top:{cardPositions[rp.entry_id]?.y ??
                                0}px;transform:scale({cardScales[rp.entry_id] ??
                                1});transform-origin:top left"
                            on:mousedown={(e) =>
                                onCardMouseDown(e, rp.entry_id)}
                        >
                            <div class="rel-card-header">
                                <span class="rel-card-badge"
                                    >{getFirstCategory(rp.categories)}</span
                                >
                            </div>
                            <h4 class="rel-card-title">
                                {rp.title ?? rp.entry_id}
                            </h4>
                            <p class="rel-card-authors">
                                {displayAuthors(rp.authors)}
                            </p>
                            <div class="rel-card-meta-row">
                                <span class="rel-card-year"
                                    >{rp.published
                                        ? new Date(rp.published).getFullYear()
                                        : "—"}</span
                                >
                                <span class="rel-card-category"
                                    >{categoryFullName(rp.categories)}</span
                                >
                            </div>
                            <div
                                class="rel-card-abstract"
                                class:expanded={expandedAbstracts.has(
                                    rp.entry_id,
                                )}
                            >
                                {#if expandedAbstracts.has(rp.entry_id)}
                                    <p>
                                        {rp.abstract ||
                                            "No abstract available."}
                                    </p>
                                {:else}
                                    <p>
                                        {rp.abstract
                                            ? truncate(rp.abstract, 120)
                                            : "No abstract available."}
                                    </p>
                                {/if}
                                {#if rp.abstract && rp.abstract.length > 120}
                                    <button
                                        class="abstract-toggle"
                                        on:click|stopPropagation={() =>
                                            toggleAbstract(rp.entry_id)}
                                    >
                                        {expandedAbstracts.has(rp.entry_id)
                                            ? "Show less"
                                            : "Show more"}
                                    </button>
                                {/if}
                            </div>
                            <div class="rel-card-footer">
                                <span class="rel-stat"
                                    >{rp.citations?.length ?? 0} Cit.</span
                                >
                                <span class="rel-stat"
                                    >{rp.references?.length ?? 0} Ref.</span
                                >
                                {#if (rp.non_arxiv_citation_count ?? 0) + (rp.non_arxiv_reference_count ?? 0) > 0}
                                    <span class="rel-stat non-arxiv"
                                        >{(rp.non_arxiv_citation_count ?? 0) +
                                            (rp.non_arxiv_reference_count ?? 0)}
                                        Non-arXiv</span
                                    >
                                {/if}
                                {#if rp.url}
                                    <a
                                        class="rel-arxiv-link"
                                        href={rp.url}
                                        target="_blank"
                                        rel="noopener"
                                        on:click|stopPropagation
                                    >
                                        arXiv ↗
                                    </a>
                                {/if}
                            </div>
                            <!-- svelte-ignore a11y-no-static-element-interactions -->
                            <div
                                class="resize-handle"
                                on:mousedown={(e) =>
                                    onResizeMouseDown(e, rp.entry_id)}
                                title="Drag to resize"
                            ></div>
                        </div>
                    {/each}
                </div>
            </div>
        {/if}
    {/if}
</div>

<style>
    .detail-wrapper {
        width: 100%;
        height: 100%;
        position: relative;
        background: var(--bg-primary, #0f1020);
        display: flex;
        flex-direction: column;
    }

    /* ── top bar ── */
    .top-bar {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 8px 12px;
        border-bottom: 1px solid var(--glass-border, rgba(255, 255, 255, 0.08));
        background: var(--bg-secondary, #141530);
        flex-shrink: 0;
        flex-wrap: wrap;
    }

    .back-btn {
        background: var(--glass-bg, rgba(20, 22, 50, 0.55));
        border: 1px solid var(--border-subtle, rgba(147, 51, 234, 0.18));
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
        background: rgba(0, 0, 0, 0.3);
        border-radius: var(--radius-sm, 8px);
        padding: 3px;
        border: 1px solid var(--glass-border, rgba(255, 255, 255, 0.08));
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
        background: linear-gradient(
            135deg,
            rgba(147, 51, 234, 0.35),
            rgba(232, 57, 160, 0.25)
        );
        color: var(--text-primary, #f0f0f8);
        box-shadow: 0 0 12px rgba(147, 51, 234, 0.2);
    }
    .tab-btn:hover:not(.active) {
        background: rgba(255, 255, 255, 0.05);
        color: var(--text-secondary, #a8a8c8);
    }

    /* ── sigma container ── */
    .sigma-container {
        flex: 1;
        width: 100%;
    }

    /* ── legend ── */
    .legend {
        position: absolute;
        bottom: 14px;
        left: 14px;
        z-index: 15;
        background: var(--glass-bg, rgba(20, 22, 50, 0.55));
        border: 1px solid var(--glass-border, rgba(255, 255, 255, 0.08));
        border-radius: var(--radius-sm, 8px);
        padding: 8px 14px;
        display: flex;
        gap: 14px;
        font-size: 12px;
        color: var(--text-secondary, #a8a8c8);
        pointer-events: auto;
        backdrop-filter: blur(var(--glass-blur, 16px));
    }
    .legend-item {
        display: flex;
        align-items: center;
        gap: 5px;
    }
    .legend-static {
        cursor: default;
        user-select: none;
    }
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
    .legend-toggle:hover {
        color: var(--text-primary, #f0f0f8);
    }
    .legend-toggle.muted {
        color: var(--text-muted, #6b6b8d);
    }
    .dot {
        width: 10px;
        height: 10px;
        border-radius: 50%;
        display: inline-block;
        box-shadow: 0 0 5px currentColor;
        flex-shrink: 0;
    }

    /* ── overlays ── */
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
    .overlay.error {
        color: #f56565;
    }
    .spinner {
        width: 28px;
        height: 28px;
        border: 3px solid rgba(147, 51, 234, 0.2);
        border-top-color: var(--accent-cyan, #22d3ee);
        border-radius: 50%;
        animation: spin 0.8s linear infinite;
    }
    @keyframes spin {
        to {
            transform: rotate(360deg);
        }
    }

    /* ── hover tooltip (paper info on node hover) ── */
    .hover-tooltip {
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
        z-index: 30;
        pointer-events: none;
        backdrop-filter: blur(var(--glass-blur, 16px));
        box-shadow: var(--shadow-glow-sm);
    }
    .hover-tooltip h4 {
        margin: 0 0 6px;
        font-size: 14px;
        color: var(--text-primary, #f0f0f8);
        line-height: 1.3;
        font-weight: 600;
    }
    .hover-tooltip .meta {
        margin: 2px 0;
        color: var(--text-muted, #6b6b8d);
        font-size: 12px;
    }
    .hover-tooltip .abstract {
        margin: 8px 0 4px;
        line-height: 1.4;
        color: var(--text-secondary, #a8a8c8);
    }
    .hover-tooltip .stats {
        margin: 6px 0 0;
        color: var(--accent-cyan, #22d3ee);
        font-size: 11px;
        opacity: 0.8;
    }

    /* ── graph tooltip for non-arXiv aggregate ── */
    .graph-tooltip {
        position: absolute;
        z-index: 30;
        background: var(--glass-bg, rgba(20, 22, 50, 0.9));
        border: 1px solid var(--glass-border, rgba(255, 255, 255, 0.12));
        border-radius: 8px;
        padding: 8px 12px;
        color: var(--text-primary, #f0f0f8);
        font-size: 12px;
        pointer-events: none;
        backdrop-filter: blur(12px);
        white-space: pre-line;
        line-height: 1.6;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
    }

    /* ── relation view ── */
    .relation-empty {
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
    .relation-empty h3 {
        margin: 0;
        font-size: 20px;
        color: var(--text-primary, #f0f0f8);
    }
    .relation-empty p {
        margin: 0;
        font-size: 14px;
        line-height: 1.5;
        max-width: 440px;
    }

    .relation-canvas {
        flex: 1;
        overflow: hidden;
        position: relative;
        cursor: grab;
        user-select: none;
    }
    .relation-canvas:active {
        cursor: grabbing;
    }

    .relation-transform {
        position: absolute;
        top: 40px;
        left: 50%;
        transform-origin: top center;
        width: 0;
        height: 0;
    }

    .relation-lines {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        pointer-events: none;
        overflow: visible;
    }

    /* ── relation cards ── */
    .rel-card {
        position: absolute;
        width: 310px;
        background: var(--glass-bg, rgba(20, 22, 50, 0.75));
        border: 1px solid var(--glass-border, rgba(255, 255, 255, 0.08));
        border-radius: var(--radius-md, 12px);
        padding: 12px 14px;
        cursor: grab;
        transition:
            box-shadow 0.2s ease,
            border-color 0.2s ease;
        backdrop-filter: blur(var(--glass-blur, 16px));
        user-select: none;
    }
    .rel-card:hover {
        border-color: rgba(147, 51, 234, 0.3);
        box-shadow: 0 0 20px rgba(147, 51, 234, 0.15);
    }
    .rel-card:active {
        cursor: grabbing;
    }
    .rel-card-selected {
        border-color: rgba(0, 255, 136, 0.3);
        box-shadow: 0 0 24px rgba(0, 255, 136, 0.15);
    }
    .rel-card-selected:hover {
        border-color: rgba(0, 255, 136, 0.5);
        box-shadow: 0 0 30px rgba(0, 255, 136, 0.2);
    }

    .rel-card-header {
        display: flex;
        align-items: center;
        gap: 6px;
        margin-bottom: 6px;
    }

    .rel-card-badge {
        display: inline-block;
        font-size: 10px;
        font-weight: 600;
        padding: 2px 8px;
        border-radius: 999px;
        background: rgba(147, 51, 234, 0.2);
        color: rgba(147, 51, 234, 0.9);
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .rel-card-badge.selected {
        background: rgba(0, 255, 136, 0.15);
        color: #00ff88;
    }

    .rel-card-title {
        margin: 0 0 4px;
        font-size: 13px;
        font-weight: 600;
        color: var(--text-primary, #f0f0f8);
        line-height: 1.35;
        display: -webkit-box;
        -webkit-line-clamp: 3;
        line-clamp: 3;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }

    .rel-card-authors {
        margin: 0 0 4px;
        font-size: 11px;
        color: var(--text-muted, #6b6b8d);
        font-style: italic;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .rel-card-meta-row {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 6px;
        font-size: 11px;
    }

    .rel-card-year {
        color: var(--text-muted, #6b6b8d);
        font-weight: 500;
    }

    .rel-card-category {
        color: rgba(147, 51, 234, 0.7);
        font-size: 10px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .rel-card-abstract {
        margin-bottom: 8px;
        max-height: 60px;
        overflow: hidden;
        transition: max-height 0.3s ease;
    }
    .rel-card-abstract.expanded {
        max-height: 600px;
    }
    .rel-card-abstract p {
        margin: 0;
        font-size: 11px;
        line-height: 1.45;
        color: var(--text-secondary, #a8a8c8);
    }

    .abstract-toggle {
        background: none;
        border: none;
        color: var(--accent-cyan, #22d3ee);
        font-size: 10px;
        cursor: pointer;
        padding: 2px 0;
        transition: color 0.15s ease;
    }
    .abstract-toggle:hover {
        color: #5ee6f5;
    }

    .rel-card-footer {
        display: flex;
        align-items: center;
        gap: 8px;
        flex-wrap: wrap;
        border-top: 1px solid var(--glass-border, rgba(255, 255, 255, 0.06));
        padding-top: 6px;
    }

    .rel-stat {
        font-size: 10px;
        color: var(--text-muted, #6b6b8d);
    }
    .rel-stat.non-arxiv {
        color: #888;
    }

    .rel-arxiv-link {
        font-size: 10px;
        color: var(--accent-cyan, #22d3ee);
        text-decoration: none;
        margin-left: auto;
        transition: color 0.15s ease;
    }
    .rel-arxiv-link:hover {
        color: #5ee6f5;
        text-decoration: underline;
    }

    /* ── resize handle ── */
    .resize-handle {
        position: absolute;
        bottom: 4px;
        left: 4px;
        width: 14px;
        height: 14px;
        cursor: nesw-resize;
        opacity: 0;
        transition: opacity 0.15s ease;
        z-index: 5;
    }
    .resize-handle::before {
        content: "";
        position: absolute;
        bottom: 0;
        left: 0;
        width: 10px;
        height: 10px;
        border-left: 2px solid rgba(147, 51, 234, 0.5);
        border-bottom: 2px solid rgba(147, 51, 234, 0.5);
        border-radius: 0 0 0 3px;
    }
    .rel-card:hover .resize-handle {
        opacity: 1;
    }
</style>
