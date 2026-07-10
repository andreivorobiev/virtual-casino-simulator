// AUTO-COMMENTED FOR CODEX: each meaningful executable line has an adjacent purpose comment.
// Import required dependency so this module can call the frozen API envelope safely.
import { api, logClient } from './core/api.js';
// Import required dependency so this module can render shared wallet and premium UI helpers.
import { refreshBalance, addFakeMoney, toast, money, safe, renderPremiumTag } from './core/ui.js';
// Import required dependency so this module can preload global voice settings before games mount.
import { loadVoiceSettings } from './core/voice.js';

// Describe each game route once so navigation, lobby cards, and dynamic imports stay aligned.
const gameDescriptors = [
  // Define the Roulette route as the featured table game in the premium lobby.
  { id: 'roulette', label: 'Roulette', path: './games/roulette.js', exportName: 'RouletteGame', featured: true, wide: false, artClass: 'roulette-art', symbol: '&#9679;', kicker: 'Featured', description: 'Classic wheel with inside and outside bets, racetrack specials, bots, zero rules, and last-1000 stats.', tags: ['Bots', 'Autoplay', 'Stats', 'Ledger-backed'] },
  // Define the Slots route with the wide machine-card treatment.
  { id: 'slots', label: 'Slots', path: './games/slots.js', exportName: 'SlotsGame', featured: false, wide: true, artClass: 'slot-art', symbol: '&#9638;', kicker: 'Machine', description: 'Animated 5-reel slots with paylines, wilds, scatters, free spins, and progressive features.', tags: ['Bots', 'Autoplay', 'Bonus rounds'] },
  // Define the Keno route with draw-game tags and CSS-native card art.
  { id: 'keno', label: 'Keno', path: './games/keno.js', exportName: 'KenoGame', featured: false, wide: false, artClass: 'keno-art', symbol: '18', kicker: 'Draw', description: 'Pick 1-20 spots, draw 20 numbers, paytable display, animations, and bot tickets.', tags: ['Bots', 'Autoplay', 'Stats'] },
  // Define the Bingo route with draw-game tags and stable card treatment.
  { id: 'bingo', label: 'Bingo', path: './games/bingo.js', exportName: 'BingoGame', featured: false, wide: false, artClass: 'bingo-art', symbol: '&#9638;', kicker: 'Cards', description: '75-ball American Bingo with patterns, bot cards, call history, and winning pattern highlights.', tags: ['Bots', 'Autoplay', 'Stats'] },
  // Define the Blackjack route with table-game card and chip cues.
  { id: 'blackjack', label: 'Blackjack', path: './games/blackjack.js', exportName: 'BlackjackGame', featured: false, wide: false, artClass: 'blackjack-art', symbol: '&#9824;', kicker: 'Table', description: 'Hit, stand, double, split, surrender, insurance, even money, and table rule controls.', tags: ['Bots', 'Autoplay', 'Stats', 'Ledger-backed'] },
  // Define the Baccarat route with shoe, road-history, and bot capability cues.
  { id: 'baccarat', label: 'Baccarat', path: './games/baccarat.js', exportName: 'BaccaratGame', featured: false, wide: false, artClass: 'baccarat-art', symbol: '&#9827;', kicker: 'Table', description: 'Punto Banco shoe with burn/cut behavior, Player/Banker/Tie bets, bots, and road history.', tags: ['Bots', 'Autoplay', 'Stats'] },
];
// Store loaded game modules so repeated route changes do not re-import the same module.
const loadedGames = new Map();
// Track the active route so navigation can show the selected shell item.
let active = null;
// Cache the latest casino state so lobby and status rail values render without extra calls.
let latestState = null;

// Relay game/autoplay toast events through the shell-level toast outlet.
window.addEventListener('casino-toast', event => toast(event.detail?.message || 'Auto stopped'));
// Report top-level browser errors through the client log API for admin visibility.
window.addEventListener('error', event => logClient('window_error', { message: event.message, filename: event.filename, lineno: event.lineno, colno: event.colno }));
// Report unhandled promise rejections through the client log API for admin visibility.
window.addEventListener('unhandledrejection', event => logClient('unhandled_rejection', { reason: String(event.reason?.message || event.reason) }));

