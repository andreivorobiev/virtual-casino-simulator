# Visual Design Standard

Status: authoritative for production browser UI and visual-review evidence.

This standard defines the reusable visual rules for the shared casino shell, authentication, lobby, all game screens, and Admin. It supersedes one-off mockup decisions when they conflict. The executable coverage inventory is [`tests/visual/visual_matrix.json`](../tests/visual/visual_matrix.json).

## Review baseline

Every browser-visible change must identify the affected matrix surface, states, locales, and viewports before implementation. The required standard viewports are:

- Desktop primary: 1920 by 1080.
- Desktop compact: 1440 by 900.
- Tablet: 1024 by 900.
- Mobile: 390 by 844.

English (`en-US`) and Russian (`ru-RU`) are the required visual-validation locales. Text must be real user-facing copy in evidence; resource keys, fallback identifiers, and debug labels are failures.

## Surface hierarchy

The shared shell establishes brand, navigation, current-user wallet, locale, profile/logout, and persistent simulator status. A game screen then uses this order:

1. User-facing game title and current phase.
2. Dominant game stage containing the table, board, cards, reels, or draw surface.
3. Control rail containing actions and configuration.
4. Data rail containing bets, outcomes, history, statistics, paytables, bots, or autoplay status.

At standard desktop viewports, the game stage must be wider and visually stronger than both support rails combined. Controls, status, and data use distinguishable borders, headings, spacing, and surface treatments; they must not read as one undifferentiated developer form.

## Wallet and play-token presentation

The wallet is a single reusable shell component, not ad hoc text. It must include:

- A reliable code-native icon or medallion that renders consistently without depending on a special-font glyph.
- A legible `Play token balance` label.
- A visually dominant formatted numeric value for the authenticated current user.
- An add-token affordance that is visually secondary to the balance.

The numeric value must not depend on a diamond, replacement character, mojibake sequence, currency symbol, or icon font to communicate meaning. UI copy must say `play tokens`, `token balance`, `wager`, `win`, or `payout` as appropriate. It must not say deposit, cash, dollars, purchase, withdraw, money balance, or imply real value.

## Scrolling and viewport fit

The browser page, game layout, and a rail must not become competing primary scroll containers.

- At the desktop primary viewport, the wallet, game title/phase, primary wager selector, primary action, and full game stage must be visible without scrolling a support rail.
- Desktop compact validates graceful compression or an intentional responsive transition without horizontal overflow; it must not create cramped or clipped three-zone panels.
- A long support rail may own one intentional vertical scroll surface for advanced controls or historical data.
- Lists, tables, histories, and paytables inside a scrolling rail expand into that rail at desktop; nested primary scrollbars are forbidden.
- Intentional scroll surfaces use the shared thin themed scrollbar, preserve wheel and touch panning, and are keyboard focusable with a visible focus indicator and accessible region name.
- Tablet and mobile use document scrolling with vertically stacked panels. Desktop `100%` row containment must not create empty tails in stacked panels.
- Page-level horizontal overflow is forbidden at every matrix viewport.

## Render stability and containment (hard rules)

These two rules are permanent requirements, not guidance. They are enforced by
Browser cases and by runtime telemetry, and a surface that violates either one
fails review regardless of how it looks in a static screenshot.

**Containment (UX-026, enforced by `BR-LAYOUT-CONTAIN-001`).** Every component
renders fully inside the viewport or a designed scroll region at every supported
viewport from 320 CSS pixels wide upward. Meaningful content — controls,
labels, cards, table cells — must never be clipped by a hidden-overflow
ancestor or extend past the viewport edge. Fixed-geometry boards (for example
the Roulette hit-map) scale continuously to their measured shell; discrete
breakpoint scale ladders are forbidden because every gap between breakpoints is
a clipping defect. Grid and flex tracks that can receive long or translated
content use `minmax(0, …)` or `min-width: 0` so localization can never force a
track past its container. The application shell audits settled renders and
resizes with `auditLayoutContainment` and reports confirmed loss to Admin
telemetry as a bounded `layout_overflow` client-log event, so violations in
real sessions are visible without a bug report.

