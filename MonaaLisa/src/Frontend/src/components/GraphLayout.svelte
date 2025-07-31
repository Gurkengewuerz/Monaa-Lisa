<script lang="ts">
  import { dummyPapers, type Paper } from '../testdata/dummyData';
  import Graph from './Graph.svelte';
  import Searchbar from './Searchbar.svelte';
  import Sidebar from './Sidebar.svelte';

  let filteredPapers: Paper[] = dummyPapers; // Papers after search/filter applied
  let sidebarOpen = false; // Controls sidebar visibility
  let selectedPaperId: string | null = null; // Currently selected paper ID

  //handling search results from Searchbar component
  function handleFiltered(event: CustomEvent<Paper[]>) {
    filteredPapers = event.detail;
  }

  //toggle sidebar open/closed 
  function handleToggleSidebar() {
    sidebarOpen = !sidebarOpen;
  }

  //handling of paper selection from sidebar - update graph
  function handleSelectPaper(event: CustomEvent<Paper>) {
    const paper = event.detail;
    selectedPaperId = paper.id.toString();
    console.log('Selected paper from sidebar:', paper);
  }

  //handling for node selection from graph - update sidebar
  function handleNodeSelected(event: CustomEvent<string>) {
    selectedPaperId = event.detail;
    sidebarOpen = true; // Auto-open sidebar when node is selected
    console.log('Selected node from graph:', event.detail);
  }

  //handling node deselection from graph - clear sidebar selection
  function handleNodeDeselected() {
    selectedPaperId = null;
  }
</script>

<!-- main app container -->
<div class="app-container">
  <!-- search component at top -->
  <Searchbar 
    papers={dummyPapers} 
    on:filtered={handleFiltered}
  />

  <!-- main area containing graph and sidebar -->
  <div class="main-content">
    <!-- graph visualization component with selection binding -->
    <Graph 
      {selectedPaperId}
      on:nodeSelected={handleNodeSelected}
      on:nodeDeselected={handleNodeDeselected}
    />
    
    <!-- sidebar component for the paper listt -->
    <Sidebar 
      papers={filteredPapers}
      isOpen={sidebarOpen}
      {selectedPaperId}
      on:toggle={handleToggleSidebar}
      on:selectPaper={handleSelectPaper}
    />
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

  .main-content {
    flex: 1;
    position: relative;
    display: flex;
  }

  :global(.graph-container) {
    width: 100% !important;
    height: 100% !important;
  }
</style>