// Load a game module lazily while preserving one module boundary per game.
async function loadGame(desc) {
  // Return a cached module export when this route has already been loaded.
  if (loadedGames.has(desc.id)) return loadedGames.get(desc.id);
  // Start protected import logic so load failures are captured in client logs.
  try {
    // Import the owned game frontend module by its documented route path.
    const mod = await import(desc.path);
    // Read the known game class export from the module namespace.
    const game = mod[desc.exportName];
    // Cache the class so later navigations can mount without importing again.
    loadedGames.set(desc.id, game);
    // Return the game class to the navigation flow.
    return game;
  // Handle dynamic import failures with diagnostics for Admin telemetry.
  } catch (err) {
    // Record the module load error with route context.
    await logClient('game_module_load_error', { game: desc.id, message: err.message, stack: err.stack });
    // Re-throw so navigation can render its friendly failure panel.
    throw err;
  }
}

// Render the premium top navigation from the route registry.
function renderNav() {
  // Read the navigation outlet that index.html reserves for route buttons.
  const nav = document.getElementById('main-nav');
  // Build the lobby button with the active shell class when selected.
  const items = [`<button data-route="lobby" class="nav-item ${active === 'lobby' ? 'active' : ''}" data-testid="nav-lobby"><span class="nav-icon" aria-hidden="true">&#8962;</span>Lobby</button>`];
  // Add one button per game so every game remains equally reachable.
  gameDescriptors.forEach(game => items.push(`<button data-route="${game.id}" class="nav-item ${active === game.id ? 'active' : ''}" data-testid="nav-${game.id}">${safe(game.label)}</button>`));
  // Add the Admin route as a normal top-level shell affordance.
  items.push('<button data-admin="true" class="nav-item admin" data-testid="nav-admin">Admin</button>');
  // Replace the nav contents atomically so active state cannot drift.
  nav.innerHTML = items.join('');
  // Wire every app route button to the shared navigate function.
  nav.querySelectorAll('[data-route]').forEach(button => { button.onclick = () => navigate(button.dataset.route); });
  // Wire the Admin button to the existing dedicated Admin page.
  nav.querySelector('[data-admin]').onclick = () => { location.href = '/admin'; };
}

// Render one status tile for the lobby trust rail.
function trustItemHtml(code, title, detail) {
  // Return a compact status tile that mirrors the approved lobby prerender.
  return `<div class="trust-item"><span class="round-icon">${safe(code)}</span><span><strong>${safe(title)}</strong><span>${safe(detail)}</span></span></div>`;
}

// Render one premium lobby game card from shared game metadata.
function lobbyCardHtml(game) {
  // Compute the layout modifier classes used by the approved card grid.
  const sizeClass = `${game.featured ? ' featured' : ''}${game.wide ? ' wide' : ''}`;
  // Render all card tags through the shared helper so later workers can reuse the tag contract.
  const tags = game.tags.map(tag => renderPremiumTag(tag)).join('');
  // Return the full card with deterministic art, metadata, and open-game control.
  return `<article class="game-card${sizeClass}" data-testid="card-${game.id}"><div class="card-art ${game.artClass}" aria-hidden="true"></div><span class="game-kicker">${game.featured ? '&#9733; ' : ''}${safe(game.kicker)}</span><div class="game-card-content"><h2 class="game-heading"><span class="game-symbol">${game.symbol}</span>${safe(game.label)}</h2><p>${safe(game.description)}</p><div class="tag-row">${tags}</div><button class="play-button" data-open-game="${game.id}" data-testid="open-${game.id}"><span>Play</span><span aria-hidden="true">&#8250;</span></button></div></article>`;
}

