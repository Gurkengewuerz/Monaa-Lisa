<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { fade } from 'svelte/transition';
  import { spring } from 'svelte/motion';

  const dispatch = createEventDispatcher();

  let scrollY = 0;
  let innerHeight = 1000;

  // Scroll progress: 0 to 1
  $: rawProgress = innerHeight ? scrollY / (innerHeight * 2) : 0;

  const smoothProgress = spring(0, {
    stiffness: 0.02,
    damping: 0.9
  });

  $: smoothProgress.set(rawProgress);

  $: progress = $smoothProgress;

  // 1. Hero Section
  $: heroOpacity = Math.max(0, 1 - progress * 4);
  
  // 2. Background Image
  $: bgScale = 1.2 - (progress * 0.2);
  
  // 3. Transition Title "Monaa-Lisa"
  // We want an exponential zoom for linear visual speed.
  // Range: progress 0.1 to 0.8
  const zoomStart = 0.1;
  const zoomEnd = 0.8;
  $: zoomT = Math.min(1, Math.max(0, (progress - zoomStart) / (zoomEnd - zoomStart)));
  
  // Scale: 3000 -> 1 exponentially
  $: titleScale = 3000 * Math.pow(1 / 3000, zoomT);
  
  // Opacity: Starts transparent (0), fades to white (1)
  // User wants it faster/earlier.
  // Start fading in slightly before the zoom finishes (at 0.75) and finish by 0.8
  $: titleOpacity = Math.min(1, Math.max(0, (progress - 0.75) * 20));

  // 4. Subtitle
  $: subtitleOpacity = Math.max(0, (progress - 0.7) * 5);

  export function reset() {
    window.scrollTo({ top: 0, behavior: 'instant' });
    smoothProgress.set(0, { hard: true });
  }

  function start() {
    dispatch('start');
  }
</script>

<svelte:window bind:scrollY bind:innerHeight />

<div class="landing-page">
  <div class="sticky-wrapper">
      <!-- Background Image Layer -->
      <div class="background" style="transform: scale({bgScale})">
           <div class="art-placeholder"></div>
      </div>

      <!-- Hero Section -->
      <div class="hero" style="opacity: {heroOpacity}; pointer-events: {heroOpacity < 0.1 ? 'none' : 'auto'}">
          <h1 class="hero-title">Monaa-Lisa</h1>
          <button class="start-btn" on:click={start}>START</button>
          <p class="hero-subtitle">Visualize academia interactively</p>
      </div>

      <!-- Second Section (Zoomed out view) -->
      <!-- 
        We use an SVG mask to create the "Hole" effect.
        The SVG scales from 100 -> 1.
        The Rect is solid dark blue.
        The Text in the mask creates a hole.
        The Text Fill fades in to white.
      -->
      <div class="second-section" style="transform: scale({titleScale}) translateZ(0)">
           <svg class="overlay-svg" viewBox="0 0 100 50" preserveAspectRatio="xMidYMid slice">
              <defs>
                 <mask id="text-mask">
                    <rect x="0" y="0" width="100%" height="100%" fill="white" />
                    <text x="50%" y="50%" text-anchor="middle" dominant-baseline="middle" font-size="12" font-weight="900" fill="black">Monaa-Lisa</text>
                 </mask>
              </defs>
              <!-- The Solid Background with Hole -->
              <rect x="0" y="0" width="100%" height="100%" fill="#1a1f2c" mask="url(#text-mask)" />
              
              <!-- The White Text Fill -->
              <text x="50%" y="50%" text-anchor="middle" dominant-baseline="middle" font-size="12" font-weight="900" fill="white" opacity={titleOpacity}>Monaa-Lisa</text>
           </svg>
      </div>
      
      <!-- Subtitle is separate, fades in at the end -->
      <div class="subtitle-container" style="opacity: {subtitleOpacity}">
          <h2 class="sub-title">Graph visualization software</h2>
      </div>
  </div>
  
  <!-- Scroll Track -->
  <div class="scroll-track"></div>
</div>

<style>
  .landing-page {
    position: relative;
    width: 100%;
    background: #000;
    color: #fff;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
    z-index: 9999;
  }

  .scroll-track {
    height: 300vh;
  }

  .sticky-wrapper {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100vh;
    overflow: hidden;
    display: flex;
    justify-content: center;
    align-items: center;
  }

  .background {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    z-index: 0;
    transition: transform 0.1s linear;
    will-change: transform;
  }

  .art-placeholder {
    width: 100%;
    height: 100%;
    background: radial-gradient(circle at center, #2b1055, #7597de);
    background-image: url('https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?q=80&w=2564&auto=format&fit=crop');
    background-size: cover;
    background-position: center;
    filter: brightness(0.6);
  }

  .hero {
    position: absolute;
    z-index: 10;
    width: 100%;
    height: 100%;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    text-align: center;
    transition: opacity 0.1s linear;
  }

  .hero-title {
    font-size: 8rem;
    margin: 0;
    text-transform: uppercase;
    letter-spacing: 10px;
    font-weight: 900;
    text-shadow: 0 0 20px rgba(0,0,0,0.5);
  }

  .start-btn {
    margin-top: 40px;
    padding: 15px 50px;
    font-size: 1.5rem;
    background: rgba(255, 255, 255, 0.1);
    border: 2px solid #fff;
    color: #fff;
    cursor: pointer;
    text-transform: uppercase;
    letter-spacing: 2px;
    transition: all 0.3s ease;
    backdrop-filter: blur(5px);
  }

  .start-btn:hover {
    background: #fff;
    color: #000;
    transform: scale(1.05);
  }

  .hero-subtitle {
    position: absolute;
    bottom: 40px;
    font-size: 1.2rem;
    letter-spacing: 4px;
    text-transform: uppercase;
    opacity: 0.8;
    text-shadow: 0 0 10px rgba(0,0,0,0.5);
  }

  .second-section {
    position: absolute;
    z-index: 20;
    width: 100%;
    height: 100%;
    display: flex;
    justify-content: center;
    align-items: center;
    pointer-events: none;
    will-change: transform;
  }

  .overlay-svg {
    width: 100vw;
    height: 100vh;
    /* Ensure text is crisp */
    shape-rendering: geometricPrecision;
    text-rendering: geometricPrecision;
  }
  
  .overlay-svg text {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
    text-transform: uppercase;
  }

  .subtitle-container {
    position: absolute;
    z-index: 30;
    top: 60%; /* Position below the title */
    width: 100%;
    text-align: center;
    pointer-events: none;
  }

  .sub-title {
    font-size: 2rem;
    font-weight: 300;
    letter-spacing: 5px;
    text-transform: uppercase;
    text-shadow: 0 0 10px rgba(0,0,0,0.8);
  }

  @media (max-width: 768px) {
    .hero-title {
      font-size: 4rem;
    }
    .hero-subtitle {
      bottom: 20px;
      font-size: 0.9rem;
    }
  }
</style>
