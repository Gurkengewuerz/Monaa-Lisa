<script lang="ts">
  import { createEventDispatcher, tick } from 'svelte';
  import type { Paper } from '$lib/types/paper';
  import { getClusterColor } from '../utils/clusterColors';

  /**
   * array of papers to display.
   * passed from the parent.
   * @type {Paper[]}
   */
  export let papers: Paper[] = [];

  /**
   * control for sidebar visibility.
   * @type {boolean}
   */
  export let isOpen: boolean = false;

  /**
   * currently selected paper id.
   * @type {string | null}
   */
  export let selectedPaperId: string | null = null;

  const dispatch = createEventDispatcher();

  $: dataSource = papers;

  // UI state
  let query = '';
  let focusSelected = false; // if true, only the selected paper is shown
  let expandedCitations = new Set<string>();
  let localSelected: Paper | null = null; // local selected for immediate display

  // *** BULLETPROOF REACTIVE - WAITS FOR DATA ***
  $: {
    if (selectedPaperId && dataSource && dataSource.length > 0) {
      const foundPaper = dataSource.find((p) => p.entry_id === selectedPaperId);
      
      localSelected = foundPaper || null;
      focusSelected = true;
      isOpen = true; // FORCE OPEN SIDEBAR
      
      tick().then(() => {
        const el = document.querySelector(`[data-paper-id="${selectedPaperId}"]`) as HTMLElement | null;
        if (el) {
          el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
      });
    } else {
      localSelected = null;
      focusSelected = false;
    }
  }

  // Search/filter
  function normalize(s: string | undefined | null) {
    return (s ?? '').toLowerCase();
  }

  $: filteredList = (() => {
    const q = normalize(query).trim();
    if (!q) return dataSource;
    return dataSource.filter((p) => {
      const inTitle = normalize(p.title).includes(q);
      const inAuthors = normalize(p.authors).includes(q);
      const inSummary = normalize(p.abstract).includes(q);
      return inTitle || inAuthors || inSummary;
    });
  })();

  function sortSelectedFirst(list: Paper[]) {
    if (!localSelected) return list;
    const selId = localSelected.entry_id;
    return list.slice().sort((a, b) => {
      if (a.entry_id === selId && b.entry_id !== selId) return -1;
      if (b.entry_id === selId && a.entry_id !== selId) return 1;
      return 0;
    });
  }

  // Displayed list:
  // - If focusing selected, show only that one (on any selection)
  // - Else show filtered list, with selected (if any) at top
  $: displayedPapers =
    focusSelected && localSelected ? [localSelected] : sortSelectedFirst(filteredList);

  // Handlers
  function onSearchInput(e: Event) {
    const val = (e.currentTarget as HTMLInputElement).value;
    query = val;
    if (val.trim()) {
      // Searching shows relevant papers; do not force single-selected view
      focusSelected = false;
    }
  }

  function clearSearch() {
    query = '';
  }

  function showAll() {
    focusSelected = false;
    localSelected = null;
  }

  function toggleSidebar() {
    dispatch('toggle');
  }

  function toggleCitations(paperEntryId: string) {
    if (expandedCitations.has(paperEntryId)) {
      expandedCitations.delete(paperEntryId);
    } else {
      expandedCitations.add(paperEntryId);
    }
    expandedCitations = new Set(expandedCitations); // trigger reactivity
  }

  function selectPaper(paper: Paper) {
    // Selecting a paper focuses it and collapses view to that paper
    localSelected = paper;
    focusSelected = true;
    query = '';
    dispatch('selectPaper', paper);
    // Scroll to the selected paper
    tick().then(() => {
      const el = document.querySelector(
        `[data-paper-id="${paper.entry_id}"]`
      ) as HTMLElement | null;
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    });
  }

  function selectCitedPaper(citedId: string) {
    const target = dataSource.find((p) => p.entry_id === citedId);
    if (target) selectPaper(target);
  }

  //badges next to the papers in the sidebar
  //colors by cluster identifiers (falls back to grey when missing)
  //todo: remove when backend provides cluster colors or make dynamic

  /** Extract the first (primary) category from a space/comma-separated categories string */
  function getFirstCategory(categories: string | null | undefined): string {
    if (!categories) return 'N/A';
    // categories may be "cs.AI cs.LG math.OC" (space-sep) or "cs.AI,cs.LG" (comma-sep)
    return categories.trim().split(/[\s,]+/)[0] ?? categories;
  }

  /** Short badge label: show the part after the last dot (e.g. "AI") or the full code if short */
  function badgeLabel(categories: string | null | undefined): string {
    const cat = getFirstCategory(categories);
    const parts = cat.split('.');
    if (parts.length > 1) return parts[parts.length - 1].toUpperCase().slice(0, 4);
    return cat.slice(0, 5).toUpperCase();
  }
</script>

<!-- sidebar toggle button -->
<button class="sidebar-toggle" class:open={isOpen} on:click={toggleSidebar}>
  <span class="toggle-icon">{isOpen ? '→' : '←'}</span>
</button>

<!-- expandable sidebar -->
<div class="sidebar" class:open={isOpen}>
  <div class="sidebar-header">
    <h3>Academic Papers</h3>
    <button class="close-btn" on:click={toggleSidebar}>×</button>
  </div>

  <div class="sidebar-tools">
    <div class="search">
      <input
        type="text"
        placeholder="Search title or authors..."
        value={query}
        on:input={onSearchInput}
      />
      {#if query}
        <button class="clear" on:click={clearSearch}>✕</button>
      {/if}
    </div>

    {#if focusSelected || query}
      <button class="show-all" on:click={showAll}>Show all</button>
    {/if}
  </div>
  
  <div class="sidebar-content" on:click={() => dispatch('deselect')}>
    {#if displayedPapers.length === 0}
      <div class="empty">No papers found.</div>
    {:else}
      {#each displayedPapers as paper (paper.entry_id)}
        <div 
          class="paper-item" 
          class:selected={selectedPaperId === paper.entry_id}
          data-paper-id={paper.entry_id}
          on:click|stopPropagation={() => selectPaper(paper)}
        >
          <div 
            class="paper-cluster" 
            style="background-color: {getClusterColor(paper.categories, paper.cluster)}"
            title={paper.categories ?? ''}
          >
            {badgeLabel(paper.categories)}
          </div>
          <div class="paper-info">
            <h4>{paper.title}</h4>
            <p class="paper-authors">{paper.authors}</p>
            <p class="paper-summary">
              {paper.abstract.length > 100
                ? `${paper.abstract.substring(0, 100)}...`
                : paper.abstract}
            </p>
            <div class="paper-meta">
              <button
                class="citations"
                on:click|stopPropagation={() => toggleCitations(paper.entry_id)}
              >
                Citations ({paper.citations?.length ?? 0}) {expandedCitations.has(paper.entry_id) ? '▾' : '▸'}
              </button>
              <span class="date">{paper.published ? new Date(paper.published).getFullYear() : '—'}</span>
            </div>

            {#if expandedCitations.has(paper.entry_id) && (paper.citations?.length ?? 0) > 0}
              <div class="cited-papers">
                {#each paper.citations as citedId}
                  {@const citedPaper = dataSource.find((p) => p.entry_id === citedId)}
                  {#if citedPaper}
                    <div 
                      class="cited-paper-item" 
                      on:click|stopPropagation={() => selectCitedPaper(citedId)}
                    >
                      <h5>{citedPaper.title}</h5>
                      <p>{citedPaper.authors}</p>
                    </div>
                  {/if}
                {/each}
              </div>
            {/if}
          </div>
        </div>
      {/each}
    {/if}
  </div>
</div>

<style>
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
    right: 360px;
    border-radius: 0 50% 50% 0;
  }

  .toggle-icon {
    font-size: 16px;
    font-weight: bold;
  }

  .sidebar {
    position: absolute;
    right: -380px;
    top: 0;
    width: 370px;
    height: 100%;
    background: var(--bg-secondary, #141530);
    border-left: 1px solid var(--glass-border, rgba(255,255,255,0.08));
    transition: right 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    z-index: 150;
    display: flex;
    flex-direction: column;
    backdrop-filter: blur(20px);
  }

  .sidebar.open {
    right: 0;
  }

  .sidebar-header {
    padding: 14px 16px;
    border-bottom: 1px solid var(--glass-border, rgba(255,255,255,0.08));
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: linear-gradient(180deg, rgba(147,51,234,0.06), transparent);
  }

  .sidebar-header h3 {
    margin: 0;
    color: var(--text-primary, #f0f0f8);
    font-size: 16px;
    font-weight: 600;
    letter-spacing: 0.3px;
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
    border-radius: var(--radius-sm, 8px);
    transition: all var(--transition-fast, 0.15s ease);
  }

  .close-btn:hover {
    color: var(--text-primary, #f0f0f8);
    background: rgba(147, 51, 234, 0.15);
  }

  .sidebar-tools {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 0.75rem;
    border-bottom: 1px solid var(--glass-border, rgba(255,255,255,0.08));
    flex-wrap: nowrap;
  }

  .search {
    flex: 1;
    position: relative;
  }

  .search input {
    width: 100%;
    max-width: 200px;
    padding: 0.45rem 2rem 0.45rem 0.6rem;
    border: 1px solid var(--border-subtle, rgba(147,51,234,0.18));
    border-radius: var(--radius-sm, 8px);
    background: rgba(15, 16, 32, 0.6);
    color: var(--text-primary, #f0f0f8);
    outline: none;
    font-size: 13px;
    transition: border-color var(--transition-fast, 0.15s ease);
  }

  .search input:focus {
    border-color: rgba(147, 51, 234, 0.45);
    box-shadow: 0 0 10px rgba(147, 51, 234, 0.15);
  }

  .search input::placeholder {
    color: var(--text-muted, #6b6b8d);
  }

  .search .clear {
    position: absolute;
    right: 4px;
    top: 50%;
    transform: translateY(-50%);
    background: none;
    border: none;
    color: var(--text-muted, #6b6b8d);
    cursor: pointer;
    padding: 0 6px;
    height: 100%;
    transition: color var(--transition-fast, 0.15s ease);
  }

  .search .clear:hover {
    color: var(--accent-magenta, #e839a0);
  }

  .show-all {
    flex-shrink: 0;
    background: rgba(147, 51, 234, 0.12);
    color: var(--text-primary, #f0f0f8);
    border: 1px solid var(--border-subtle, rgba(147,51,234,0.18));
    border-radius: var(--radius-sm, 8px);
    padding: 0.4rem 0.6rem;
    cursor: pointer;
    white-space: nowrap;
    font-size: 12px;
    transition: all var(--transition-fast, 0.15s ease);
  }

  .show-all:hover {
    background: rgba(147, 51, 234, 0.22);
    border-color: rgba(147, 51, 234, 0.35);
  }

  .sidebar-content {
    flex: 1;
    overflow-y: auto;
    padding: 0;
  }

  .empty {
    color: var(--text-muted, #6b6b8d);
    padding: 1.5rem;
    font-size: 13px;
    text-align: center;
  }

  .paper-item {
    padding: 12px 14px;
    border-bottom: 1px solid var(--glass-border, rgba(255,255,255,0.06));
    cursor: pointer;
    transition: all var(--transition-fast, 0.15s ease);
    display: flex;
    gap: 0.75rem;
  }

  .paper-item:hover {
    background: rgba(147, 51, 234, 0.08);
  }

  .paper-item.selected {
    background: rgba(147, 51, 234, 0.12);
    border-left: 3px solid var(--accent-purple, #9333ea);
    box-shadow: inset 4px 0 15px rgba(147, 51, 234, 0.1);
  }

  .paper-cluster {
    width: 28px;
    height: 28px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-weight: bold;
    font-size: 11px;
    flex-shrink: 0;
    box-shadow: 0 0 8px rgba(0,0,0,0.3);
  }

  .paper-info {
    flex: 1;
    min-width: 0;
  }

  .paper-info h4 {
    margin: 0 0 0.4rem 0;
    font-size: 13px;
    color: var(--text-primary, #f0f0f8);
    line-height: 1.3;
    word-wrap: break-word;
    font-weight: 500;
  }

  .paper-authors {
    margin: 0 0 0.4rem 0;
    font-size: 11px;
    color: var(--text-muted, #6b6b8d);
    font-style: italic;
  }

  .paper-summary {
    margin: 0 0 0.4rem 0;
    font-size: 11px;
    color: var(--text-secondary, #a8a8c8);
    line-height: 1.4;
  }

  .paper-meta {
    display: flex;
    justify-content: space-between;
    font-size: 11px;
    color: var(--text-muted, #6b6b8d);
  }

  .citations {
    cursor: pointer;
    color: var(--accent-cyan, #22d3ee);
    background: none;
    border: none;
    padding: 0;
    font-size: 11px;
    transition: color var(--transition-fast, 0.15s ease);
  }

  .citations:hover {
    color: var(--accent-magenta, #e839a0);
  }

  .cited-papers {
    margin-top: 0.5rem;
    padding-left: 0.75rem;
    border-left: 2px solid var(--accent-purple, #9333ea);
  }

  .cited-paper-item {
    padding: 0.4rem 0.5rem;
    background: rgba(147, 51, 234, 0.08);
    margin-bottom: 0.25rem;
    border-radius: var(--radius-sm, 8px);
    cursor: pointer;
    transition: all var(--transition-fast, 0.15s ease);
  }

  .cited-paper-item:hover {
    background: rgba(147, 51, 234, 0.16);
  }

  .cited-paper-item h5 {
    margin: 0 0 0.15rem 0;
    font-size: 11px;
    color: var(--text-primary, #f0f0f8);
  }

  .cited-paper-item p {
    margin: 0;
    font-size: 10px;
    color: var(--text-secondary, #a8a8c8);
  }
</style>