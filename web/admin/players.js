// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Build the Admin Players & Bots tab behind explicit shell dependencies. (ADMIN-005, ADMIN-015)
export function createPlayersTab(dependencies) {
  // Capture the established shell helpers once so the renderer owns no ambient mutable state.
  const {
    api, emptyState, formatMoney, formatNumber, html, humanLabel, post, safe, setTitle, t, table, toast, view,
  } = dependencies;

  // Persist one bot controller card through the existing public mutation boundary.
  async function saveBot(button) {
    // Resolve the card that owns the submitted strategy and stake controls.
    const box = button.closest('.bot-edit');
    // Preserve the server-authored bot id carried by the stable action control.
    const id = button.dataset.bot;
    // Collect one strategy id per compatible game.
    const strategies = {};
    // Collect one numeric stake per compatible game.
    const stakes = {};
    // Index strategy selections by their game ids.
    box.querySelectorAll('.bot-strategy').forEach(select => { strategies[select.dataset.game] = select.value; });
    // Index normalized numeric stakes by their game ids.
    box.querySelectorAll('.bot-stake').forEach(input => { stakes[input.dataset.game] = Number(input.value || 1); });
    // Persist the complete bot controller configuration through the frozen route.
    await post(`/api/v1/bots/${id}`, {
      enabled: box.querySelector('.bot-enabled').checked,
      strategies,
      stakes,
    });
    // Preserve the established success acknowledgement.
    toast('Bot settings saved.', true);
    // Trigger the established non-blocking refresh of server-normalized values.
    playersBots();
  }

  // Seed each fixed practice opponent through its ledger-backed Admin action.
  async function fundPracticeOpponents() {
    // Submit the issue-scoped game allocation without accepting caller-selected wallets.
    await post('/api/v1/admin/bots/practice-opponents/fund', { game_id: 'texas_holdem_practice_table' });
    // Confirm completion with locale-owned copy.
    toast(t('players.practiceFunded', {}, 'admin'), true);
    // Reload balances and append-only audit activity after the funding action.
    await playersBots();
  }

  // Render one controller card with game-specific strategy and stake controls.
  function botCard(bot, capabilities, gameOptions) {
    // Preserve one strategy row per bot-compatible game.
    const controls = gameOptions.map((game) => {
      // Render the reviewed strategy options through the escaping template tag.
      const options = capabilities[game].strategies.map((strategy) => {
        // Keep the accepted selected-state projection for each strategy.
        const selected = bot.strategies?.[game] === strategy.id ? 'selected' : '';
        // Return one escaped strategy option without source-only whitespace.
        return html`<option value="${safe(strategy.id)}" ${selected}>${safe(strategy.label)}</option>`;
      });
      // Isolate the strategy control so the template remains reviewable.
      const strategyControl = html`<label>${safe(t('bots.strategy', { game }, 'admin'))} <select class="bot-strategy" data-game="${safe(game)}">${options}</select></label>`;
      // Isolate the stake control while preserving its existing defaults.
      const stakeLabel = safe(t('bots.stake', {}, 'admin'));
      // Normalize the accepted default stake before escaping it into the control.
      const stakeValue = safe(bot.stakes?.[game] || 5);
      // Preserve the exact stake input attributes and ordering.
      const stakeControl = html`<label>${stakeLabel} <input class="bot-stake" data-game="${safe(game)}" type="number" min="1" value="${stakeValue}"></label>`;
      // Preserve the exact row wrapper around both controls.
      return html`<div class="row">${strategyControl}${stakeControl}</div>`;
    });
    // Preserve the compact card topology without adding source-formatting whitespace.
    const identity = html`<b>${safe(bot.display_name)}</b>`;
    // Preserve the enabled control and accepted checked-state projection.
    const enabled = bot.enabled ? 'checked' : '';
    const toggle = html`<label><input type="checkbox" class="bot-enabled" ${enabled}>${safe(t('bots.enabled', {}, 'admin'))}</label>`;
    // Keep balance formatting delegated to the shared Admin formatter.
    const balance = html`<span class="badge">${formatMoney(bot.balance)}</span>`;
    // Keep the localized save label and stable automation hook together.
    const save = html`<button class="save-bot" data-bot="${safe(bot.bot_id)}">${safe(t('bots.save', { name: bot.display_name }, 'admin'))}</button>`;
    // Return the exact accepted card order.
    return html`<div class="bot-edit" data-bot="${safe(bot.bot_id)}"><div class="row">${identity}${toggle}${balance}</div>${controls}${save}</div>`;
  }

  // Return the established renderer contract used by the Admin dispatcher.
  async function playersBots() {
    // Set the localized title and helper line before requesting data.
    setTitle(t('players.title', {}, 'admin'), t('players.subtitle', {}, 'admin'));
    // Load the same dashboard envelope used by the accepted inline implementation.
    const data = await api('/api/v1/admin/dashboard');
    // Read only bot-capable catalog rows for controller controls.
    const capabilities = data.bot_capabilities || {};
    // Preserve API insertion order while excluding games without bot support.
    const gameOptions = Object.keys(capabilities).filter(game => capabilities[game].supports_bots);
    // Read the fixed practice-account allocation and append-only audit rows.
    const practiceAccounts = data.practice_opponents || [];
    const practiceActivity = data.practice_opponent_activity || [];
    // Map stable controller action ids to locale-owned audit labels.
    const practiceActionLabels = {
      fund_account: t('players.actionFund', {}, 'admin'),
      reserve_stack: t('players.actionReserve', {}, 'admin'),
      refund_stack: t('players.actionRefund', {}, 'admin'),
      settle_payout: t('players.actionPayout', {}, 'admin'),
    };
    // Build the player table independently so source reflow cannot alter output bytes.
    const playerRows = (data.players || []).map((player) => {
      // Keep player identity cells in their established order.
      const identity = html`<td>${safe(player.player_id)}</td><td>${safe(player.display_name)}</td>`;
      // Keep type and balance cells in their established order.
      const account = html`<td>${safe(player.type)}</td><td>${formatMoney(player.balance)}</td>`;
      // Return one compact table row.
      return html`<tr>${identity}${account}</tr>`;
    });
    // Keep player column labels localized by the Admin namespace.
    const playerHeadings = [
      t('players.id', {}, 'admin'), t('players.name', {}, 'admin'),
      t('players.type', {}, 'admin'), t('players.balance', {}, 'admin'),
    ];
    // Compose the player card from the reviewed heading and row projections.
    const playerCard = html`<section class="admin-card"><h3>${safe(t('nav.players', {}, 'admin'))}</h3>${table(playerHeadings, playerRows)}</section>`;
    // Build controller cards through the dedicated compact helper.
    const botCardList = (data.bots || []).map(bot => botCard(bot, capabilities, gameOptions));
    const botSection = html`<section class="admin-card"><h3>${safe(t('bots.controllers', {}, 'admin'))}</h3>${botCardList}</section>`;
    // Preserve fixed-account rows and localized balance wording.
    const accountRows = practiceAccounts.map((account) => {
      // Render seat and account identity with their accepted localized labels.
      const identity = html`<td>${safe(t('players.opponentSeat', { number: account.seat_id.split('_').pop() }, 'admin'))}</td><td>${safe(account.display_name)} (${safe(account.player_id)})</td>`;
      // Render the fixed caller policy and token balance.
      const policy = html`<td>${safe(t('players.automaticCaller', {}, 'admin'))}</td><td>${formatNumber(account.balance)} ${safe(t('players.playTokens', {}, 'admin'))}</td>`;
      // Preserve the stable practice-account browser hook.
      return html`<tr data-testid="practice-opponent-account">${identity}${policy}</tr>`;
    });
    // Preserve newest-first append-only activity rows.
    const activityRows = practiceActivity.slice().reverse().map((row) => {
      // Resolve the reviewed action label before composing the row.
      const action = practiceActionLabels[row.details?.controller_action]
        || humanLabel(row.transaction_type);
      // Keep timestamp, player, and optional round identity grouped.
      const identity = html`<td>${safe(row.ts)}</td><td>${safe(row.player_id)}</td><td>${safe(row.round_id || '—')}</td>`;
      // Keep the action and token amount grouped.
      const detail = html`<td>${safe(action)}</td><td>${formatNumber(row.amount)} ${safe(t('players.playTokens', {}, 'admin'))}</td>`;
      // Preserve the stable activity browser hook.
      return html`<tr data-testid="practice-opponent-activity">${identity}${detail}</tr>`;
    });
    // Preserve the populated activity table or its exact empty-state hook.
    const activity = practiceActivity.length ? table([
      t('players.time', {}, 'admin'), t('players.account', {}, 'admin'), t('players.round', {}, 'admin'),
      t('players.action', {}, 'admin'), t('players.amount', {}, 'admin'),
    ], activityRows) : emptyState(
      t('players.noPracticeActivity', {}, 'admin'),
      t('players.noPracticeActivityDetail', {}, 'admin'),
      'practice-opponent-empty',
    );
    // Compose the practice-opponent card without introducing visible whitespace.
    const practiceCopy = html`<div><h3>${safe(t('players.practiceTitle', {}, 'admin'))}</h3><p>${safe(t('players.practiceSubtitle', {}, 'admin'))}</p></div>`;
    // Keep the funding action's id and browser hook stable.
    const practiceButton = html`<button id="fund_practice_opponents" data-testid="fund-practice-opponents">${safe(t('players.fundPractice', {}, 'admin'))}</button>`;
    // Preserve the accepted copy-then-action layout.
    const practiceHeader = html`<div class="row">${practiceCopy}${practiceButton}</div>`;
    const accountTable = table([
      t('players.seat', {}, 'admin'), t('players.account', {}, 'admin'),
      t('players.policy', {}, 'admin'), t('players.balance', {}, 'admin'),
    ], accountRows);
    const activityHeading = html`<h3>${safe(t('players.practiceActivity', {}, 'admin'))}</h3>`;
    // Preserve the established practice-opponent card order.
    const practiceSection = html`<section class="admin-card" data-testid="practice-opponent-admin">${practiceHeader}${accountTable}${activityHeading}${activity}</section>`;
    // Replace the active tab in one atomic write using the exact accepted card order.
    view.innerHTML = html`${playerCard}${botSection}${practiceSection}`;
    // Bind every bot save action to its owning card after the DOM replacement.
    view.querySelectorAll('.save-bot').forEach(button => { button.onclick = async () => saveBot(button); });
    // Bind the explicit practice-account funding control.
    view.querySelector('#fund_practice_opponents').onclick = fundPracticeOpponents;
  }

  // Publish only the dispatcher-facing renderer.
  return playersBots;
}
