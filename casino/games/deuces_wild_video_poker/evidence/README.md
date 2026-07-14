# Deuces Wild Video Poker evidence boundary

This directory may hold issue #92 evidence, but its existence is not acceptance evidence. The isolated worker and the #77 integration owner use different evidence boundaries.

## Focused worker evidence

Focused evidence may demonstrate:

- deterministic full-pay classification, including natural royal flush, four deuces, wild royal flush, five of a kind, and all lower paying outcomes;
- deal, hold, and draw `action_id` replay plus conflicting-payload rejection;
- one wager debit and at most one payout credit after retry or simulated recovery;
- hostile body or query `player_id` values losing to the authenticated player binding in an isolated router test;
- reload-safe active holds and settled recent rounds;
- English/Russian key parity, absence of visible hard-coded English, JavaScript syntax, and timer cleanup;
- module-boundary and comment-density compliance.

Store command output or structured results under a clearly named `focused/` path with the branch, commit, command, timestamp, and result. Any isolated-harness screenshot must be labeled `diagnostic_only`; it is neither `after_pass` nor evidence that the catalog, authenticated shared shell, wallet, canonical route, or shared visual row is accepted.

## Formal `after_pass` evidence

Only #77 may classify visual evidence as `after_pass`, and only after the descriptor has an aggregate module revision, the permanent requirements and compatibility metadata exist, the visual row is registered, and the game runs through the real authenticated backend and shared shell.

Formal evidence must record:

- exact branch and commit;
- evidence class `after_pass`;
- surface `deuces_wild_video_poker` or the existing `shell_lobby` surface;
- one of `ready`, `choose_holds`, `settled`, `reduced_motion`, or `route_restored` for the game surface;
- locale `en-US` or `ru-RU`;
- viewport `desktop_primary`, `desktop_compact`, `tablet`, or `mobile`;
- screenshot or artifact path;
- test command and result;
- loopback listener PID and ephemeral non-8765 port, followed by verified listener closure.

The final evidence set must cover both locales and all four game viewports. It must also prove lobby search/category discovery, direct navigation, reload, Back and Forward restoration, session-bound hostile-player rejection, ledger replay safety, and one catalog-discovered long-driver scenario. Visible resource keys, debug state names, mojibake, real-money wording, clipped controls, stale wallet values, or unclosed listeners invalidate the evidence.

Port `8765` and shared `data/` belong to the user's live Casino session and are never evidence fixtures. No evidence workflow may stop, reset, copy over, clean, or otherwise mutate them.
