# Virtual Casino Simulator Architecture

Describes the architecture of the current packaged release. The authoritative version is
`modules/module-manifest.json` (`application`), mirrored by `pyproject.toml`.

For the per-release record see `RELEASE_NOTES.md`; for contributor workflow see `AGENTS.md`,
`CONTRIBUTING.md`, and `ENGINEERING_PRACTICES.md`.

## Principle

Each game is isolated from every other game. Shared concerns — players, wallet ledger, storage,
authentication, sessions, logs, bot controllers, autoplay, settings, admin telemetry, and
operations — live outside game modules and are consumed through `casino/core/`.

Game isolation is mechanically enforced: `scripts/validate_module_boundaries.py` scans real Python
and JavaScript imports and fails on any cross-game import.

## Catalog is descriptor-driven

There is no hard-coded game list anywhere. Each game ships a descriptor at `modules/<id>.json` that
owns its id, route prefix, backend callable, frontend export, and contract list.

- `casino/config.py` `load_game_catalog()` discovers descriptors by globbing `modules/*.json` and
  fails startup on id drift or duplicate ids.
- `casino/games/registry.py` registers backend routes from those descriptors.
- `web/app.js` lazy-loads each frontend module from the same catalog served by the API.
- `scripts/validate_game_catalog.py` verifies every descriptor's callable, frontend export, i18n
  resources, and contracts exist.

Adding a game therefore never requires editing an application-level registry. The full per-game
integration checklist is in `docs/game_expansion_integration_sequence.md`.

## Entry points

Two HTTP adapters share one route registry (`ROUTER` in `casino/app.py`):

- **`casino/app.py`** — development server (`ThreadingHTTPServer`). Started by `run.py`,
  `Run Virtual Casino.bat`, and `Run Virtual Casino.command`. Intended for loopback use.
- **`casino/wsgi.py`** — production WSGI adapter. Reuses the same router without starting the
  development server, and adds the deployment request-integrity policy: exact-Origin checking,
  per-session double-submit CSRF, strict forwarding-header handling, body caps, rate limiting, and
  the response security-header set (implemented in `casino/core/security.py`). Served by gunicorn
  behind nginx; see `deploy/`.

`casino/config.py` `validate_bootstrap_for_startup()` refuses to start on a non-loopback bind while
known development credentials or short digest keys are still configured.

## Key folders

```text
casino/
  app.py                 route registry + development HTTP server
  wsgi.py                production WSGI adapter and request-integrity policy
  router.py              route dispatch; binds player identity from the session
  config.py              runtime config, startup validation, game-catalog discovery
  admin.py               admin console API surface
  errors.py              typed error taxonomy with stable codes
  module_versions.py     module revisions loaded from modules/module-manifest.json
  core/
    storage.py           StorageProvider abstraction: JsonStorageProvider, MySQLStorageProvider
    ledger.py            all debits and credits
    simple_game.py       shared exactly-once wager/settle core for newer games
    players.py           player accounts and balances
    auth.py              users, roles, sessions, guest trials, admin authorization
    security.py          origin/CSRF/forwarding policy, security headers, rate limiting
    request_player.py    strips client-authored outcome/RNG/wallet fields from game requests
    validation.py        amount and JSON-number validation
    state_store.py       atomic JSON/JSONL state helpers
    mysql_migrations.py  checksummed, fail-closed schema migration runner
    recovery.py          authenticated encrypted export/restore
    cards.py, poker.py   shared card and hand-evaluation primitives
    autoplay.py, settings.py, logger.py, history.py, receipts.py, feedback.py, ...
  bots/
    profiles.py          bot accounts, capabilities, strategies, stakes
    controller.py        bot actions for supported games
    practice_opponents.py practice-table opponent wallets
    api.py               bot API routes
  games/
    <game_id>/           one isolated package per catalog id (modules/*.json); every package has
                         api.py and engine.py, plus rules.py and/or service.py where needed
web/
  index.html             application shell
  app.js                 router; lazy-loads game modules from the served catalog
  sw.js                  service worker (versioned precache, excludes /api/ and /admin)
  admin.html/admin.js    admin console (requires an authenticated Admin session)
  styles.css             shared stylesheet
  core/
    api.js               fetch wrapper: CSRF header, offline fail-closed, error envelopes
    i18n.js              manifest-driven i18n with per-game lazy domains
    pwa.js               install/update lifecycle and offline boundary
    ui.js                shared toast, escaping, card rendering
    autoplay.js, bots.js, voice.js, motion.js, dice.js, feedback.js
  games/                 isolated frontend game modules, one per catalog id
  i18n/<locale>/         en-US and ru-RU resources, including per-game domains
```

