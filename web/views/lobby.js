// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Build searchable catalog, trust rail, and game cards behind the Lobby route view. (CORE-007, CORE-012)

// Create the Lobby renderer with route-local filter state.
export function createLobbyView(dependencies) {
  // Capture the accepted brand, catalog, navigation, and presentation seams.
  const {
    activeBrand, getGameDescriptors, getLatestState, html, navigate,
    raw, renderPremiumTag, safe, t,
  } = dependencies;
  // Retain transient catalog search text only for this browser module lifetime.
  let lobbySearch = '';
  // Retain the selected discovered category without encoding it into game routes.
  let lobbyCategory = 'all';

  // Render one compact lobby trust tile.
  function trustItemHtml(code, title, detail) {
    // Preserve the approved icon, title, and detail hierarchy.
    return html`<div class="trust-item"><span class="round-icon">${code}</span><span><strong>${title}</strong><span>${detail}</span></span></div>`;
  }

  // Render one premium game card from catalog metadata.
  function lobbyCardHtml(game) {
    // Preserve featured and wide layout modifiers.
    const sizeClass = `${game.featured ? ' featured' : ''}${game.wide ? ' wide' : ''}`;
    const tags = game.tags.map(tag => raw(renderPremiumTag(tag)));
    const featured = game.featured ? html`&#9733; ` : html``;
    const kicker = html`${featured}${game.kicker}`;
    // Preserve deterministic art and localized descriptive content.
    const art = html`<div class="card-art ${game.artClass}" aria-hidden="true"></div>`;
    const heading = html`<h2 class="game-heading"><span class="game-symbol">${game.symbol}</span>${game.label}</h2>`;
    const playLabel = html`<span>${t('catalog.play', {}, 'shell')}</span>`;
    const play = html`<button class="play-button" data-open-game="${game.id}" data-testid="open-${game.id}">${playLabel}<span aria-hidden="true">&#8250;</span></button>`;
    const content = html`<div class="game-card-content">${heading}<p>${game.description}</p><div class="tag-row">${tags}</div>${play}</div>`;
    return html`<article class="game-card${sizeClass}" data-testid="card-${game.id}">${art}<span class="game-kicker">${kicker}</span>${content}</article>`;
  }

  // Return catalog descriptors matching active search and category filters.
  function filteredGames() {
    // Normalize user search text for stable case-insensitive matching.
    const query = lobbySearch.trim().toLocaleLowerCase();
    return getGameDescriptors().filter((game) => {
      // Require selected category membership unless all categories are active.
      const categoryMatch = lobbyCategory === 'all'
        || game.categories.includes(lobbyCategory);
      const searchText = [
        game.label, game.description, ...game.tags, ...game.categories,
      ].join(' ').toLocaleLowerCase();
      return categoryMatch && (!query || searchText.includes(query));
    });
  }

  // Resolve a localized player-facing category label.
  function categoryLabel(category) {
    // Use dedicated copy for the synthetic all-games category.
    if (category === 'all') return t('catalog.allGames', {}, 'shell');
    // Resolve installed identifiers without title-casing internal ids.
    return t(`catalog.category.${category}`, {}, 'shell');
  }

  // Render catalog controls derived from current game metadata.
  function catalogControls(gameDescriptors, gameCount) {
    // Derive scalable category navigation without shell edits.
    const categories = [...new Set(
      gameDescriptors.flatMap(game => game.categories),
    )].sort();
    const buttons = ['all', ...categories].map((category) => {
      // Preserve selected visual and assistive state.
      const selected = lobbyCategory === category;
      const activeClass = selected ? ' active' : '';
      const label = categoryLabel(category);
      return html`<button type="button" class="catalog-category${activeClass}" data-catalog-category="${category}" aria-pressed="${selected}">${label}</button>`;
    });
    const searchLabel = html`<label class="catalog-search-label" for="catalog-search">${t('catalog.searchLabel', {}, 'shell')}</label>`;
    const searchInput = html`<input id="catalog-search" data-testid="catalog-search" type="search" value="${lobbySearch}" placeholder="${t('catalog.searchPlaceholder', {}, 'shell')}">`;
    const search = html`${searchLabel}${searchInput}`;
    const categoryRail = html`<div class="catalog-categories" data-testid="catalog-categories" aria-label="${t('catalog.categoriesAria', {}, 'shell')}">${buttons}</div>`;
    const capacity = html`<p class="catalog-capacity" data-testid="catalog-capacity">${t('catalog.capacity', { current: gameCount }, 'shell')}</p>`;
    return html`<section class="catalog-controls" data-testid="catalog-controls">${search}${categoryRail}${capacity}</section>`;
  }

  // Render the premium trust rail from authoritative state.
  function trustRail(gameCount, onlinePlayerCount) {
    // Preserve play-token, presence, autoplay, and ledger cues.
    return [
      trustItemHtml(
        'SIM',
        t('lobby.trust.localTitle', {}, 'shell'),
        t('lobby.trust.localDetail', {}, 'shell'),
      ),
      trustItemHtml(
        'LIVE',
        t('status.online', { count: onlinePlayerCount }, 'shell'),
        t('lobby.presenceDetail', {}, 'shell'),
      ),
      trustItemHtml(
        'AUTO',
        t('lobby.trust.autoplayTitle', {}, 'shell'),
        t('lobby.trust.autoplayDetail', {}, 'shell'),
      ),
      trustItemHtml(
        'LED',
        t('lobby.trust.ledgerTitle', {}, 'shell'),
        t('lobby.trust.ledgerDetail', { count: gameCount }, 'shell'),
      ),
    ];
  }

  // Render the complete premium Lobby markup.
  function lobbyHtml(state = getLatestState()) {
    // Resolve authoritative counts and current descriptors.
    const descriptors = getGameDescriptors();
    const gameCount = Array.isArray(state?.games) ? state.games.length : descriptors.length;
    const onlinePlayerCount = Number.isInteger(state?.online_player_count)
      ? state.online_player_count
      : 0;
    const visibleGames = filteredGames();
    const cards = visibleGames.length
      ? visibleGames.map(lobbyCardHtml)
      : html`<p class="catalog-empty" data-testid="catalog-empty">${t('catalog.empty', {}, 'shell')}</p>`;
    // Preserve hero identity and trust rail.
    const eyebrow = html`<p class="eyebrow">${t('lobby.chooseTable', {}, 'shell')}</p>`;
    const title = html`<h1 class="hero-title">${activeBrand.venue}</h1>`;
    const rule = html`<div class="hero-rule"><span>${activeBrand.mark}</span></div>`;
    const heroCopy = html`<div>${eyebrow}${title}${rule}</div>`;
    const trust = html`<aside class="trust-rail" data-testid="lobby-trust-rail" aria-label="Casino status">${trustRail(gameCount, onlinePlayerCount)}</aside>`;
    const hero = html`<section class="lobby-hero" aria-label="Lobby introduction">${heroCopy}${trust}</section>`;
    // Preserve catalog controls and gallery as one named region.
    const controls = catalogControls(descriptors, gameCount);
    const gallery = html`<section class="game-gallery" data-testid="game-gallery" aria-label="${t('catalog.galleryAria', {}, 'shell')}">${cards}</section>`;
    const catalog = html`<section class="catalog-region" data-testid="catalog-region" aria-label="${t('catalog.controlsAria', {}, 'shell')}">${controls}${gallery}</section>`;
    return html`<section class="lobby" data-testid="lobby">${hero}${catalog}</section>`;
  }

  // Render Lobby markup and bind catalog-driven controls.
  function renderLobby(view, focusSearch = false) {
    // Replace atomically so cards and category counts cannot drift.
    view.innerHTML = html`${lobbyHtml()}`;
    const search = view.querySelector('[data-testid="catalog-search"]');
    // Rerender matching cards for each user edit.
    search.oninput = () => {
      lobbySearch = search.value;
      renderLobby(view, true);
    };
    // Bind discovered category filters.
    view.querySelectorAll('[data-catalog-category]').forEach((button) => {
      // Preserve one selected category at a time.
      button.onclick = () => {
        lobbyCategory = button.dataset.catalogCategory;
        renderLobby(view);
      };
    });
    // Bind visible game cards to canonical route navigation.
    view.querySelectorAll('[data-open-game]').forEach((button) => {
      // Navigate through the shared shell router.
      button.onclick = () => navigate(button.dataset.openGame);
    });
    // Restore search focus and caret after filter rerender.
    if (focusSearch) {
      search.focus();
      search.setSelectionRange(search.value.length, search.value.length);
    }
  }

  // Publish only the router-facing Lobby renderer.
  return renderLobby;
}
