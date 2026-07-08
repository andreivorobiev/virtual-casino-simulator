# Virtual Casino Simulator v9.1.0 Architecture

## Principle
Each game is isolated from other games. Shared concerns such as players, ledger, logs, bot controllers, autoplay sessions, settings, and admin telemetry live outside game modules.

## Key folders

```text
casino/
  app.py                 local HTTP server and route registration
  core/
    players.py           player accounts and balances
    ledger.py            all debits and credits
    logger.py            app, error, and client JSONL logs
    autoplay.py          server-registered autoplay sessions
    settings.py          persisted global settings, including audio
    state_store.py       atomic JSON/JSONL state helpers
  bots/
    profiles.py          bot accounts, capabilities, strategies, stakes
    controller.py        bot actions for supported games
    api.py               bot API routes
  games/
    roulette/            isolated Roulette API, engine, rules
    slots/               isolated Slots API and engine
    blackjack/           isolated Blackjack API and engine
    baccarat/            isolated Baccarat API and engine
    keno/                isolated Keno API and engine
    bingo/               isolated Bingo API and engine
web/
  app.js                 casino router and lazy-loaded game modules
  admin.html/admin.js    unauthenticated local admin console
  core/
    autoplay.js          client scheduler using server autoplay sessions
    bots.js              bot panel and play-round calls
    voice.js             global audio/voice client behavior
  games/                 isolated frontend game modules
```

## Bot architecture
Bots are controllers for player accounts. They are not embedded in game state and they are not owned by a game. The bot controller reads a bot's assigned strategy for a game, submits legal actions through game engines/API surfaces, and moves money through the same ledger used by humans.

## Autoplay architecture
Autoplay is client-scheduled but server-registered. The browser executes one atomic game action at a time. The server owns telemetry and stop_requested state. The browser checks the server state before each next action, so `/admin` can request Stop All.

## Audio architecture
Sound and voice settings are global. The settings are persisted under `data/settings/audio.json`, edited under `/admin -> Audio & Voice`, and consumed by `web/core/voice.js`. Games trigger sound events, but they do not own global sound configuration.

## Data layout

```text
data/
  players.json
  bots.json
  ledger.jsonl
  history.csv
  autoplay.json
  settings/audio.json
  games/roulette.json
  games/slots.json
  games/blackjack.json
  games/baccarat.json
  games/keno.json
  games/bingo.json
logs/
  app-YYYY-MM-DD.jsonl
  errors-YYYY-MM-DD.jsonl
  client-YYYY-MM-DD.jsonl
  test-runs/latest_results.json
```
