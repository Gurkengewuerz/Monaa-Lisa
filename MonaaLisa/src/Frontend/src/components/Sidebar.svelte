<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { dummyPapers, type Paper } from '../testdata/dummyData'; //temporary import for demo data; replace with api later

  //prop components
  /**
   * array of papers to display.
   * passed from parent.
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

  //toggle so parent can open/close sidebar
  function toggleSidebar() {
    dispatch('toggle');
  }

  //notify parent of selected paper so it can sync the selection state
  function selectPaper(paper: Paper) {
    dispatch('selectPaper', paper);
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
  
  <div class="sidebar-content">
    {#each dataSource as paper}
      <div 
        class="paper-item" 
        class:selected={selectedPaperId === paper.id.toString()}
        on:click={() => selectPaper(paper)}
      >
        <div class="paper-cluster" style="background-color: {clusterColors[paper.cluster] || '#999999'}">
          {paper.cluster}
        </div>
        <div class="paper-info">
          <h4>{paper.title}</h4>
          <p class="paper-authors">{paper.authors}</p>
          <p class="paper-summary">{paper.summary.substring(0, 100)}...</p>
          <div class="paper-meta">
            <span class="citations">{paper.citations.length} citations</span>
            <span class="date">{new Date(paper.published).getFullYear()}</span>
          </div>
        </div>
      </div>
    {/each}
  </div>
</div>

<style>
  .sidebar-toggle {
    position: absolute;
    right: 20px;
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

  .sidebar-content {
    flex: 1;
    overflow-y: auto;
    padding: 0;
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
</style>