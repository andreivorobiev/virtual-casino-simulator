# Slots

Issue #471 Split A corrects the shipped Slots economics while preserving the frozen `/api/v1`
route and accepted line/stake vocabulary. Permanent requirement `SLOT-036` governs this bounded
delivery. The module version is `9.3.0`.

## Authoritative rules

- The server owns the line paytable, scatter values, four-spin feature award, and progressive
  configuration; the browser renders the additive runtime configuration instead of embedding a
  second rules model.
- Accepted line counts remain exactly 1, 3, 5, 9, and 20. The line bet remains a finite,
  cent-normalized value from 0.01 through 1,000,000 play tokens.
- Three scatters award four free spins and no direct token return. Four scatters return 1x the line
  bet and five scatters return 5x the line bet.
- WILD substitutes for ordinary symbols. Five SEVEN with WILD substitution can win the progressive
  only on an eligible paid spin.

## Progressive and feature basis

Exactly one constant-size progressive meter is retained. It starts and resets at 200 play tokens.
Only a paid spin at exactly 20 lines and a 1.00 line bet contributes one percent of its paid cost
and can win the meter. Other paid setups and every free spin leave it unchanged. Switching controls
away from and back to the qualifier neither transfers nor discards its value.

A feature bank is locked to the server-owned line and stake basis of the paid trigger. Every
feature spin and retrigger uses that basis with zero cost, so a later request cannot raise its
ordinary or scatter return. Pre-upgrade banks use trusted paid-trigger history when available and
otherwise adopt the conservative legal minimum.

## Settlement evidence

The existing route gives its debit, engine result, optional payout credit, history entry, and
response one current round identifier. Browser-free tests reconcile paid cost, ordinary line
return, scatter return, progressive return, and finite maximum-stake settlement through those
existing route boundaries.

The governed Long lane runs six real-engine scenarios: nonprogressive 0.01-line-bet play at every
supported line choice and the exact 20-line by 1.00 qualifier. Each scenario completes one million
paid spins, drains the complete triggered and retriggered feature chain after every paid spin,
closes confidence blocks only after that drainage, and uses paid cost as its denominator. The
nonprogressive one-line best strategy and the qualifying strategy have separate predeclared
near-92-percent bands, and every 99 percent upper confidence bound must remain below 1.

## Browser evidence

The `slots` visual surface covers idle, spinning, win, multi-win, bonus, invalid line bet, reduced
motion, zoomed, restored route, and repeat-available states in `en-US` and `ru-RU` at desktop
primary, desktop compact, tablet, and mobile viewports. Evidence verifies exact localized
paytable/scatter/progressive copy, immediate qualifier feedback, preserved result/history text,
payline geometry, autoplay/repeat behavior, and absence of clipping or page-level overflow.

The remaining provider transaction dependency is tracked separately under issue #430 Phase0c;
this Split A change does not alter that boundary.
