<script lang="ts">
  import { fade } from 'svelte/transition';
</script>

<div class="loading-screen" out:fade={{ duration: 800 }}>
  <div class="logo-container">
    <div class="loading-logo">M-L</div>
  </div>
</div>

<style>
  .loading-screen {
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    background-color: #1a1f2c; /* Dark-blueish gray from LandingPage */
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 10000; /* High z-index to be on top */
  }

  .loading-logo {
    font-size: 48px;
    font-weight: bold;
    letter-spacing: 4px;
    border: 4px solid #fff;
    padding: 10px 20px;
    background: transparent;
    color: #fff;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
    animation: glow 2s ease-in-out infinite;
  }

  @keyframes glow {
    0% {
      filter: drop-shadow(0 0 5px rgba(0, 191, 255, 0.6)); /* Blue */
    }
    50% {
      filter: drop-shadow(0 0 25px rgba(138, 43, 226, 0.9)); /* Purple */
    }
    100% {
      filter: drop-shadow(0 0 5px rgba(255, 105, 180, 0.6)); /* Pink */
    }
  }
</style>
