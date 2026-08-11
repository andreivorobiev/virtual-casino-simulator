// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Enumerate every governed OpenAPI source so one Swagger URL exposes the complete published API. (API-003)
const contractFiles = Object.freeze([
  // Group the first reviewed contracts without inventing runtime discovery or hidden endpoints.
  'acey_deucey.v1.yaml', 'admin.v1.yaml', 'admin-users.v2.yaml', 'andar_bahar.v1.yaml', 'auth.v2.yaml', 'autoplay.v1.yaml', 'baccarat.v1.yaml', 'big_six_wheel.v1.yaml',
  // Continue the complete alphabetic inventory through the core casino and wheel surfaces.
  'bingo.v1.yaml', 'blackjack.v1.yaml', 'bots.v1.yaml', 'boule.v1.yaml', 'caribbean_stud.v1.yaml', 'casino.v1.yaml', 'casino_holdem.v1.yaml', 'casino_war.v1.yaml',
  // Include every remaining C and D game contract through the same immutable namespace.
  'chuck_a_luck.v1.yaml', 'coin_pusher.v1.yaml', 'color_wheel.v1.yaml', 'craps.v1.yaml', 'crown_and_anchor.v1.yaml', 'daily_draw_lab.v1.yaml', 'deuces_wild_video_poker.v1.yaml', 'double_bonus_video_poker.v1.yaml',
  // Include game, feedback, guest, and identity contracts without enabling request execution.
  'dragon_tiger.v1.yaml', 'fan_tan.v1.yaml', 'faro.v1.yaml', 'feedback.v2.yaml', 'four_card_poker.v1.yaml', 'guest-trials.v2.yaml', 'hi_lo.v1.yaml', 'invitations.v2.yaml',
  // Include the J-through-O contract group in the selector's deterministic source order.
  'jacks_or_better_video_poker.v1.yaml', 'joker_poker.v1.yaml', 'keno.v1.yaml', 'ledger.v1.yaml', 'let_it_ride.v1.yaml', 'lucky_grid.v1.yaml', 'marble_race.v1.yaml', 'mississippi_stud.v1.yaml', 'multi_hand_video_poker.v1.yaml', 'one-time-tokens.v2.yaml', 'operations.v1.yaml',
  // Include every P and R contract while preserving the repository filenames verbatim.
  'over_under_7.v1.yaml', 'pachinko.v1.yaml', 'pai_gow_poker.v1.yaml', 'pattern_draw.v1.yaml', 'players.v1.yaml', 'plinko.v1.yaml', 'poker_dice.v1.yaml', 'red_dog.v1.yaml', 'roulette.v1.yaml',
  // Complete the selector with all S-through-U governed contracts.
  'scratch_cards.v1.yaml', 'self-service-batch.v2.yaml', 'sic_bo.v1.yaml', 'slots.v1.yaml', 'teen_patti.v1.yaml', 'texas_holdem_practice_table.v1.yaml', 'three_card_poker.v1.yaml', 'transactional-mail.v2.yaml', 'trente_et_quarante.v1.yaml', 'user-settings.v2.yaml',
]);
// Convert reviewed filenames into Swagger selector entries under the traversal-safe public namespace.
const contracts = Object.freeze(contractFiles.map(filename => ({ name: filename.slice(0, -5), url: `/openapi/${filename}` })));
// Create one read-only Swagger explorer with the official Topbar selector for every contract.
window.ui = SwaggerUIBundle({ urls: contracts, 'urls.primaryName': contracts[0].name, dom_id: '#swagger-ui', deepLinking: true, docExpansion: 'none', defaultModelsExpandDepth: 1, supportedSubmitMethods: [], validatorUrl: null, presets: [SwaggerUIBundle.presets.apis, SwaggerUIStandalonePreset], plugins: [SwaggerUIBundle.plugins.DownloadUrl], layout: 'StandaloneLayout' });
