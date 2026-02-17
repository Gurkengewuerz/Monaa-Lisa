<div class="header">
  <div class="header-accent-line"></div>
  <div class="header-inner">
    <span class="header-logo">M-L</span>
    <h1 class="header-title">Monaa-Lisa <span class="header-divider">—</span> <span class="header-subtitle">Academic Paper Visualization</span></h1>
  </div>
</div>

<style>
  .header {
    position: relative;
    padding: 0;
    background: var(--bg-secondary, #141530);
    border-bottom: 1px solid var(--glass-border, rgba(255,255,255,0.08));
    z-index: 100;
    flex-shrink: 0;
    overflow: hidden;
  }

  .header-accent-line {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    height: 2px;
    background: var(--gradient-header, linear-gradient(90deg, #9333ea, #e839a0, #22d3ee));
    opacity: 0.7;
  }

  .header-inner {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 10px 20px;
  }

  .header-logo {
    font-size: 14px;
    font-weight: 800;
    letter-spacing: 2px;
    color: var(--text-primary, #f0f0f8);
    padding: 4px 8px;
    border: 1.5px solid rgba(147, 51, 234, 0.5);
    border-radius: 4px;
    background: linear-gradient(135deg, rgba(147,51,234,0.15), rgba(232,57,160,0.1));
    text-shadow: 0 0 8px rgba(147, 51, 234, 0.4);
    flex-shrink: 0;
  }

  .header-title {
    color: var(--text-primary, #f0f0f8);
    font-size: 15px;
    margin: 0;
    font-weight: 600;
    letter-spacing: 0.5px;
    white-space: nowrap;
  }

  .header-divider {
    color: var(--text-muted, #6b6b8d);
    margin: 0 2px;
    font-weight: 300;
  }

  .header-subtitle {
    color: var(--text-secondary, #a8a8c8);
    font-weight: 400;
  }
</style>