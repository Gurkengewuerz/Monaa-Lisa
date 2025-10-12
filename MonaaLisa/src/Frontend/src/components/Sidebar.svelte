<script lang="ts">
  import { createEventDispatcher, tick } from 'svelte';
  import { dummyPapers, type Paper } from '../testdata/dummyData'; //temporary import for demo data; replace with api later

  /**
   * array of papers to display.
   * passed from the parent.
   * @type {Paper[]}
   */
  export let papers: Paper[] = [];

  /**
   * flag to use dummy data for showcasing.
   * when true, uses dummypapers instead of the papers prop.
   * set to true for demo, false for real data.
   * @type {boolean}
   */
  export let useDummyData: boolean = true;

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

  //determine data source: use dummypapers if flag is set, otherwise use papers prop
  //to use dummy data: set usedummydata={true} in parent component
  //to use real data: pass papers prop from api/db and set usedummydata={false}
  //later, replace dummypapers import with api call in parent
  $: dataSource = useDummyData ? dummyPapers : papers;

  // UI state
  let query = '';
  let focusSelected = false; // if true, only the selected paper is shown
  let expandedCitations = new Set<number>(); // paper.id values with expanded citations
  let localSelected: Paper | null = null; // local selected for immediate display

  // *** BULLETPROOF REACTIVE - WAITS FOR DATA + DEBUG LOGS ***
  $: {
    console.log('SIDEBAR REACTIVE TRIGGERED:', { selectedPaperId, dataSourceLength: dataSource?.length });
    
    if (selectedPaperId && dataSource && dataSource.length > 0) {
      console.log('SEARCHING FOR PAPER:', selectedPaperId);
      const foundPaper = dataSource.find((p) => p.id.toString() === selectedPaperId);
      console.log('FOUND PAPER:', foundPaper?.title || 'NOT FOUND');
      
      localSelected = foundPaper || null;
      focusSelected = true;
      isOpen = true; // FORCE OPEN SIDEBAR
      
      tick().then(() => {
        console.log('SCROLLING TO PAPER:', selectedPaperId);
        const el = document.querySelector(`[data-paper-id="${selectedPaperId}"]`) as HTMLElement | null;
        console.log('SCROLL ELEMENT:', el);
        if (el) {
          el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
          el.classList.add('force-selected'); // TEMP VISUAL DEBUG
        }
      });
    } else {
      console.log('NO SELECTION');
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
      const inSummary = normalize(p.summary).includes(q);
      return inTitle || inAuthors || inSummary;
    });
  })();

  function sortSelectedFirst(list: Paper[]) {
    if (!localSelected) return list;
    const selId = localSelected.id;
    return list.slice().sort((a, b) => {
      if (a.id === selId && b.id !== selId) return -1;
      if (b.id === selId && a.id !== selId) return 1;
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

  function toggleCitations(paperId: number) {
    if (expandedCitations.has(paperId)) {
      expandedCitations.delete(paperId);
    } else {
      expandedCitations.add(paperId);
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
        `[data-paper-id="${paper.id}"]`
      ) as HTMLElement | null;
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    });
  }

  function selectCitedPaper(citedId: number) {
    const target = dataSource.find((p) => p.id === citedId);
    if (target) selectPaper(target);
  }

  //badges next to the papers in the sidebar
  //colors by cluster identifiers (falls back to grey when missing)
  //todo: remove when backend provides cluster colors or make dynamic
  const clusterColors: Record<string, string> = {
    A: '#CC6666',
    B: '#66B2B2',
    C: '#9966CC',
    D: '#CC66B2',
    E: '#6699CC',
    F: '#FF4500',
    G: '#00CED1',
  };
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
      {#each displayedPapers as paper (paper.id)}
        <div 
          class="paper-item" 
          class:selected={selectedPaperId === paper.id.toString()}
          class:force-selected={localSelected?.id === paper.id}
          data-paper-id={paper.id}
          on:click|stopPropagation={() => selectPaper(paper)}
        >
          <div class="paper-cluster" style="background-color: {clusterColors[paper.cluster] || '#999999'}">
            {paper.cluster}
          </div>
          <div class="paper-info">
            <h4>{paper.title}</h4>
            <p class="paper-authors">{paper.authors}</p>
            <p class="paper-summary">{paper.summary.substring(0, 100)}...</p>
            <div class="paper-meta">
              <button
                class="citations"
                on:click|stopPropagation={() => toggleCitations(paper.id)}
              >
                Citations ({paper.citations?.length ?? 0}) {expandedCitations.has(paper.id) ? '▾' : '▸'}
              </button>
              <span class="date">{new Date(paper.published).getFullYear()}</span>
            </div>

            {#if expandedCitations.has(paper.id) && (paper.citations?.length ?? 0) > 0}
              <div class="cited-papers">
                {#each paper.citations as citedId}
                  {@const citedPaper = dataSource.find((p) => p.id === citedId)}
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
    background-color: #4a9eff;
    border: none;
    border-radius: 50% 0 0 50%;
    width: 40px;
    height: 60px;
    color: white;
    cursor: pointer;
    z-index: 200;
    transition: all 0.3s ease;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .sidebar-toggle:hover {
    background-color: #357abd;
  }

  .sidebar-toggle.open {
    right: 350px;
    border-radius: 0 50% 50% 0;
  }

  .toggle-icon {
    font-size: 18px;
    font-weight: bold;
  }

  .sidebar {
    position: absolute;
    right: -370px;
    top: 0;
    width: 370px;
    height: 100%;
    background-color: #2a2a35;
    border-left: 1px solid #3a3a45;
    transition: right 0.3s ease;
    z-index: 150;
    display: flex;
    flex-direction: column;
  }

  .sidebar.open {
    right: 0;
  }

  .sidebar-header {
    padding: 1rem;
    border-bottom: 1px solid #3a3a45;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .sidebar-header h3 {
    margin: 0;
    color: white;
    font-size: 18px;
  }

  .close-btn {
    background: none;
    border: none;
    color: #999;
    font-size: 24px;
    cursor: pointer;
    padding: 0;
    width: 30px;
    height: 30px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .close-btn:hover {
    color: white;
  }

  .sidebar-tools {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 0.75rem;
    border-bottom: 1px solid #3a3a45;
    flex-wrap: nowrap; /* Prevents the button from wrapping underneath the search bar */
  }

  .search {
    flex: 1;
    position: relative;
  }

  .search input {
    width: 100%;
    max-width: 200px; /* Limits the search bar width to prevent it from getting too big */
    padding: 0.5rem 2rem 0.5rem 0.5rem;
    border: 1px solid #3a3a45;
    border-radius: 4px;
    background: #1f1f29;
    color: #e6e6e6;
    outline: none;
  }

  .search .clear {
    position: absolute;
    right: 4px;
    top: 50%;
    transform: translateY(-50%);
    background: none;
    border: none;
    color: #bbb;
    cursor: pointer;
    padding: 0 6px;
    height: 100%;
  }

  .show-all {
    flex-shrink: 0; /* Prevents the button from shrinking and getting cut off */
    background: #44495d;
    color: #e6e6e6;
    border: 1px solid #3a3a45;
    border-radius: 4px;
    padding: 0.45rem 0.6rem;
    cursor: pointer;
    white-space: nowrap;
  }

  .show-all:hover {
    background: #50566e;
  }

  .sidebar-content {
    flex: 1;
    overflow-y: auto;
    padding: 0;
  }

  .empty {
    color: #bbb;
    padding: 1rem;
    font-size: 14px;
  }

  .paper-item {
    padding: 1rem;
    border-bottom: 1px solid #3a3a45;
    cursor: pointer;
    transition: background-color 0.2s;
    display: flex;
    gap: 0.75rem;
  }

  .paper-item:hover {
    background-color: #3a3a45;
  }

  .paper-item.selected {
    background-color: #4a9eff20;
    border-left: 3px solid #4a9eff;
  }

  /* *** TEMP DEBUG STYLE *** */
  .paper-item.force-selected {
    background-color: #ff000020 !important;
    border-left: 5px solid #ff0000 !important;
    animation: pulse 1s infinite;
  }

  @keyframes pulse {
    0% { border-left-color: #ff0000; }
    50% { border-left-color: #ffff00; }
    100% { border-left-color: #ff0000; }
  }

  .paper-cluster {
    width: 30px;
    height: 30px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-weight: bold;
    font-size: 12px;
    flex-shrink: 0;
  }

  .paper-info {
    flex: 1;
    min-width: 0;
  }

  .paper-info h4 {
    margin: 0 0 0.5rem 0;
    font-size: 14px;
    color: white;
    line-height: 1.3;
    word-wrap: break-word;
  }

  .paper-authors {
    margin: 0 0 0.5rem 0;
    font-size: 12px;
    color: #999;
    font-style: italic;
  }

  .paper-summary {
    margin: 0 0 0.5rem 0;
    font-size: 12px;
    color: #ccc;
    line-height: 1.4;
  }

  .paper-meta {
    display: flex;
    justify-content: space-between;
    font-size: 11px;
    color: #999;
  }

  .citations {
    cursor: pointer;
    color: #4a9eff;
    background: none;
    border: none;
    padding: 0;
    text-decoration: underline;
  }

  .cited-papers {
    margin-top: 0.5rem;
    padding-left: 0.75rem;
    border-left: 2px solid #4a9eff;
  }

  .cited-paper-item {
    padding: 0.5rem;
    background-color: #3a3a45;
    margin-bottom: 0.25rem;
    border-radius: 4px;
    cursor: pointer;
  }

  .cited-paper-item:hover {
    background-color: #4a4a55;
  }

  .cited-paper-item h5 {
    margin: 0 0 0.15rem 0;
    font-size: 12px;
    color: white;
  }

  .cited-paper-item p {
    margin: 0;
    font-size: 10px;
    color: #ccc;
  }
</style>