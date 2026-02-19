<!--
  Dashboard.svelte
  Slide-in dashboard panel showing:
    - Recent history (last 10 viewed papers)
    - Favorite papers (starred from paper detail view)
  Stored securely in localStorage with validation.
-->
<script lang="ts">
  import { createEventDispatcher, onMount } from 'svelte';
  import { getSubcategoryName } from '../utils/arxivTaxonomy';

  export let isOpen: boolean = false;

  const HISTORY_KEY   = 'monaalisa_history_v1';
  const FAVORITES_KEY = 'monaalisa_favorites_v1';
  const MAX_HISTORY   = 10;
  const MAX_STR       = 500;   // max chars for any stored string

  interface DashboardItem {
    entry_id: string;
    title: string;
    authors: string;
    categories: string | null;
    published: string | null;
    savedAt: number;
  }

  const dispatch = createEventDispatcher<{
    navigate: DashboardItem;
    close: void;
  }>();

  let history: DashboardItem[]   = [];
  let favorites: DashboardItem[] = [];
  let activeTab: 'history' | 'favorites' = 'history';

  // ─── validation & sanitisation ────────────────────────────────────
  function clamp(s: unknown, max: number): string {
    if (typeof s !== 'string') return '';
    return s.slice(0, max);
  }

  function isValidItem(obj: unknown): obj is DashboardItem {
    if (!obj || typeof obj !== 'object') return false;
    const o = obj as Record<string, unknown>;
    return (
      typeof o.entry_id  === 'string' && o.entry_id.length > 0 &&
      typeof o.title     === 'string' && o.title.length > 0 &&
      typeof o.authors   === 'string' &&
      typeof o.savedAt   === 'number'
    );
  }

  function loadList(key: string): DashboardItem[] {
    try {
      const raw = typeof localStorage !== 'undefined' ? localStorage.getItem(key) : null;
      if (!raw) return [];
      const parsed = JSON.parse(raw);
      if (!Array.isArray(parsed)) return [];
      return parsed
        .filter(isValidItem)
        .map(item => ({
          entry_id:   clamp(item.entry_id, 100),
          title:      clamp(item.title,    MAX_STR),
          authors:    clamp(item.authors,  MAX_STR),
          categories: item.categories ? clamp(item.categories, 200) : null,
          published:  item.published  ? clamp(item.published,  30)  : null,
          savedAt:    item.savedAt,
        }));
    } catch {
      return [];
    }
  }

  function saveList(key: string, list: DashboardItem[]) {
    try {
      if (typeof localStorage !== 'undefined') {
        localStorage.setItem(key, JSON.stringify(list));
      }
    } catch {}
  }

  // ─── public API (called from GraphLayout) ─────────────────────────
  export function addToHistory(paper: { entry_id: string; title: string; authors: string; categories: string | null; published: string | null }) {
    const item: DashboardItem = {
      entry_id:   clamp(paper.entry_id,   100),
      title:      clamp(paper.title,      MAX_STR),
      authors:    clamp(paper.authors,    MAX_STR),
      categories: paper.categories ? clamp(paper.categories, 200) : null,
      published:  paper.published  ? clamp(paper.published,  30)  : null,
      savedAt:    Date.now(),
    };
    history = [item, ...history.filter(h => h.entry_id !== paper.entry_id)].slice(0, MAX_HISTORY);
    saveList(HISTORY_KEY, history);
  }

  export function toggleFavorite(paper: { entry_id: string; title: string; authors: string; categories: string | null; published: string | null }) {
    const exists = favorites.some(f => f.entry_id === paper.entry_id);
    if (exists) {
      favorites = favorites.filter(f => f.entry_id !== paper.entry_id);
    } else {
      favorites = [
        {
          entry_id:   clamp(paper.entry_id,   100),
          title:      clamp(paper.title,      MAX_STR),
          authors:    clamp(paper.authors,    MAX_STR),
          categories: paper.categories ? clamp(paper.categories, 200) : null,
          published:  paper.published  ? clamp(paper.published,  30)  : null,
          savedAt:    Date.now(),
        },
        ...favorites,
      ];
    }
    saveList(FAVORITES_KEY, favorites);
  }

  export function isFavorite(entryId: string): boolean {
    return favorites.some(f => f.entry_id === entryId);
  }

  // ─── helpers ──────────────────────────────────────────────────────
  function formatYear(d: string | null): string {
    if (!d) return '—';
    return new Date(d).getFullYear().toString();
  }

  function formatFirstCat(cats: string | null): string {
    if (!cats) return '';
    const cat = cats.trim().split(/[\s,]+/)[0] ?? '';
    if (!cat) return '';
    const full = getSubcategoryName(cat);
    return full !== cat ? `${full} (${cat})` : cat;
  }

  function truncate(s: string, n: number): string {
    return s.length > n ? s.slice(0, n) + '…' : s;
  }

  function removeHistory(entryId: string) {
    history = history.filter(h => h.entry_id !== entryId);
    saveList(HISTORY_KEY, history);
  }

  function removeFavorite(entryId: string) {
    favorites = favorites.filter(f => f.entry_id !== entryId);
    saveList(FAVORITES_KEY, favorites);
  }

  function clearHistory() {
    history = [];
    saveList(HISTORY_KEY, history);
  }

  onMount(() => {
    history   = loadList(HISTORY_KEY);
    favorites = loadList(FAVORITES_KEY);
  });
