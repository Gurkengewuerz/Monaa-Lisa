<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import type { Paper } from '../testdata/dummyData';

  export let papers: Paper[];
  export let searchQuery: string = '';
  
  const dispatch = createEventDispatcher();

  $: filteredPapers = papers.filter(paper => 
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