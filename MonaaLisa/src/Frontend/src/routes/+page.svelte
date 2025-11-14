<script lang="ts">
  import GraphLayout from '../components/GraphLayout.svelte';
</script>

<main>
  <GraphLayout />
</main>

<style>
  :global(body) {
    margin: 0;
    padding: 0;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
  }

  main {
    width: 100vw;
    height: 100vh;
  }
</style>