// Render the full premium lobby with hero, status rail, and all current games.
function lobbyHtml(state = latestState) {
  // Count the available games from API state while falling back to the frontend registry.
  const gameCount = Array.isArray(state?.games) ? state.games.length : gameDescriptors.length;
  // Count visible players so the lobby trust rail reflects the local casino state.
  const playerCount = Array.isArray(state?.players) ? state.players.length : 0;
  // Render the game card collection from the shared route registry.
  const cards = gameDescriptors.map(game => lobbyCardHtml(game)).join('');
  // Render the premium trust rail with play-token, bot, autoplay, and ledger cues.
  const trustRail = [trustItemHtml('SIM', 'Local Simulator', 'All play tokens'), trustItemHtml('BOT', `${playerCount} Players`, 'Human and bots'), trustItemHtml('AUTO', 'Autoplay Ready', 'Control-plane automation'), trustItemHtml('LED', 'Ledger-Backed', `${gameCount} games tracked`)].join('');
  // Return the complete lobby markup as one route payload.
  return `<section class="lobby" data-testid="lobby"><section class="lobby-hero" aria-label="Lobby introduction"><div><p class="eyebrow">Choose your table</p><h1 class="hero-title">Midnight Ledger Casino</h1><div class="hero-rule"><span>&#9824;</span></div></div><aside class="trust-rail" data-testid="lobby-trust-rail" aria-label="Casino status">${trustRail}</aside></section><section class="game-gallery" aria-label="Games">${cards}</section></section>`;
}

// Update one status text node if that node exists in the current document.
function setStatusText(id, text) {
  // Read the target status element by id.
  const element = document.getElementById(id);
  // Update the text only when the shell outlet exists.
  if (element) element.textContent = text;
}

// Keep the bottom status rail synchronized with the latest API state.
function updateShellStatus(state, connected) {
  // Resolve the app version string from API state or fallback text.
  const version = state?.version ? `v${state.version}` : 'Unavailable';
  // Resolve player count text from the state payload.
  const players = Array.isArray(state?.players) ? `${state.players.length} online` : '0 online';
  // Write the version into the persistent status rail.
  setStatusText('status-version', version);
  // Write the player count into the persistent status rail.
  setStatusText('status-players', players);
  // Write the connection state into the persistent status rail.
  setStatusText('connection-status', connected ? 'Connected' : 'Disconnected');
  // Find the visual connection indicator for online/offline styling.
  const dot = document.getElementById('connection-dot');
  // Toggle the offline class without assuming the status rail is present.
  if (dot) dot.classList.toggle('offline', !connected);
}

// Fetch casino state for shell-level status without changing gameplay APIs.
async function refreshShellState(options = {}) {
  // Start protected API polling so the shell can mark itself disconnected on failure.
  try {
    // Read the frozen v1 casino state envelope.
    const state = await api('/api/v1/casino/state');
    // Cache the state for lobby rendering and later refreshes.
    latestState = state;
    // Mark the shell connected and update status values.
    updateShellStatus(state, true);
    // Return state to callers that need initial render data.
    return state;
  // Handle state polling errors without breaking already-mounted games.
  } catch (err) {
    // Mark the shell disconnected when state cannot be read.
    updateShellStatus(null, false);
    // Log quiet polling errors so Admin can see intermittent state failures.
    if (options.quiet) await logClient('shell_state_error', { message: err.message });
    // Rethrow non-quiet initial-load failures so init can show a toast.
    if (!options.quiet) throw err;
    // Return null for quiet polling so setInterval never rejects.
    return null;
  }
}

