<script lang="ts">
  import { onMount } from 'svelte';
  import { dummyPapers, type Paper } from '../testdata/dummyData'; //temporary import for demo data; replace with api later
  import Graph from './Graph.svelte';
  import Searchbar from './Searchbar.svelte';
  import Sidebar from './Sidebar.svelte';

  //flag to use dummy data for showcasing
  //set to true for demo, false for real data
  let useDummyData: boolean = true; //change to false when backend is ready

  let papers: Paper[] = []; //real papers from api
  let filteredPapers: Paper[] = []; //papers after search/filter applied
  let sidebarOpen = false; //controls sidebar visibility
  let selectedPaperId: string | null = null; //currently selected paper id

  // Fetch real data from api when not using dummy
  onMount(async () => {
    if (!useDummyData) {
      try {
        const response = await fetch('http://localhost:8000/papers'); //your api url
        papers = await response.json();
        filteredPapers = papers;
      } catch (error) {
        console.error('failed to fetch papers:', error);
        // Fallback to dummy if api fails
        papers = dummyPapers;
        filteredPapers = dummyPapers;
      }
    } else {
      // Use dummy data
      papers = dummyPapers;
      filteredPapers = dummyPapers;
    }
  });

  //handling search results from searchbar component
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
    console.log('selected paper from sidebar:', paper);
  }

  //handling for node selection from graph - update sidebar
  function handleNodeSelected(event: CustomEvent<string>) {
    selectedPaperId = event.detail;
    sidebarOpen = true; //auto-open sidebar when node is selected
    console.log('selected node from graph:', event.detail);
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
    {papers}
    {useDummyData}
    on:filtered={handleFiltered}
  />

  <!-- main area containing graph and sidebar -->
  <div class="main-content">
    <!-- graph visualization component with selection binding -->
    <Graph 
      {papers}
      {useDummyData}
      {selectedPaperId}
      on:nodeSelected={handleNodeSelected}
      on:nodeDeselected={handleNodeDeselected}
    />
    
    <!-- sidebar component for the paper list -->
    <Sidebar 
      papers={filteredPapers}
      {useDummyData}
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