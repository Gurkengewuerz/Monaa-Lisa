<script lang="ts">
  import GraphLayout from '../components/GraphLayout.svelte';
  import LandingPage from '../components/LandingPage.svelte';
  import { fade } from 'svelte/transition';

  let showLanding = true;

  function handleStart() {
    showLanding = false;
  }
</script>

{#if !showLanding}
  <main in:fade>
    <GraphLayout />
  </main>
{:else}
  <LandingPage on:start={handleStart} />
{/if}

<style>
  :global(body) {
    margin: 0;
    padding: 0;
    background: #000;
    color: #fff;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
    overflow-x: hidden;
  }

  main {
    width: 100vw;
    height: 100vh;
  }
</style>