Supporting trees: `contracts/` (OpenAPI + compatibility artifacts), `docs/` (requirements,
governance, per-game docs), `tests/`, `scripts/` (validators and tooling), `migrations/mysql/`,
`deploy/` (nginx, systemd, gunicorn, edge policy), `mobile/` (Capacitor lane), `site/` (marketing).

## Persistence

Storage is behind one `StorageProvider` interface (`casino/core/storage.py`) with two
implementations selected by configuration:

- **`JsonStorageProvider`** — default. JSON/JSONL files under `data/`, with atomic temp-file
  replacement, a cross-process wallet lock, and a write-ahead action journal
  (`data/ledger_actions.json`) that is replayed on startup so an interrupted wallet mutation is
  recovered rather than lost or duplicated.
- **`MySQLStorageProvider`** — optional (`pip install .[mysql]`). Wallet mutations run as one
  transaction with `SELECT ... FOR UPDATE` on the player row; exactly-once settlement is enforced by
  a unique action-identity index. Schema changes go through `casino/core/mysql_migrations.py`, which
  verifies a checksummed migration catalog and uses a fail-closed clean/applying/dirty state machine
  under an advisory lock. `casino/core/mysql_pool.py` provides one lazy bounded physical-connection
  pool per process; request-scoped leases roll back unfinished work, reset session state, validate
  without reconnecting, and either return a healthy session or discard it.

## Money and settlement

All balance changes go through `casino/core/ledger.py`. Newer games build on
`casino/core/simple_game.py`, which owns exactly-once wager and settlement: the round's entropy is
committed **inside** the wager's ledger row, so a retry after a lost response replays the original
outcome instead of redrawing it, and settlement uses storage-atomic `debit_once`/`credit_once` keyed
by a durable action id.

> **Known gap.** The six original games (roulette, slots, blackjack, baccarat, keno, bingo) and
> several other early modules predate this core and still settle with non-idempotent
> `ledger.debit`/`ledger.credit` and an unlocked read-modify-write cycle. Migrating them is tracked
> in the issue tracker; new games must use the shared core.

## Server authority

Outcomes are always computed server-side. `casino/core/request_player.py` `sanitize_game_intent()`
strips client-authored `outcome`, `payout`, `seed`, `rng`, `cards`, `deck`, and `dice` fields from
every `/api/v1/games/` request body, and `casino/router.py` overwrites `player_id` with the
session-bound identity before dispatch. The generated
`contracts/compatibility/server-authority-matrix.json` records this per module and is validated by
regeneration in `scripts/validate_contracts.py`.

## Authentication and authorization

`casino/core/auth.py` owns users, roles, sessions, and guest trials. Passwords are PBKDF2-hashed;
session and one-time tokens are compared in constant time, and invitation/reset tokens are stored
only as keyed HMAC verifiers.

The endpoints in `PUBLIC_API_PATHS` (login, guest, signup, invitation redemption, enrollment
policy, OAuth provider list, `/healthz`), plus the exact OAuth start/callback route shapes matched
by `auth.is_public_api_path()`, are anonymous. Everything else requires a session, and
`/api/v1/admin/` and `/api/v2/admin/` — including the admin console's API surface — require an Admin
role via `auth.require_admin`.

## Bot architecture

Bots are controllers for ordinary player accounts. They are not embedded in game state and are not
owned by a game. The controller reads a bot's assigned strategy, submits legal actions through the
same game APIs humans use, and moves money through the same ledger.

## Autoplay architecture

Autoplay is client-scheduled but server-registered. The browser executes one atomic game action at a
time; the server owns telemetry and `stop_requested`. The browser re-checks server state before each
action, so `/admin` can request Stop All.

## Audio architecture

Sound and voice settings are global, persisted under `data/settings/audio.json`, edited in
`/admin -> Audio & Voice`, and consumed by `web/core/voice.js`. Games trigger sound events but do not
own global sound configuration.

## Data layout (JSON provider)

Runtime state is created on first run; it is not part of the source tree.

```text
data/
  players.json           accounts and balances
  bots.json              bot profiles
  ledger.jsonl           append-only debits and credits
  ledger_actions.json    write-ahead action journal for exactly-once recovery
  history.csv            round history export
  autoplay.json          registered autoplay sessions
  auth/                  users, sessions, invitations, one-time tokens
  settings/audio.json    global audio and voice settings
  games/<game_id>.json   shared per-game state (used by the bot controller)
  games/<game_id>/       per-game, per-player state
logs/
  app-YYYY-MM-DD.jsonl
  errors-YYYY-MM-DD.jsonl
  client-YYYY-MM-DD.jsonl
  test-runs/latest_results.json
```

## Play-token status

Balances, chips, and ledger entries are play tokens with no cash value. There is no payment,
purchase, deposit, or withdrawal path anywhere in the application. See `README.md` and
`docs/legal/`.
