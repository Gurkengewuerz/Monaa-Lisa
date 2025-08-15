<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { dummyPapers, type Paper } from '../testdata/dummyData'; //temporary import for demo data; replace with api later

  /**
   * array of papers to search.
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
  export let useDummyData: boolean = false;

  export let searchQuery: string = '';
  
  const dispatch = createEventDispatcher();

  //determine data source: use dummypapers if flag is set, otherwise use papers prop
  //to use dummy data: set usedummydata={true} in parent component
  //to use real data: pass papers prop from api/db and set usedummydata={false}
  //later, replace dummypapers import with api call in parent
  $: dataSource = useDummyData ? dummyPapers : papers;

  $: filteredPapers = dataSource.filter(paper => 
    paper.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    paper.authors.toLowerCase().includes(searchQuery.toLowerCase()) ||
    paper.summary.toLowerCase().includes(searchQuery.toLowerCase())
  );

  $: dispatch('filtered', filteredPapers);
</script>

<div class="search-bar">
  <input 
    type="text" 
    placeholder="Search academic papers by title, author, or keywords..."
    bind:value={searchQuery}
    class="search-input"
  />
  <div class="search-results-count">
    {filteredPapers.length} papers found
  </div>
</div>

<style>
  .search-bar {
    padding: 1rem;
    background-color: #2a2a35;
    border-bottom: 1px solid #3a3a45;
    display: flex;
    align-items: center;
    gap: 1rem;
    z-index: 100;
  }

  .search-input {
    flex: 1;
    padding: 0.75rem 1rem;
    border: none;
    border-radius: 8px;
    background-color: #3a3a45;
    color: white;
    font-size: 14px;
    outline: none;
    transition: background-color 0.2s;
  }

  .search-input:focus {
    background-color: #4a4a55;
  }

  .search-input::placeholder {
    color: #999;
  }

  .search-results-count {
    color: #999;
    font-size: 14px;
    white-space: nowrap;
  }
</style>