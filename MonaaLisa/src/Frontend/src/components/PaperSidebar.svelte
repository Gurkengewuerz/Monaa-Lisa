<!--
  PaperSidebar.svelte
  Sidebar for the Paper Detail view.
  Shows the selected paper's info, expandable citations & references,
  nested paper previews, navigation history, and a filter bar.
-->
<script lang="ts">
  import { createEventDispatcher, onMount, tick } from 'svelte';
  import type { Paper, PaperSession } from '$lib/types/paper';

  // ─── props ────────────────────────────────────────────────────────
  export let paper: Paper;
  export let apiBaseUrl: string = 'http://localhost:3000';
  export let isOpen: boolean = false;
  export let sessions: PaperSession[] = [];
  /** Colour used for all citation nodes in the graph – stays consistent */
  const COLOR_CITATION  = '#ff6b6b';
  const COLOR_REFERENCE = '#4ecdc4';

  interface NeighbourPaperItem {
    entry_id: string;
    title: string;
    authors: string;
    abstract: string;
    published: string | null;
    categories: string | null;
    non_arxiv_citation_count: number;
    non_arxiv_reference_count: number;
  }

  const dispatch = createEventDispatcher();

  // ─── UI state ─────────────────────────────────────────────────────
  let historyOpen    = false;
  let citationsOpen  = true;
  let referencesOpen = true;
  let abstractExpanded = false;

  // Filter: which sections to show
  let filterCitations  = true;
  let filterReferences = true;

  // ─── neighbour data ───────────────────────────────────────────────
  let loading = true;
  let errorMsg: string | null = null;
  let citedPapers: NeighbourPaperItem[]     = []; // papers this paper cites
  let citedByPapers: NeighbourPaperItem[]   = []; // papers that cite this paper
  let nonArxivCitations  = 0;
  let nonArxivReferences = 0;

  // Per-item expanded state ─ maps entry_id → { abstract: bool, nested: bool }
  let expandedAbstracts = new Set<string>();
  let expandedNested    = new Set<string>();
  // Nested data: entry_id → { cites: NeighbourPaperItem[], citedBy: NeighbourPaperItem[] }
  let nestedData: Record<string, { cites: NeighbourPaperItem[]; citedBy: NeighbourPaperItem[]; loading: boolean }> = {};

  // Focused item inside the sidebar (single-click)
  let focusedId: string | null = null;

  // Click timing for double-click detection
  let lastClickId: string | null = null;
  let lastClickTs = 0;
  const DBLCLICK_MS = 280;

  // ─── fetch neighbourhood ──────────────────────────────────────────
  async function fetchNeighbourhood(entryId: string) {
    loading = true;
    errorMsg = null;
    citedPapers    = [];
    citedByPapers  = [];

    try {
      const [citRes, refRes] = await Promise.all([
        fetch(`${apiBaseUrl}/paper-citations/paper/${encodeURIComponent(entryId)}`),
        fetch(`${apiBaseUrl}/paper-references/paper/${encodeURIComponent(entryId)}`),
      ]);

      const citationsRaw: { cited_paper_entry_id: string }[]    = citRes.ok  ? await citRes.json()  : [];
      const referencesRaw: { referenced_paper_entry_id: string }[] = refRes.ok ? await refRes.json() : [];

      const citedIds    = citationsRaw.map(c => c.cited_paper_entry_id);
      const referencedIds = referencesRaw.map(r => r.referenced_paper_entry_id);

      const allIds = [...new Set([...citedIds, ...referencedIds])];
      let realPapers: Record<string, NeighbourPaperItem> = {};

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
        results.flat().forEach((p: any) => {
          realPapers[p.entry_id] = {
            entry_id: p.entry_id,
            title: p.title ?? p.entry_id,
            authors: Array.isArray(p.authors) ? p.authors.join(', ') : (p.authors ?? ''),
            abstract: p.abstract ?? '',
            published: p.published ?? null,
            categories: p.categories ?? null,
            non_arxiv_citation_count: p.non_arxiv_citation_count ?? 0,
            non_arxiv_reference_count: p.non_arxiv_reference_count ?? 0,
          };
        });
      }

      citedPapers   = [...new Set(citedIds)].map(id => realPapers[id]).filter(Boolean);
      citedByPapers = [...new Set(referencedIds)].map(id => realPapers[id]).filter(Boolean);
      nonArxivCitations  = paper.non_arxiv_citation_count  ?? 0;
      nonArxivReferences = paper.non_arxiv_reference_count ?? 0;
    } catch (e) {
      errorMsg = e instanceof Error ? e.message : 'Failed to load neighbourhood.';
    } finally {
      loading = false;
    }
  }

  // ─── fetch nested data for an item ───────────────────────────────
  async function fetchNested(entryId: string) {
    if (nestedData[entryId] !== undefined) return;
    nestedData = { ...nestedData, [entryId]: { cites: [], citedBy: [], loading: true } };

    try {
      const [citRes, refRes] = await Promise.all([
        fetch(`${apiBaseUrl}/paper-citations/paper/${encodeURIComponent(entryId)}`),
        fetch(`${apiBaseUrl}/paper-references/paper/${encodeURIComponent(entryId)}`),
      ]);

      const citationsRaw: { cited_paper_entry_id: string }[]     = citRes.ok  ? await citRes.json()  : [];
      const referencesRaw: { referenced_paper_entry_id: string }[] = refRes.ok ? await refRes.json() : [];

      const citedIds    = citationsRaw.map(c => c.cited_paper_entry_id).slice(0, 20);
      const citedByIds  = referencesRaw.map(r => r.referenced_paper_entry_id).slice(0, 20);
      const allIds = [...new Set([...citedIds, ...citedByIds])];

      let realPapers: Record<string, NeighbourPaperItem> = {};
      if (allIds.length > 0) {
        const raw = await fetch(`${apiBaseUrl}/papers/batch`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ entryIds: allIds }),
        }).then(r => r.ok ? r.json() : []);
        raw.forEach((p: any) => {
          realPapers[p.entry_id] = {
            entry_id: p.entry_id,
            title: p.title ?? p.entry_id,
            authors: Array.isArray(p.authors) ? p.authors.join(', ') : (p.authors ?? ''),
            abstract: p.abstract ?? '',
            published: p.published ?? null,
            categories: p.categories ?? null,
            non_arxiv_citation_count: p.non_arxiv_citation_count ?? 0,
            non_arxiv_reference_count: p.non_arxiv_reference_count ?? 0,
          };
        });
      }

      nestedData = {
        ...nestedData,
        [entryId]: {
          cites: citedIds.map(id => realPapers[id]).filter(Boolean),
          citedBy: citedByIds.map(id => realPapers[id]).filter(Boolean),
          loading: false,
        },
      };
    } catch {
      nestedData = { ...nestedData, [entryId]: { cites: [], citedBy: [], loading: false } };
    }
  }

  // ─── interaction helpers ──────────────────────────────────────────
  function handleItemClick(item: NeighbourPaperItem) {
    const now = Date.now();
    if (lastClickId === item.entry_id && now - lastClickTs < DBLCLICK_MS) {
      // Double-click → navigate
      navigateTo(item);
    } else {
      // Single click → focus
      focusedId = focusedId === item.entry_id ? null : item.entry_id;
      lastClickId = item.entry_id;
      lastClickTs = now;
    }
  }

  function navigateTo(item: NeighbourPaperItem) {
    // Build a minimal Paper-compatible object and dispatch navigate
    const p = {
      id: 0,
      entry_id: item.entry_id,
      title: item.title,
      authors: item.authors,
      abstract: item.abstract,
      published: item.published,
      categories: item.categories,
      url: null,
      citations: [],
      references: [],
      non_arxiv_citation_count: item.non_arxiv_citation_count,
      non_arxiv_reference_count: item.non_arxiv_reference_count,
      tsne1: 0,
      tsne2: 0,
      cluster: item.categories ?? 'U',
    };
    dispatch('navigate', p);
  }

  function toggleAbstract(entryId: string) {
    if (expandedAbstracts.has(entryId)) {
      expandedAbstracts.delete(entryId);
    } else {
      expandedAbstracts.add(entryId);
    }
    expandedAbstracts = new Set(expandedAbstracts);
  }

  function toggleNested(entryId: string) {
    if (expandedNested.has(entryId)) {
      expandedNested.delete(entryId);
    } else {
      expandedNested.add(entryId);
      fetchNested(entryId);
    }
    expandedNested = new Set(expandedNested);
  }

  function toggleSidebar() {
    dispatch('toggle');
  }

  function deleteSession(sessionId: string) {
    dispatch('deleteSession', sessionId);
  }

  function restoreSession(session: PaperSession) {
    dispatch('restoreSession', session);
  }

  // ─── format helpers ───────────────────────────────────────────────
  function formatYear(d: string | null): string {
    if (!d) return '—';
    return new Date(d).getFullYear().toString();
  }

  function truncate(s: string, n: number): string {
    return s.length > n ? s.slice(0, n) + '…' : s;
  }

  function firstCat(categories: string | null): string {
    if (!categories) return '';
    const cat = categories.trim().split(/[\s,]+/)[0] ?? '';
    return cat;
  }

  // ─── reactive: reload when paper changes ──────────────────────────
  $: {
    const eid = paper?.entry_id;
    if (eid) {
      focusedId = null;
      expandedAbstracts = new Set();
      expandedNested = new Set();
      nestedData = {};
      abstractExpanded = false;
      fetchNeighbourhood(eid);
    }
  }

  onMount(() => {
    if (paper?.entry_id) {
      fetchNeighbourhood(paper.entry_id);
    }
  });

  $: abstractSnippet = paper?.abstract
    ? (paper.abstract.length > 250 ? paper.abstract.slice(0, 250) + '…' : paper.abstract)
    : 'No abstract available.';