</script>

<!-- overlay backdrop -->
{#if isOpen}
  <div class="db-backdrop" on:click={() => dispatch('close')} on:keydown={() => {}} role="presentation"></div>
{/if}

<div class="dashboard" class:open={isOpen}>
  <!-- header -->
  <div class="db-header">
    <div class="db-title-row">
      <span class="db-icon">&#9733;</span>
      <h2 class="db-title">Dashboard</h2>
    </div>
    <button class="db-close" on:click={() => dispatch('close')} title="Close">&#x2715;</button>
  </div>

  <!-- tabs -->
  <div class="db-tabs">
    <button
      class="db-tab"
      class:active={activeTab === 'history'}
      on:click={() => { activeTab = 'history'; }}
    >
      Recent ({history.length})
    </button>
    <button
      class="db-tab"
      class:active={activeTab === 'favorites'}
      on:click={() => { activeTab = 'favorites'; }}
    >
      Favorites ({favorites.length})
    </button>
  </div>

  <!-- tab content -->
  <div class="db-content">

    <!-- ── history tab ── -->
    {#if activeTab === 'history'}
      {#if history.length === 0}
        <p class="db-empty">No papers viewed yet. Open a paper to start tracking history.</p>
      {:else}
        <div class="db-actions-row">
          <button class="db-clear-btn" on:click={clearHistory}>Clear all</button>
        </div>
        {#each history as item (item.entry_id)}
          <div class="db-item">
            <div class="db-item-body">
              <button class="db-item-title" on:click={() => dispatch('navigate', item)}>
                {truncate(item.title, 90)}
              </button>
              <p class="db-item-meta">{truncate(item.authors, 60)}</p>
              <p class="db-item-meta db-item-tags">
                {formatYear(item.published)}
                {#if item.categories}&nbsp;·&nbsp;{formatFirstCat(item.categories)}{/if}
              </p>
            </div>
            <button class="db-del-btn" title="Remove from history" on:click={() => removeHistory(item.entry_id)}>&#x2715;</button>
          </div>
        {/each}
      {/if}

    <!-- ── favorites tab ── -->
    {:else}
      {#if favorites.length === 0}
        <p class="db-empty">No favorites yet. Star a paper from the detail view to save it here.</p>
      {:else}
        {#each favorites as item (item.entry_id)}
          <div class="db-item">
            <div class="db-item-body">
              <button class="db-item-title" on:click={() => dispatch('navigate', item)}>
                {truncate(item.title, 90)}
              </button>
              <p class="db-item-meta">{truncate(item.authors, 60)}</p>
              <p class="db-item-meta db-item-tags">
                {formatYear(item.published)}
                {#if item.categories}&nbsp;·&nbsp;{formatFirstCat(item.categories)}{/if}
              </p>
            </div>
            <button class="db-del-btn db-del-fav" title="Remove from favorites" on:click={() => removeFavorite(item.entry_id)}>&#x2665;</button>
          </div>
        {/each}
      {/if}
    {/if}

  </div>
</div>

<style>
  .db-backdrop {
    position: fixed;
    inset: 0;
    z-index: 199;
    background: rgba(0, 0, 0, 0.35);
    backdrop-filter: blur(2px);
  }

  .dashboard {
    position: fixed;
    top: 0;
    left: 0;
    width: 360px;
    height: 100vh;
    z-index: 200;
    display: flex;
    flex-direction: column;
    background: var(--bg-secondary, #141530);
    border-right: 1px solid var(--glass-border, rgba(255,255,255,0.10));
    box-shadow: 4px 0 32px rgba(0,0,0,0.5);
    transform: translateX(-100%);
    transition: transform 0.28s cubic-bezier(0.4, 0, 0.2, 1);
    overflow: hidden;
  }

  .dashboard.open {
    transform: translateX(0);
  }

  /* ── header ── */
  .db-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 14px 16px 10px;
    border-bottom: 1px solid var(--glass-border, rgba(255,255,255,0.08));
    flex-shrink: 0;
    background: var(--bg-secondary, #141530);
  }

  .db-title-row {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .db-icon {
    font-size: 16px;
    color: var(--accent-yellow, #ffd166);
  }

  .db-title {
    margin: 0;
    font-size: 15px;
    font-weight: 700;
    color: var(--text-primary, #f0f0f8);
    letter-spacing: 0.3px;
  }

  .db-close {
    background: none;
    border: 1px solid transparent;
    color: var(--text-muted, #6b6b8d);
    font-size: 14px;
    cursor: pointer;
    padding: 4px 8px;
    border-radius: var(--radius-sm, 8px);
    transition: all 0.15s ease;
    line-height: 1;
  }
  .db-close:hover {
    color: var(--text-primary, #f0f0f8);
    background: rgba(255,255,255,0.07);
    border-color: rgba(255,255,255,0.12);
  }

  /* ── tabs ── */
  .db-tabs {
    display: flex;
    gap: 0;
    border-bottom: 1px solid var(--glass-border, rgba(255,255,255,0.08));
    flex-shrink: 0;
  }

  .db-tab {
    flex: 1;
    background: none;
    border: none;
    border-bottom: 2px solid transparent;
    padding: 10px 12px;
    color: var(--text-muted, #6b6b8d);
    font-size: 12px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.15s ease;
  }
  .db-tab:hover {
    color: var(--text-primary, #f0f0f8);
    background: rgba(255,255,255,0.04);
  }
  .db-tab.active {
    color: var(--accent-cyan, #22d3ee);
    border-bottom-color: var(--accent-cyan, #22d3ee);
  }

  /* ── content ── */
  .db-content {
    flex: 1;
    overflow-y: auto;
    padding: 8px 0;
    scrollbar-width: thin;
    scrollbar-color: rgba(147,51,234,0.3) transparent;
  }
  .db-content::-webkit-scrollbar { width: 4px; }
  .db-content::-webkit-scrollbar-track { background: transparent; }
  .db-content::-webkit-scrollbar-thumb { background: rgba(147,51,234,0.3); border-radius: 99px; }

  .db-empty {
    margin: 32px 20px;
    font-size: 12px;
    color: var(--text-muted, #6b6b8d);
    line-height: 1.6;
    text-align: center;
  }

  .db-actions-row {
    display: flex;
    justify-content: flex-end;
    padding: 4px 14px 6px;
  }

  .db-clear-btn {
    background: none;
    border: 1px solid rgba(245,101,101,0.25);
    color: #f56565;
    font-size: 11px;
    padding: 3px 10px;
    border-radius: 999px;
    cursor: pointer;
    transition: all 0.15s ease;
  }
  .db-clear-btn:hover {
    background: rgba(245,101,101,0.12);
    border-color: rgba(245,101,101,0.45);
  }

  /* ── item ── */
  .db-item {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    padding: 9px 14px;
    border-bottom: 1px solid rgba(255,255,255,0.04);
    transition: background 0.12s ease;
  }
  .db-item:hover {
    background: rgba(255,255,255,0.03);
  }

  .db-item-body {
    flex: 1;
    min-width: 0;
  }

  .db-item-title {
    background: none;
    border: none;
    padding: 0;
    margin: 0 0 4px;
    color: var(--text-primary, #f0f0f8);
    font-size: 12px;
    font-weight: 500;
    cursor: pointer;
    text-align: left;
    line-height: 1.4;
    transition: color 0.12s ease;
    white-space: normal;
    word-break: break-word;
  }
  .db-item-title:hover {
    color: var(--accent-cyan, #22d3ee);
  }

  .db-item-meta {
    margin: 0;
    font-size: 11px;
    color: var(--text-muted, #6b6b8d);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .db-item-tags {
    color: var(--text-secondary, #a8a8c8);
    font-size: 10.5px;
    margin-top: 2px;
  }

  .db-del-btn {
    background: none;
    border: 1px solid transparent;
    color: var(--text-muted, #6b6b8d);
    font-size: 12px;
    cursor: pointer;
    padding: 3px 6px;
    border-radius: var(--radius-sm, 8px);
    transition: all 0.12s ease;
    flex-shrink: 0;
    margin-top: 1px;
    line-height: 1;
  }
  .db-del-btn:hover {
    color: #f56565;
    background: rgba(245,101,101,0.10);
    border-color: rgba(245,101,101,0.25);
  }

  .db-del-fav {
    color: var(--accent-yellow, #ffd166);
    opacity: 0.6;
  }
  .db-del-fav:hover {
    color: #f56565;
    background: rgba(245,101,101,0.10);
    border-color: rgba(245,101,101,0.25);
    opacity: 1;
  }
</style>
