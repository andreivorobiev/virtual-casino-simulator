// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Preserve reviewed technical acronyms while normalizing all-caps API identifiers for human-readable Admin copy.
const HUMAN_LABEL_ACRONYMS = Object.freeze({ api: 'API', csrf: 'CSRF', http: 'HTTP', id: 'ID', oauth: 'OAuth', ui: 'UI', url: 'URL' });
// Order transaction suffixes from most specific to generic so each ledger event receives one stable localized action.
const LEDGER_EVENT_LABEL_RULES = Object.freeze([
  ['ESCROW_REFUND_CREDIT', 'ledger.events.escrowRefundCredit'], // Explain returned table escrow before the generic refund rule can match.
  ['INSURANCE_CREDIT', 'ledger.events.insuranceCredit'], // Explain Blackjack insurance settlement credits.
  ['INSURANCE_DEBIT', 'ledger.events.insuranceDebit'], // Explain Blackjack insurance reservations.
  ['SETTLEMENT_CREDIT', 'ledger.events.settlementCredit'], // Explain canonical positive round settlement.
  ['SURRENDER_CREDIT', 'ledger.events.surrenderCredit'], // Explain partial stake returns after surrender.
  ['PAYOUT_CREDIT', 'ledger.events.payoutCredit'], // Explain a winning payout.
  ['REFUND_CREDIT', 'ledger.events.refundCredit'], // Explain an interrupted or released wager.
  ['CARD_PURCHASED', 'ledger.events.cardPurchased'], // Explain Bingo-card purchases.
  ['TICKET_PURCHASED', 'ledger.events.ticketPurchased'], // Explain Keno-ticket purchases.
  ['CALL_BET_PLACED', 'ledger.events.callBetPlaced'], // Explain a named Roulette call bet.
  ['REBET_PLACED', 'ledger.events.rebetPlaced'], // Explain replaying a prior Roulette bet.
  ['BET_PLACED', 'ledger.events.betPlaced'], // Explain canonical placed bets.
  ['WAR_WAGER_DEBIT', 'ledger.events.warWagerDebit'], // Explain the Casino War escalation wager.
  ['WAGER_DEBIT', 'ledger.events.wagerDebit'], // Explain an ordinary wager reservation.
  ['ANTE_DEBIT', 'ledger.events.anteDebit'], // Explain an opening ante reservation.
  ['CALL_DEBIT', 'ledger.events.callDebit'], // Explain a call reservation.
  ['PLAY_DEBIT', 'ledger.events.playDebit'], // Explain a play reservation.
  ['RAISE_DEBIT', 'ledger.events.raiseDebit'], // Explain a raise reservation.
  ['DOUBLE_DEBIT', 'ledger.events.doubleDebit'], // Explain a Blackjack double-down reservation.
  ['SPLIT_DEBIT', 'ledger.events.splitDebit'], // Explain a Blackjack split reservation.
  ['SPIN_DEBIT', 'ledger.events.spinDebit'], // Explain a Slots spin reservation.
  ['ESCROW_DEBIT', 'ledger.events.escrowDebit'], // Explain a table escrow reservation.
  ['INITIAL_DEBIT', 'ledger.events.initialDebit'], // Explain an opening multi-stage reservation.
  ['BET_DEBIT', 'ledger.events.betDebit'], // Explain a later-street bet reservation.
  ['TOKEN_GRANT', 'ledger.events.tokenCredit'], // Explain Admin-issued play-token grants.
  ['TOKENS_ADDED', 'ledger.events.tokenCredit'], // Explain self-service play-token additions.
  ['MONEY_ADDED', 'ledger.events.tokenCredit'], // Explain the legacy fake-money addition without exposing its enum.
  ['DEBIT', 'ledger.events.debit'], // Localize any future debit conservatively without exposing its raw enum.
  ['CREDIT', 'ledger.events.credit'], // Localize any future credit conservatively without exposing its raw enum.
  ['PURCHASED', 'ledger.events.purchased'], // Localize any future purchase conservatively.
  ['PLACED', 'ledger.events.placed'], // Localize any future placed action conservatively.
  ['ADJUSTMENT', 'ledger.events.adjustment'], // Explain a controlled token adjustment.
]);

// Export humanLabel to normalize API identifiers while preserving reviewed acronyms.
export const humanLabel = value => String(value || '').trim().replace(/[_-]+/g, ' ').split(/\s+/).filter(Boolean).map(token => HUMAN_LABEL_ACRONYMS[token.toLowerCase()] || `${token.charAt(0).toUpperCase()}${token.slice(1).toLowerCase()}`).join(' ');

// Export ledgerEventLabel so Admin can keep canonical event identity internal while rendering locale-backed operator copy.
export function ledgerEventLabel(value, game, translate) {
  // Normalize the server enum once so suffix classification stays deterministic.
  const canonical = String(value || '').trim().toUpperCase();
  // Select the first ordered suffix rule or fall back to a deliberately generic localized label.
  const rule = LEDGER_EVENT_LABEL_RULES.find(([suffix]) => canonical.endsWith(suffix));
  // Translate only a reviewed resource key so Russian Admin never falls back to an English source enum.
  const action = translate(rule ? rule[1] : 'ledger.events.other', {});
  // Preserve the game dimension through a readable product name without repeating raw transaction syntax.
  const gameLabel = humanLabel(game);
  // Join the stable game and localized action when the event belongs to a game.
  return gameLabel ? `${gameLabel} · ${action}` : action;
}