// Navigate between lobby and game routes while keeping one mounted game at a time.
export async function navigate(route) {
  // Store the requested route for error reporting.
  let targetRoute = route;
  // Start protected navigation so failures render inside the route outlet.
  try {
    // Store the previous route so mounted games can unmount before route changes.
    const previous = active;
    // Check whether the requested route is one of the registered games.
    const knownGame = gameDescriptors.some(game => game.id === route);
    // Fall back to lobby for unknown routes.
    targetRoute = route === 'lobby' || knownGame ? route : 'lobby';
    // Unmount the previously active game when that game supplied cleanup.
    if (previous && loadedGames.has(previous)) loadedGames.get(previous).unmount?.();
    // Store the active route for nav rendering.
    active = targetRoute;
    // Re-render navigation after active route changes.
    renderNav();
    // Read the main route outlet from the document.
    const view = document.getElementById('view');
    // Render the lobby when the target route is lobby.
    if (targetRoute === 'lobby') {
      // Apply the lobby screen class contract for responsive shell styling.
      view.className = 'screen lobby-screen';
      // Render lobby markup from the cached or freshly loaded state.
      view.innerHTML = lobbyHtml(latestState);
      // Wire each premium game card button to its corresponding route.
      view.querySelectorAll('[data-open-game]').forEach(button => { button.onclick = () => navigate(button.dataset.openGame); });
      // Stop after lobby render because no game module is mounted.
      return;
    }
    // Apply the game screen class contract before mounting a game module.
    view.className = 'screen game-screen';
    // Render a premium loading panel while the dynamic game module loads.
    view.innerHTML = `<div class="panel loading-panel"><h2>Loading ${safe(targetRoute)}...</h2></div>`;
    // Resolve the descriptor for the selected game route.
    const desc = gameDescriptors.find(game => game.id === targetRoute);
    // Load the game class through the module registry.
    const game = await loadGame(desc);
    // Mount the game into the same route outlet used by the original app.
    await game.mount(view);
    // Refresh wallet and status rail after route mount.
    await refreshBalance();
  // Handle navigation errors with a route-local recovery panel.
  } catch (err) {
    // Write diagnostic output so the current operation can be inspected.
    console.error(err);
    // Record the navigation failure with route context.
    await logClient('navigation_error', { route: targetRoute, message: err.message, stack: err.stack });
    // Read the route outlet for the fallback panel.
    const view = document.getElementById('view');
    // Keep the route outlet in game-screen mode so the error panel has premium shell padding.
    view.className = 'screen game-screen';
    // Render a friendly error state with a lobby recovery action.
    view.innerHTML = `<div class="panel loading-panel"><h2>Could not load ${safe(targetRoute)}</h2><p class="status">${safe(err.message)}</p><button data-route="lobby">Back to lobby</button></div>`;
    // Wire the fallback button without relying on the top navigation.
    view.querySelector('[data-route="lobby"]')?.addEventListener('click', () => navigate('lobby'));
  }
}

// Initialize shell state, wallet behavior, and the first lobby route.
async function init() {
  // Read the add-money button from the wallet popover.
  const addButton = document.getElementById('add-money-btn');
  // Wire play-token addition through the existing compatible player endpoint.
  addButton.onclick = async () => {
    // Start protected wallet mutation so validation errors become toasts.
    try {
      // Read the requested play-token amount from the wallet input.
      const amount = Number(document.getElementById('add-money-amount').value || 0);
      // Call the existing add-money helper, which refreshes the balance.
      await addFakeMoney(amount);
      // Refresh shell state so status rail counts stay current.
      await refreshShellState({ quiet: true });
      // Close the wallet popover after a successful play-token addition.
      document.querySelector('.wallet-menu')?.removeAttribute('open');
      // Show positive feedback for the completed wallet action.
      toast(`Added ${money(amount)} in play tokens.`, true);
    // Handle validation or API errors from the wallet action.
    } catch (err) {
      // Show the error message without interrupting the current route.
      toast(err.message);
    }
  };
  // Start protected bootstrapping so the app can still show a friendly error toast.
  try {
    // Preload global voice settings for game modules that announce events.
    await loadVoiceSettings();
    // Load casino state for status rail and initial lobby counts.
    await refreshShellState();
    // Load the human player balance into the premium wallet.
    await refreshBalance();
  // Handle initial state failures with a visible toast and client log.
  } catch (err) {
    // Show the startup error in the shell toast.
    toast(`Could not load state: ${err.message}`);
    // Record the initial load failure for Admin telemetry.
    await logClient('initial_state_error', { message: err.message });
  }
  // Render the lobby after shell bootstrapping has finished.
  navigate('lobby');
  // Poll shell state periodically for connection and player-count status.
  setInterval(() => refreshShellState({ quiet: true }), 30000);
}

// Start the premium shell controller.
init();