</script>

<!-- toggle button -->
<button class="sidebar-toggle" class:open={isOpen} on:click={toggleSidebar}>
  <span class="toggle-icon">{isOpen ? '→' : '←'}</span>
</button>

<!-- sidebar panel -->
<div class="sidebar" class:open={isOpen}>

  <div class="sidebar-header">
    <h3>Paper Details</h3>
    <button class="close-btn" on:click={toggleSidebar}>×</button>
  </div>

  <!-- filter chips -->
  <div class="filter-bar">
    <label class="filter-chip" class:active={filterCitations} title="Show/hide citations section">
      <input type="checkbox" bind:checked={filterCitations} />
      <span class="dot citation-dot"></span>
      Cites
    </label>
    <label class="filter-chip" class:active={filterReferences} title="Show/hide cited-by section">
      <input type="checkbox" bind:checked={filterReferences} />
      <span class="dot reference-dot"></span>
      Cited by
    </label>
  </div>

  <div class="sidebar-content">

    <!-- ── history ── -->
    {#if sessions.length > 0}
      <div class="section">
        <button class="section-header" on:click={() => (historyOpen = !historyOpen)}>
          <span class="section-title">📚 History ({sessions.length})</span>
          <span class="chevron">{historyOpen ? '▾' : '▸'}</span>
        </button>
        {#if historyOpen}
          <div class="history-list">
            {#each sessions as session (session.id)}
              <div class="history-item">
                <div class="history-info">
                  <p class="history-title" title={session.mainPaper.title}>
                    {truncate(session.mainPaper.title, 55)}
                  </p>
                  <p class="history-meta">
                    {session.mainPaper.authors.split(',')[0]}
                    · {new Date(session.startedAt).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                  </p>
                </div>
                <div class="history-actions">
                  <button class="history-nav-btn" on:click={() => restoreSession(session)} title="Go to this paper">↗</button>
                  <button class="history-del-btn" on:click={() => deleteSession(session.id)}  title="Remove from history">×</button>
                </div>
              </div>
            {/each}
          </div>
        {/if}
      </div>
    {/if}

    <!-- ── selected paper ── -->
    <div class="selected-paper">
      <div class="selected-label">Currently Viewing</div>
      <h4 class="selected-title">{paper.title}</h4>
      <p class="selected-meta">{paper.authors}</p>
      <p class="selected-meta">
        {formatYear(paper.published)}
        {#if paper.categories}&nbsp;·&nbsp;{firstCat(paper.categories)}{/if}
      </p>
      <div class="abstract-block">
        <button class="abstract-toggle" on:click={() => (abstractExpanded = !abstractExpanded)}>
          Abstract {abstractExpanded ? '▾' : '▸'}
        </button>
        <p class="abstract-text">{abstractExpanded ? (paper.abstract || 'N/A') : abstractSnippet}</p>
      </div>
      {#if paper.url}
        <a class="arxiv-link" href={paper.url} target="_blank" rel="noopener noreferrer">Open on arXiv ↗</a>
      {/if}
    </div>

    {#if loading}
      <div class="loading-row"><div class="mini-spinner"></div><span>Loading…</span></div>
    {:else if errorMsg}
      <div class="error-row">{errorMsg}</div>
    {:else}

      <!-- ── citations (papers this paper cites) ── -->
      {#if filterCitations}
        <div class="section">
          <button class="section-header citation-header" on:click={() => (citationsOpen = !citationsOpen)}>
            <span class="section-dot citation-dot"></span>
            <span class="section-title">Cites ({citedPapers.length}{nonArxivCitations > 0 ? ` + ${nonArxivCitations} non-arXiv` : ''})</span>
            <span class="chevron">{citationsOpen ? '▾' : '▸'}</span>
          </button>
          {#if citationsOpen}
            <div class="paper-list">
              {#each citedPapers as item (item.entry_id)}
                <!-- svelte-ignore a11y-click-events-have-key-events -->
                <!-- svelte-ignore a11y-no-static-element-interactions -->
                <div
                  class="paper-item"
                  class:focused={focusedId === item.entry_id}
                  on:click={() => handleItemClick(item)}
                  title="Single click to expand · Double-click to navigate to this paper"
                >
                  <div class="item-accent citation-accent"></div>
                  <div class="item-body">
                    <p class="item-title citation-title">{item.title}</p>
                    <p class="item-meta">{truncate(item.authors, 50)} · {formatYear(item.published)}</p>
                    {#if focusedId === item.entry_id}
                      <p class="item-abstract">
                        {item.abstract ? truncate(item.abstract, 300) : 'No abstract.'}
                      </p>
                      <div class="item-actions">
                        <button class="action-btn" on:click|stopPropagation={() => toggleAbstract(item.entry_id)}>
                          {expandedAbstracts.has(item.entry_id) ? 'Less ▴' : 'Full Abstract ▾'}
                        </button>
                        <button class="action-btn" on:click|stopPropagation={() => toggleNested(item.entry_id)}>
                          {expandedNested.has(item.entry_id) ? 'Less ▴' : 'Its network ▾'}
                        </button>
                        <button class="navigate-btn" on:click|stopPropagation={() => navigateTo(item)}>
                          Navigate ↗
                        </button>
                      </div>

                      {#if expandedAbstracts.has(item.entry_id)}
                        <p class="item-abstract full">{item.abstract || 'No abstract available.'}</p>
                      {/if}

                      {#if expandedNested.has(item.entry_id)}
                        {#if nestedData[item.entry_id]?.loading}
                          <div class="loading-row small"><div class="mini-spinner"></div><span>Loading…</span></div>
                        {:else}
                          {@const nd = nestedData[item.entry_id]}
                          {#if nd && (nd.cites.length > 0 || nd.citedBy.length > 0)}
                            <div class="nested-section">
                              {#if nd.cites.length > 0}
                                <p class="nested-label citation-label">Cites ({nd.cites.length})</p>
                                {#each nd.cites.slice(0, 8) as nc}
                                  <!-- svelte-ignore a11y-click-events-have-key-events -->
                                  <!-- svelte-ignore a11y-no-static-element-interactions -->
                                  <div class="nested-item" on:click|stopPropagation={() => navigateTo(nc)}>
                                    <span class="nested-title">{truncate(nc.title, 60)}</span>
                                  </div>
                                {/each}
                              {/if}
                              {#if nd.citedBy.length > 0}
                                <p class="nested-label reference-label">Cited by ({nd.citedBy.length})</p>
                                {#each nd.citedBy.slice(0, 8) as nr}
                                  <!-- svelte-ignore a11y-click-events-have-key-events -->
                                  <!-- svelte-ignore a11y-no-static-element-interactions -->
                                  <div class="nested-item" on:click|stopPropagation={() => navigateTo(nr)}>
                                    <span class="nested-title">{truncate(nr.title, 60)}</span>
                                  </div>
                                {/each}
                              {/if}
                            </div>
                          {:else}
                            <p class="nested-empty">No connected papers found.</p>
                          {/if}
                        {/if}
                      {/if}
                    {/if}
                  </div>
                </div>
              {/each}
              {#if citedPapers.length === 0}
                <p class="empty-msg">No arXiv citations found.</p>
              {/if}
            </div>
          {/if}
        </div>
      {/if}

      <!-- ── cited by (papers that cite this paper) ── -->
      {#if filterReferences}
        <div class="section">
          <button class="section-header reference-header" on:click={() => (referencesOpen = !referencesOpen)}>
            <span class="section-dot reference-dot"></span>
            <span class="section-title">Cited by ({citedByPapers.length}{nonArxivReferences > 0 ? ` + ${nonArxivReferences} non-arXiv` : ''})</span>
            <span class="chevron">{referencesOpen ? '▾' : '▸'}</span>
          </button>
          {#if referencesOpen}
            <div class="paper-list">
              {#each citedByPapers as item (item.entry_id)}
                <!-- svelte-ignore a11y-click-events-have-key-events -->
                <!-- svelte-ignore a11y-no-static-element-interactions -->
                <div
                  class="paper-item"
                  class:focused={focusedId === item.entry_id}
                  on:click={() => handleItemClick(item)}
                  title="Single click to expand · Double-click to navigate to this paper"
                >
                  <div class="item-accent reference-accent"></div>
                  <div class="item-body">
                    <p class="item-title reference-title">{item.title}</p>
                    <p class="item-meta">{truncate(item.authors, 50)} · {formatYear(item.published)}</p>
                    {#if focusedId === item.entry_id}
                      <p class="item-abstract">
                        {item.abstract ? truncate(item.abstract, 300) : 'No abstract.'}
                      </p>
                      <div class="item-actions">
                        <button class="action-btn" on:click|stopPropagation={() => toggleAbstract(item.entry_id)}>
                          {expandedAbstracts.has(item.entry_id) ? 'Less ▴' : 'Full Abstract ▾'}
                        </button>
                        <button class="action-btn" on:click|stopPropagation={() => toggleNested(item.entry_id)}>
                          {expandedNested.has(item.entry_id) ? 'Less ▴' : 'Its network ▾'}
                        </button>
                        <button class="navigate-btn reference-navigate" on:click|stopPropagation={() => navigateTo(item)}>
                          Navigate ↗
                        </button>
                      </div>

                      {#if expandedAbstracts.has(item.entry_id)}
                        <p class="item-abstract full">{item.abstract || 'No abstract available.'}</p>
                      {/if}

                      {#if expandedNested.has(item.entry_id)}
                        {#if nestedData[item.entry_id]?.loading}
                          <div class="loading-row small"><div class="mini-spinner"></div><span>Loading…</span></div>
                        {:else}
                          {@const nd = nestedData[item.entry_id]}
                          {#if nd && (nd.cites.length > 0 || nd.citedBy.length > 0)}
                            <div class="nested-section">
                              {#if nd.cites.length > 0}
                                <p class="nested-label citation-label">Cites ({nd.cites.length})</p>
                                {#each nd.cites.slice(0, 8) as nc}
                                  <!-- svelte-ignore a11y-click-events-have-key-events -->
                                  <!-- svelte-ignore a11y-no-static-element-interactions -->
                                  <div class="nested-item" on:click|stopPropagation={() => navigateTo(nc)}>
                                    <span class="nested-title">{truncate(nc.title, 60)}</span>
                                  </div>
                                {/each}
                              {/if}
                              {#if nd.citedBy.length > 0}
                                <p class="nested-label reference-label">Cited by ({nd.citedBy.length})</p>
                                {#each nd.citedBy.slice(0, 8) as nr}
                                  <!-- svelte-ignore a11y-click-events-have-key-events -->
                                  <!-- svelte-ignore a11y-no-static-element-interactions -->
                                  <div class="nested-item" on:click|stopPropagation={() => navigateTo(nr)}>
                                    <span class="nested-title">{truncate(nr.title, 60)}</span>
                                  </div>
                                {/each}
                              {/if}
                            </div>
                          {:else}
                            <p class="nested-empty">No connected papers found.</p>
                          {/if}
                        {/if}
                      {/if}
                    {/if}
                  </div>
                </div>
              {/each}
              {#if citedByPapers.length === 0}
                <p class="empty-msg">No arXiv citing papers found.</p>
              {/if}
            </div>
          {/if}
        </div>
      {/if}

    {/if}
  </div>
</div>

<style>
  /* ── toggle button ── */
  .sidebar-toggle {
    position: absolute;
    right: -5px;
    top: 50%;
    transform: translateY(-50%);
    background: linear-gradient(135deg, var(--accent-purple, #9333ea), var(--accent-magenta, #e839a0));
    border: none;
    border-radius: 50% 0 0 50%;
    width: 36px;
    height: 56px;
    color: white;
    cursor: pointer;
    z-index: 200;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 0 15px rgba(147, 51, 234, 0.3);
  }
  .sidebar-toggle:hover {
    box-shadow: 0 0 25px rgba(147, 51, 234, 0.5), 0 0 50px rgba(34, 211, 238, 0.2);
    transform: translateY(-50%) scale(1.05);
  }
  .sidebar-toggle.open {
    right: 380px;
    border-radius: 0 50% 50% 0;
  }
  .toggle-icon { font-size: 16px; font-weight: bold; }

  /* ── sidebar panel ── */
  .sidebar {
    position: absolute;
    right: -400px;
    top: 0;
    width: 385px;
    height: 100%;
    background: var(--bg-secondary, #141530);
    border-left: 1px solid var(--glass-border, rgba(255,255,255,0.08));
    transition: right 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    z-index: 150;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }
  .sidebar.open { right: 0; }

  .sidebar-header {
    padding: 14px 16px;
    border-bottom: 1px solid var(--glass-border, rgba(255,255,255,0.08));
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: linear-gradient(180deg, rgba(147,51,234,0.08), transparent);
    flex-shrink: 0;
  }
  .sidebar-header h3 {
    margin: 0;
    color: var(--text-primary, #f0f0f8);
    font-size: 15px;
    font-weight: 600;
  }
  .close-btn {
    background: none;
    border: none;
    color: var(--text-muted, #6b6b8d);
    font-size: 22px;
    cursor: pointer;
    padding: 0;
    width: 28px;
    height: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 8px;
    transition: all 0.15s ease;
  }
  .close-btn:hover { color: var(--text-primary, #f0f0f8); background: rgba(147,51,234,0.15); }

  /* ── filter bar ── */
  .filter-bar {
    display: flex;
    gap: 6px;
    padding: 8px 12px;
    border-bottom: 1px solid var(--glass-border, rgba(255,255,255,0.06));
    flex-shrink: 0;
    flex-wrap: wrap;
  }
  .filter-chip {
    display: flex;
    align-items: center;
    gap: 5px;
    padding: 3px 10px;
    border-radius: 999px;
    border: 1px solid var(--glass-border, rgba(255,255,255,0.10));
    background: rgba(255,255,255,0.04);
    color: var(--text-muted, #6b6b8d);
    cursor: pointer;
    font-size: 12px;
    transition: all 0.15s ease;
    user-select: none;
  }
  .filter-chip input { display: none; }
  .filter-chip.active {
    border-color: rgba(147,51,234,0.35);
    background: rgba(147,51,234,0.12);
    color: var(--text-primary, #f0f0f8);
  }

  /* ── content scroll area ── */
  .sidebar-content {
    flex: 1;
    overflow-y: auto;
    padding-bottom: 1rem;
    scrollbar-width: thin;
    scrollbar-color: rgba(147,51,234,0.3) transparent;
  }

  /* ── selected paper ── */
  .selected-paper {
    padding: 14px;
    border-bottom: 1px solid var(--glass-border, rgba(255,255,255,0.06));
    background: linear-gradient(180deg, rgba(147,51,234,0.05), transparent);
  }
  .selected-label {
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: var(--accent-purple, #9333ea);
    margin-bottom: 4px;
    font-weight: 600;
  }
  .selected-title {
    margin: 0 0 6px;
    font-size: 14px;
    color: var(--text-primary, #f0f0f8);
    line-height: 1.4;
    font-weight: 600;
  }
  .selected-meta {
    margin: 2px 0;
    font-size: 11px;
    color: var(--text-muted, #6b6b8d);
    font-style: italic;
  }
  .abstract-block { margin-top: 8px; }
  .abstract-toggle {
    background: none; border: none;
    color: var(--accent-purple, #9333ea);
    cursor: pointer; font-size: 11px; padding: 0;
    font-weight: 500; margin-bottom: 3px;
  }
  .abstract-text {
    margin: 0;
    font-size: 11px;
    color: var(--text-secondary, #a8a8c8);
    line-height: 1.5;
  }
  .arxiv-link {
    display: inline-block;
    margin-top: 6px;
    font-size: 11px;
    color: var(--accent-cyan, #22d3ee);
    text-decoration: none;
  }
  .arxiv-link:hover { text-decoration: underline; }

  /* ── section ── */
  .section {
    border-bottom: 1px solid var(--glass-border, rgba(255,255,255,0.05));
  }
  .section-header {
    display: flex;
    align-items: center;
    gap: 8px;
    width: 100%;
    background: none;
    border: none;
    cursor: pointer;
    padding: 10px 14px;
    color: var(--text-secondary, #a8a8c8);
    font-size: 12px;
    font-weight: 600;
    text-align: left;
    transition: background 0.15s ease;
  }
  .section-header:hover { background: rgba(255,255,255,0.03); }
  .citation-header:hover  { background: rgba(255,107,107,0.05); }
  .reference-header:hover { background: rgba(78,205,196,0.05); }

  .section-title { flex: 1; }
  .chevron { font-size: 10px; opacity: 0.6; }

  .section-dot {
    width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0;
  }
  .citation-dot  { background: #ff6b6b; box-shadow: 0 0 5px #ff6b6b66; }
  .reference-dot { background: #4ecdc4; box-shadow: 0 0 5px #4ecdc466; }

  /* ── paper list (inside a section) ── */
  .paper-list {
    padding: 4px 0;
  }

  .paper-item {
    display: flex;
    padding: 8px 14px 8px 10px;
    cursor: pointer;
    border-bottom: 1px solid rgba(255,255,255,0.03);
    transition: background 0.12s ease;
    gap: 8px;
  }
  .paper-item:hover { background: rgba(255,255,255,0.03); }
  .paper-item.focused {
    background: rgba(147,51,234,0.06);
    border-left: 2px solid var(--accent-purple, #9333ea);
  }

  .item-accent {
    width: 3px;
    border-radius: 3px;
    flex-shrink: 0;
    align-self: stretch;
  }
  .citation-accent  { background: linear-gradient(to bottom, #ff6b6b, rgba(255,107,107,0.2)); }
  .reference-accent { background: linear-gradient(to bottom, #4ecdc4, rgba(78,205,196,0.2)); }

  .item-body { flex: 1; min-width: 0; }

  .item-title {
    margin: 0 0 3px;
    font-size: 12px;
    line-height: 1.4;
    font-weight: 500;
    word-break: break-word;
  }
  .citation-title  { color: #ffa0a0; }
  .reference-title { color: #7ee8e3; }

  .item-meta {
    margin: 0 0 4px;
    font-size: 10px;
    color: var(--text-muted, #6b6b8d);
    font-style: italic;
  }

  .item-abstract {
    margin: 4px 0;
    font-size: 11px;
    color: var(--text-secondary, #a8a8c8);
    line-height: 1.4;
  }
  .item-abstract.full { color: var(--text-primary, #f0f0f8); }

  .item-actions {
    display: flex;
    gap: 6px;
    margin-top: 6px;
    flex-wrap: wrap;
  }

  .action-btn {
    background: rgba(147,51,234,0.12);
    border: 1px solid rgba(147,51,234,0.2);
    color: var(--text-secondary, #a8a8c8);
    border-radius: 999px;
    padding: 2px 10px;
    font-size: 10px;
    cursor: pointer;
    transition: all 0.12s ease;
  }
  .action-btn:hover {
    background: rgba(147,51,234,0.22);
    color: var(--text-primary, #f0f0f8);
  }

  .navigate-btn {
    background: rgba(255,107,107,0.15);
    border: 1px solid rgba(255,107,107,0.3);
    color: #ffa0a0;
    border-radius: 999px;
    padding: 2px 10px;
    font-size: 10px;
    cursor: pointer;
    transition: all 0.12s ease;
    font-weight: 600;
  }
  .navigate-btn:hover { background: rgba(255,107,107,0.25); color: #fff; }

  .reference-navigate {
    background: rgba(78,205,196,0.15);
    border-color: rgba(78,205,196,0.3);
    color: #7ee8e3;
  }
  .reference-navigate:hover { background: rgba(78,205,196,0.25); color: #fff; }

  /* ── nested section ── */
  .nested-section {
    margin-top: 6px;
    padding: 6px 8px;
    border-radius: 6px;
    background: rgba(0,0,0,0.2);
    border: 1px solid rgba(255,255,255,0.05);
  }
  .nested-label {
    margin: 4px 0 2px;
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
  .citation-label  { color: #ff6b6b; }
  .reference-label { color: #4ecdc4; }

  .nested-item {
    padding: 3px 4px;
    cursor: pointer;
    border-radius: 4px;
    transition: background 0.1s ease;
  }
  .nested-item:hover { background: rgba(147,51,234,0.1); }

  .nested-title {
    font-size: 11px;
    color: var(--text-secondary, #a8a8c8);
    line-height: 1.3;
  }
  .nested-empty { font-size: 11px; color: var(--text-muted, #6b6b8d); padding: 4px 0; margin: 0; }

  /* ── history ── */
  .history-list {
    padding: 4px 0;
  }
  .history-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 14px;
    border-bottom: 1px solid rgba(255,255,255,0.04);
  }
  .history-info { flex: 1; min-width: 0; }
  .history-title {
    margin: 0 0 2px;
    font-size: 11px;
    color: var(--text-secondary, #a8a8c8);
    font-weight: 500;
    line-height: 1.3;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .history-meta {
    margin: 0;
    font-size: 10px;
    color: var(--text-muted, #6b6b8d);
    font-style: italic;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .history-actions { display: flex; gap: 4px; flex-shrink: 0; }
  .history-nav-btn, .history-del-btn {
    background: none;
    border: 1px solid rgba(255,255,255,0.10);
    color: var(--text-muted, #6b6b8d);
    border-radius: 6px;
    width: 22px;
    height: 22px;
    cursor: pointer;
    font-size: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.12s ease;
  }
  .history-nav-btn:hover {
    background: rgba(34,211,238,0.15);
    color: var(--accent-cyan, #22d3ee);
    border-color: rgba(34,211,238,0.35);
  }
  .history-del-btn:hover {
    background: rgba(245,101,101,0.15);
    color: #f56565;
    border-color: rgba(245,101,101,0.35);
  }

  /* ── misc ── */
  .loading-row {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 12px 14px;
    color: var(--text-muted, #6b6b8d);
    font-size: 12px;
  }
  .loading-row.small { padding: 6px 0; font-size: 11px; }

  .mini-spinner {
    width: 14px;
    height: 14px;
    border: 2px solid rgba(147,51,234,0.2);
    border-top-color: var(--accent-cyan, #22d3ee);
    border-radius: 50%;
    animation: spin 0.7s linear infinite;
    flex-shrink: 0;
  }
  @keyframes spin { to { transform: rotate(360deg); } }

  .error-row {
    padding: 10px 14px;
    color: #f56565;
    font-size: 12px;
  }

  .empty-msg {
    padding: 8px 14px;
    font-size: 11px;
    color: var(--text-muted, #6b6b8d);
    margin: 0;
  }

  .dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    display: inline-block;
    flex-shrink: 0;
  }
</style>
