// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Provide isolated accessible card markup for future card and poker games.
// Requirements: CARD-002.

// Define stable rank labels for screen-reader descriptions.
const RANK_LABELS = { A: 'Ace', K: 'King', Q: 'Queen', J: 'Jack', '10': '10', '9': '9', '8': '8', '7': '7', '6': '6', '5': '5', '4': '4', '3': '3', '2': '2' };
// Define canonical suit metadata without relying on icon fonts.
const SUITS = {
  C: { name: 'clubs', symbol: '♣', color: 'black' }, // Describe clubs without an icon font.
  D: { name: 'diamonds', symbol: '♦', color: 'red' }, // Describe diamonds and their display color.
  H: { name: 'hearts', symbol: '♥', color: 'red' }, // Describe hearts and their display color.
  S: { name: 'spades', symbol: '♠', color: 'black' }, // Describe spades without an icon font.
};
// Map accepted suit spellings to compact canonical suit codes.
const SUIT_ALIASES = { C: 'C', CLUBS: 'C', '♣': 'C', D: 'D', DIAMONDS: 'D', '♦': 'D', H: 'H', HEARTS: 'H', '♥': 'H', S: 'S', SPADES: 'S', '♠': 'S' };

// Escape text before placing caller-owned values into generated markup.
function escapeHtml(value) {
  // Replace every HTML-sensitive character with its entity representation.
  return String(value ?? '').replace(/[&<>'"]/g, character => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' })[character]);
}

// Normalize compact strings and object payloads into one renderer shape.
export function normalizeCard(card) {
  // Reject missing card values before attempting to read fields.
  if (card === null || card === undefined || card === '') throw new TypeError('card is required');
  // Convert string cards such as AS, 10H, or A♠ into rank and suit parts.
  const source = typeof card === 'string' ? { rank: card.trim().slice(0, -1), suit: card.trim().slice(-1) } : card;
  // Normalize rank casing for face cards.
  const rank = String(source.rank ?? '').toUpperCase();
  // Resolve accepted suit symbols, initials, and names.
  const suitCode = SUIT_ALIASES[String(source.suit ?? '').toUpperCase()];
  // Reject values that are not standard playing-card ranks.
  if (!Object.hasOwn(RANK_LABELS, rank)) throw new TypeError(`Unsupported card rank: ${source.rank ?? ''}`);
  // Reject values that are not standard playing-card suits.
  if (!suitCode) throw new TypeError(`Unsupported card suit: ${source.suit ?? ''}`);
  // Read canonical suit metadata for labels and styling.
  const suit = SUITS[suitCode];
  // Return a stable immutable-friendly plain object for rendering adapters.
  return { rank, suit: suit.name, suitCode, symbol: suit.symbol, color: suit.color, label: `${RANK_LABELS[rank]} of ${suit.name}` };
}

// Retain only safe CSS class tokens supplied by a downstream game.
function classTokens(value) {
  // Filter whitespace-separated tokens so markup attributes cannot be injected.
  return String(value ?? '').split(/\s+/).filter(token => /^[a-zA-Z0-9_-]+$/.test(token)).join(' ');
}

// Render one semantic playing card or an accessible face-down card.
export function renderCard(card, options = {}) {
  // Treat explicit hidden state or the legacy ?? marker as a card back.
  const hidden = options.hidden === true || card === '??';
  // Build optional state classes without exposing unsafe caller text.
  const extraClass = classTokens(options.className);
  // Add a selected state that is communicated in both markup and CSS hooks.
  const selected = options.selected === true;
  // Render a labeled card back without exposing hidden card identity.
  if (hidden) return `<span class="playing-card playing-card--back${extraClass ? ` ${extraClass}` : ''}" role="img" aria-label="Face-down playing card"><span aria-hidden="true">◆</span></span>`;
  // Normalize and validate the visible card before generating markup.
  const normalized = normalizeCard(card);
  // Build stable classes for suit color and optional selected state.
  const classes = `playing-card playing-card--${normalized.color}${selected ? ' playing-card--selected' : ''}${extraClass ? ` ${extraClass}` : ''}`;
  // Render visible rank and suit as decorative text under one accessible label.
  return `<span class="${classes}" role="img" aria-label="${escapeHtml(normalized.label)}"${selected ? ' aria-current="true"' : ''}><span class="playing-card__rank" aria-hidden="true">${escapeHtml(normalized.rank)}</span><span class="playing-card__suit" aria-hidden="true">${escapeHtml(normalized.symbol)}</span></span>`;
}

// Render a responsive labeled group without introducing timers or animation state.
export function renderCardGroup(cards, options = {}) {
  // Require a real array so accidental strings are not rendered character by character.
  if (!Array.isArray(cards)) throw new TypeError('cards must be an array');
  // Use a caller-provided accessible name or a neutral default.
  const label = escapeHtml(options.label || 'Playing cards');
  // Apply shared card options consistently to every item in the group.
  const rendered = cards.map(card => renderCard(card, options.cardOptions || {})).join('');
  // Return a flex-based group whose companion CSS wraps at narrow widths.
  return `<div class="playing-card-group" role="group" aria-label="${label}">${rendered}</div>`;
}

// Report the user's reduced-motion preference without requiring a browser global.
export function prefersReducedMotion(matchMedia = globalThis.matchMedia) {
  // Avoid animation when the platform exposes and matches the standard media query.
  return typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches === true;
}
