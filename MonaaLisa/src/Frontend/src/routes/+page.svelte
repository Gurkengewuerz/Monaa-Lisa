<script lang="ts">
  import GraphLayout from '../components/GraphLayout.svelte';
  import LandingPage from '../components/LandingPage.svelte';
  import { fade } from 'svelte/transition';

  let showLanding = true;
  let landingPage: LandingPage;

  function handleStart() {
    showLanding = false;
  }

  function handleReset() {
    if (showLanding && landingPage) {
      landingPage.reset();
    } else {
      showLanding = true;
      if (typeof window !== 'undefined') {
        window.scrollTo({ top: 0, behavior: 'instant' });
      }
    }
  }
</script>

<button class="logo-btn" on:click={handleReset}>M-L</button>

{#if !showLanding}
  <main in:fade>
    <GraphLayout />
  </main>
{:else}
  <LandingPage bind:this={landingPage} on:start={handleStart} />
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

  .logo-btn {
    position: fixed;
    top: 40px;
    left: 40px;
    z-index: 10000;
    font-size: 24px;
    font-weight: bold;
    letter-spacing: 2px;
    border: 2px solid #fff;
    padding: 5px 10px;
    background: transparent;
    color: #fff;
    cursor: pointer;
    transition: all 0.3s ease;
    font-family: inherit;
  }

  .logo-btn:hover {
    background: #fff;
    color: #000;
  }

  @media (max-width: 768px) {
    .logo-btn {
      top: 20px;
      left: 20px;
    }
  }
</style>