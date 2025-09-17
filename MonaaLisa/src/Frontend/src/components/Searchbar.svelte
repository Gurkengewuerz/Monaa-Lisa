<script lang="ts">
  /**
   * Number of active nodes to display in the header.
   * @type {number}
   */
  export let activeNodes: number = 0;

  /**
   * Number of active edges to display in the header.
   * @type {number}
   */
  export let activeEdges: number = 0;
</script>

<div class="header">
  <h1 class="header-title">Monaa-Lisa - Academic Paper Visualization</h1>
  <div class="header-stats">
    <span class="stat">Active Nodes: {activeNodes}</span>
    <span class="stat">Active Edges: {activeEdges}</span>
  </div>
</div>

<style>
  .header {
    padding: 1rem;
    background-color: #2a2a35;
    border-bottom: 1px solid #3a3a45;
    display: flex;
    align-items: center;
    justify-content: space-between;
    z-index: 100;
  }

  .header-title {
    color: white;
    font-size: 18px;
    margin: 0;
    font-weight: bold;
  }

  .header-stats {
    display: flex;
    gap: 1rem;
  }

  .stat {
    color: #999;
    font-size: 14px;
  }
</style>