**Action stability (UX-027, enforced by `BR-ACTION-STABILITY-001`).** An
in-game action never reloads the document, never changes the route, and never
sends the player back to the top. Same-route full-root rerenders preserve the
route outlet's scroll offsets, the scroll position of every internal rail, and
keyboard focus on the same control whenever it carries a stable identity; when
the control disappears or is disabled, focus parks on the focusable game region
rather than the document body. Scroll resets to the top only when navigation
intentionally changes the route. Game modules inherit this guarantee from the
shell's route-outlet render interception and must not add competing scroll or
focus resets of their own.

## Phase and status language

Headers and status chips show only information a player can act on or understand: accepting wagers, spinning, revealing, awaiting a decision, drawing, settled, won, or complete. Internal state names, translation keys, reserved implementation slots, test IDs, API fields, and debug labels are forbidden in user-facing UI.

Status chips must be concise and subordinate to the title. They must not overlap or push the game stage below the usable desktop viewport. Live phase changes must update reserved regions without resizing the stage.

## Controls, status, and data

- Primary actions use the shared red treatment and retain stable placement across phases.
- Selected chips, bets, cards, numbers, or options use a clear selected state beyond color alone when practical.
- Configuration controls are grouped and labeled; dense settings must not resemble raw debug tooling.
- Status uses compact chips, meters, or reserved messages.
- Data uses rows, tables, charts, or cards with aligned labels and values.
- Disabled controls remain readable and explain their current unavailability through surrounding phase context.

## Responsive behavior

Desktop uses the three-zone composition when the center stage can remain dominant. Below the shared breakpoint, panels stack in control, stage, data order unless a game-specific user journey documents another order. Text, chips, and tables wrap without clipping, and the wallet remains complete rather than collapsing into an unexplained symbol.

Adopted touch-target decision (issue #283): the minimum hit size for primary and high-frequency controls is 42 CSS pixels, which exceeds the WCAG 2.2 AA target-size minimum of 24 CSS pixels; 44 CSS pixels is recommended for newly designed surfaces where layout allows. This resolves the 42-versus-44 conflict between this standard and the draft guidelines in favor of the shipped 42-pixel floor that all remediated controls already meet. Small visual controls such as checkboxes satisfy the minimum through an enlarged clickable parent row rather than by inflating the glyph.

## Accessibility and interaction

- Interactive elements use semantic controls and stable accessible names.
- Scroll regions are keyboard reachable and have a visible focus style.
- Color is not the only signal for current phase, selection, success, or failure.
- Animation respects transform/opacity stability rules and does not move essential controls.
- Locale changes preserve the active route and in-progress game state.

## Evidence protocol

Evidence is classified as `before_failure` or `after_pass`.

- `before_failure` evidence documents a defect and can never be used as acceptance proof.
- `after_pass` evidence must come from the tested branch or copied deployment at a named matrix viewport and locale.
- Each browser-visible PR lists matrix surface IDs, state IDs, locale, viewport ID, and evidence path.
- Evidence containing visible resource keys, debug labels, clipped essential controls, native nested scrollbars, stale balance data, or real-money wording is a failure even if automated interaction tests pass.
- At least the lobby and one affected game or Admin surface require `after_pass` images when shared shell/layout behavior changes.

## Forbidden anti-patterns

- Native full-width scrollbars inside cramped side panels.
- A scrollable page containing separately scrolling primary control and data panels.
- Nested scroll containers for primary rail content.
- Essential actions below a rail fold at a standard desktop viewport.
- Wallet values represented by a replacement-looking glyph, currency mark, or unlabeled number.
- Debug keys, internal phase names, placeholder status, or test data labels presented to users.
- Header ribbons colliding with the table, board, cards, reels, or draw surface.
- Equal visual weight for stage, controls, and telemetry.
- Responsive layouts with large empty panel tails, clipped content, or horizontal page overflow.
- Screenshots from an older branch or known-failing state presented as completion evidence.

## Pull-request gate

A browser-visible PR is reviewable only when it links this standard, names its matrix rows, reports requirement IDs and module versions, includes the required `after_pass` evidence, and records browser validation. Any intentional exception must be documented in the PR with a follow-up issue; exceptions cannot waive fake-money language, accessibility, current-user wallet accuracy, or absence of visible debug/resource keys.
