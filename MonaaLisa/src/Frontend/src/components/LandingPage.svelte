<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { fade } from 'svelte/transition';
  import { spring } from 'svelte/motion';
  import arxivLogo from '../assets/arxiv_logo.png';
  import monaaLisaLogo from '../assets/monaa_lisa_logo.png';
  import mlbg from '../assets/mlbg.png';
  import webmVideo from '../assets/ML_LOOP_main.webm';
  import mp4Video from '../assets/ML_LOOP_fallback.mp4';

  const dispatch = createEventDispatcher();

  let scrollY = 0;
  let innerHeight = 1000;

  // aScroll progress: 0 to 1
  $: rawProgress = innerHeight ? scrollY / (innerHeight * 4) : 0;

  const smoothProgress = spring(0, {
    stiffness: 0.02,
    damping: 0.9
  });

  $: smoothProgress.set(rawProgress);

  $: progress = $smoothProgress;

  // 1. Hero Section
  $: heroOpacity = Math.max(0, 1 - progress * 10);
  
  // 2. Background Image
  $: bgScale = 1.2 - (progress * 0.2);
  
  // 3. Transition Title "Monaa-Lisa"
  // We want an exponential zoom for linear visual speed.
  // Range: progress 0.1 to 0.4
  const zoomStart = 0.1;
  const zoomEnd = 0.4;
  $: zoomT = Math.min(1, Math.max(0, (progress - zoomStart) / (zoomEnd - zoomStart)));
  
  // Scale: 3000 -> 1 exponentially
  $: titleScale = 3000 * Math.pow(1 / 3000, zoomT);
  
  // OPTIMIZATION: Use SVG ViewBox instead of CSS transform: scale()
  // This prevents the browser from creating a massive texture layer (3000x screen size).
  
  // ADJUSTMENT: Center point for the zoom (0-100)
  // We keep the camera centered in the middle of our viewport (50x25)
  // And instead, moving the TEXT below to align the letter with this center.
  const focusX = 50; 
  const focusY = 25;

  $: vbW = 100 / titleScale;
  $: vbH = 50 / titleScale;
  $: vbX = focusX - vbW / 2;
  $: vbY = focusY - vbH / 2;

  // Title X Position: 
  // 50 = Center
  // 49.2 = Move Text slightly Left (so camera hits the letter to the Right of the gap)
  // Logic: 
  // If at 50 it hits the gap between "aa", the second 'a' is to the right.
  // We move the text LEFT (smaller X) to bring that 'a' into the center camera view.
  const titleX = 49.2; 
  
  // Opacity: Starts transparent (0), fades to white (1)
  // User wants it faster/earlier.
  // Start fading in slightly before the zoom finishes (at 0.35) and finish by 0.4
  $: titleOpacity = Math.min(1, Math.max(0, (progress - 0.35) * 20));

  // 4. Subtitle
  $: subtitleOpacity = Math.min(1, Math.max(0, (progress - 0.4) * 10));

  // Move title up
  $: titleY = 50 - (subtitleOpacity * 20);
  
  // Convert percentage-based Y to absolute World Unit Y (World Height is 50)
  $: titleYAbs = titleY * 0.5;

  // 5. Utilizing Caption
  $: utilizingOpacity = Math.min(1, Math.max(0, (progress - 0.6) * 10));

  // 6. Arxiv Logo
  $: arxivOpacity = Math.min(1, Math.max(0, (progress - 0.8) * 10));

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
           <video
             class="art-placeholder"
             autoplay
             loop
             muted
             playsinline
             poster={mlbg}
           >
             <source src={webmVideo} type="video/webm" />
             <source src={mp4Video} type="video/mp4" />
           </video>
      </div>

      <!-- Logo Layer -->
      <div class="logo-layer" style="transform: scale({bgScale})">
          <img src={monaaLisaLogo} alt="Monaa-Lisa Logo" class="hero-logo" />
      </div>

      <!-- Hero Section (Title) -->
      <div class="hero-layer title-layer" style="opacity: {heroOpacity}; pointer-events: none">
          <h1 class="hero-title">Monaa-Lisa</h1>
      </div>

      <!-- Hero Section (Content) -->
      <div class="hero-layer content-layer" style="opacity: {heroOpacity}; pointer-events: {heroOpacity < 0.1 ? 'none' : 'auto'}">
          <!-- Spacer to push content down similar to where it would be if title was here -->
          <div class="title-spacer"></div>
          <div class="hero-content">
            <button class="start-btn" on:click={start}>START</button>
            <p class="hero-subtitle">Visualize academia interactively</p>
          </div>
      </div>

      <!-- Second Section (Zoomed out view) -->
      <!-- 
        We use an SVG mask to create the "Hole" effect.
        The SVG scales via viewBox (zooming camera in/out) instead of CSS transform.
        This provides performance optimization for the 3000x zoom.
      -->
      <div class="second-section">
           <svg class="overlay-svg" viewBox="{vbX} {vbY} {vbW} {vbH}" preserveAspectRatio="xMidYMid slice">
              <defs>
                 <mask id="text-mask" maskUnits="userSpaceOnUse" maskContentUnits="userSpaceOnUse" x="-500" y="-500" width="1000" height="1000">
                    <!-- Infinite White Rect (The Mask) -->
                    <rect x="-500" y="-500" width="1000" height="1000" fill="white" />
                    <text x="{titleX}" y="{titleYAbs}" text-anchor="middle" dominant-baseline="middle" font-size="12" font-weight="900" fill="black">Monaa-Lisa</text>
                 </mask>
              </defs>
              <!-- The Solid Background with Hole (Infinite Rect) -->
              <rect x="-500" y="-500" width="1000" height="1000" fill="#1a1f2c" mask="url(#text-mask)" />
              
              <!-- The White Text Fill -->
              <text x="{titleX}" y="{titleYAbs}" text-anchor="middle" dominant-baseline="middle" font-size="12" font-weight="900" fill="white" opacity={titleOpacity}>Monaa-Lisa</text>
           </svg>
      </div>
      
      <!-- Subtitle is separate, fades in at the end -->
      <div class="subtitle-container" style="opacity: {subtitleOpacity}">
          <h2 class="sub-title">A tool to visualize academic papers, their relations and citations</h2>
      </div>

      <div class="utilizing-container" style="opacity: {utilizingOpacity}">
          <h2 class="sub-title">utilizing</h2>
      </div>

      <div class="arxiv-container" style="opacity: {arxivOpacity}; pointer-events: {arxivOpacity > 0.1 ? 'auto' : 'none'}">
          <a href="https://arxiv.org/" target="_blank" rel="noopener noreferrer">
            <img src={arxivLogo} alt="arXiv" class="arxiv-logo" />
          </a>
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
    height: 500vh;
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
    will-change: transform;
  }

  .art-placeholder {
    width: 100%;
    height: 100%;
    object-fit: cover;
    filter: brightness(0.9) contrast(0.85);
  }

  .logo-layer {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    z-index: 15; /* Middle Layer */
    pointer-events: none;
    display: flex;
    justify-content: center;
    align-items: flex-end;
  }

  .hero-layer {
    position: absolute;
    width: 100%;
    height: 100%;
    display: flex;
    flex-direction: column;
    justify-content: flex-start;
    align-items: center;
    text-align: center;
    padding-top: 10vh;
  }

  .title-layer {
    z-index: 10; /* Bottom Layer */
  }

  .content-layer {
    z-index: 20; /* Top Layer */
  }

  .title-spacer {
    /* Approximate height of title + margin to push button down */
    height: calc(6rem + 2rem); 
    width: 1px;
  }

  .hero-logo {
    height: 92vh;
    width: auto;
    margin-bottom: 0;
    filter: drop-shadow(0 0 20px rgba(0,0,0,0.8));
  }

  .hero-title {
    font-size: 10rem;
    margin: 0;
    margin-bottom: 2rem;
    text-transform: uppercase;
    letter-spacing: 10px;
    font-weight: 900;
    text-shadow: 0 0 20px rgba(0,0,0,0.5);
  }

  .hero-content {
    display: flex;
    flex-direction: column;
    align-items: center;
  }

  .start-btn {
    margin-top: 500px;
    padding: 15px 50px;
    font-size: 1.5rem;
    background: rgba(100, 100, 255, 0.15); /* Slight blue tint base */
    border: 2px solid #fff;
    color: #fff;
    cursor: pointer;
    text-transform: uppercase;
    letter-spacing: 2px;
    transition: all 0.3s ease;
    backdrop-filter: blur(10px);
    box-shadow: 0 0 20px rgba(138, 43, 226, 0.3), inset 0 0 20px rgba(0, 191, 255, 0.2); /* Purple glow + Blue inner glow */
  }

  .start-btn:hover {
    background: rgba(255, 255, 255, 0.9);
    color: #000;
    transform: scale(1.05);
    box-shadow: 0 0 30px rgba(138, 43, 226, 0.6), inset 0 0 20px rgba(0, 191, 255, 0.4);
  }

  .hero-subtitle {
    margin-top: 100px;
    font-size: 1.2rem;
    letter-spacing: 9px;
    text-transform: uppercase;
    opacity: 0.9;
    text-shadow: 0 2px 2px rgba(0,0,0,0.9);
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
    /* Removed will-change to prevent layer composition artifacts in Chrome */
  }

  .overlay-svg {
    width: 100vw;
    height: 100vh;
    /* Ensure text is crisp */
    shape-rendering: auto;
    text-rendering: optimizeLegibility;
  }
  
  .overlay-svg text {
    font-family: Arial, sans-serif;
    text-transform: uppercase;
  }

  .subtitle-container {
    position: absolute;
    z-index: 30;
    top: 45%; /* Position below the title */
    width: 100%;
    text-align: center;
    pointer-events: none;
  }

  .utilizing-container {
    position: absolute;
    z-index: 30;
    top: 55%;
    width: 100%;
    text-align: center;
    pointer-events: none;
  }

  .arxiv-container {
    position: absolute;
    z-index: 40;
    top: 65%;
    width: 100%;
    display: flex;
    justify-content: center;
    align-items: center;
  }

  .arxiv-logo {
    height: 150px;
    filter: invert(1);
    transition: transform 0.3s ease;
  }

  .arxiv-logo:hover {
    transform: scale(1.1);
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
