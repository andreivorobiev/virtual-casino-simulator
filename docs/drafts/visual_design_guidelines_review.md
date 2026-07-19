# Visual design guidelines review packet

Status: **draft for owner and external-reviewer review; not authoritative**.

This proposal expands the repository's existing visual language into an explicit,
reusable design system. It is grounded in the current `web/styles.css`,
`docs/visual_design_standard.md`, and `tests/visual/visual_matrix.json` rather
than introducing a disconnected redesign.

## Decisions requested from the owner

1. Preserve the current dark felt, warm gold, and restrained red visual identity.
2. Keep the stable path `docs/visual_design_standard.md`, retitle it **Visual
   Design Guidelines**, and expand it with the approved material below. This
   avoids a second competing visual authority and broken matrix references.
3. Approve a four-pixel spacing system and a 44 by 44 CSS-pixel minimum for
   primary touch actions.
4. Approve the current system-font strategy for UI and Georgia-style display
   typography, or request licensed/self-hosted brand fonts.
5. Keep dark theme as the sole production theme for the first release; require
   semantic tokens so a future accessible light theme remains possible.
6. Use one combined UX and visual-governance implementation ticket rather than
   creating parallel policy tickets.

---

# Proposed visual design guidelines

## 1. Purpose and visual character

Virtual Casino Simulator should feel polished, deliberate, and unmistakably a
toy casino simulator without imitating a real-money payment or gambling product.
The visual character is:

- **Cinematic but controlled:** deep backgrounds and focused stage lighting
  support gameplay without burying controls in decoration.
- **Warm and tactile:** felt greens, warm ivory text, gold accents, and measured
  depth evoke tables and physical game objects.
- **Clear before luxurious:** hierarchy, legibility, state, and balance accuracy
  always outrank ornament.
- **Consistent across games:** each game may own stage-specific imagery and
  mechanics while the shell, controls, panels, state language, and evidence
  hooks remain shared.
- **Fake-money explicit:** visual treatments must never resemble deposits,
  purchasing, cash balances, withdrawal, redemption, prizes, or transferable
  value.

## 2. Authority and relationship to UX

- The approved `docs/ux_design_guidelines.md` governs journeys, behavior,
  feedback, validation, recovery, accessibility, and trust.
- The expanded `docs/visual_design_standard.md` governs visual language,
  hierarchy, composition, tokens, components, responsive presentation, and
  visual evidence.
- `tests/visual/visual_matrix.json` is the executable inventory of required
  surfaces, states, locales, viewports, gates, and evidence.

Visual design cannot override behavioral UX. A visually attractive control that
is ambiguous, unstable, inaccessible, inaccurate, or unsafe is a failed design.

## 3. Design tokens

All shared visual decisions use semantic CSS custom properties. Components must
not depend on raw local colors when a semantic token exists.

### Color foundations

The current palette is retained as the starting point:

| Role | Current foundation | Intended use |
| --- | --- | --- |
| Canvas | `#030806` | Page background and deepest negative space |
| Felt dark | `#073d29` | Primary table and stage foundation |
| Felt light | `#0d5b39` | Stage gradients, selected felt regions |
| Panel | `rgba(3, 17, 12, 0.86)` | Standard controls and data panels |
| Panel strong | `rgba(4, 20, 15, 0.94)` | Modal, raised, or high-focus surfaces |
| Text primary | `#fff0cf` | Main readable content |
| Text muted | `#c7c0a3` | Secondary labels and explanatory content |
| Gold | `#ffd982` | Focus, selection, premium accent, key outlines |
| Gold deep | `#d5a743` | Gold gradients and pressed states |
| Action red | `#c6292d` | Primary user action |
| Action red deep | `#8f1419` | Primary action gradient and pressed state |
| Success | `#9cffbc` | Confirmed success with text/icon reinforcement |
| Error | `#ff9a9a` | Error with text/icon reinforcement |
| Admin blue | `#0b1b2a` | Admin-specific structural background |

These values are foundations, not automatic accessibility approval. Every
foreground/background pair must pass the required contrast check in its actual
composited state.

### Semantic color roles

Implementation should expose roles such as:

- `--color-canvas`
- `--color-stage`
- `--color-surface`
- `--color-surface-raised`
- `--color-border`
- `--color-border-subtle`
- `--color-text`
- `--color-text-muted`
- `--color-focus`
- `--color-action-primary`
- `--color-action-primary-hover`
- `--color-action-danger`
- `--color-selection`
- `--color-success`
- `--color-warning`
- `--color-error`
- `--color-disabled`

Gold is not a universal primary action color. Red identifies the main action;
gold identifies focus, selection, active navigation, achievement, or premium
emphasis. Green is not sufficient by itself to communicate a win or success.

### Contrast requirements

- Normal text: at least 4.5:1.
- Large text: at least 3:1.
- Focus indicators, component boundaries, and meaningful graphics: at least
  3:1 against adjacent colors.
- Disabled content remains readable but must not appear actionable.
- Text over images or felt textures requires a tested overlay or solid backing
  surface; text shadow alone is not a contrast strategy.

## 4. Typography

### Font families

- UI and body: `"Segoe UI", Inter, Arial, sans-serif`.
- Display and game titles: `Georgia, "Times New Roman", serif`.
- Monospace is limited to developer-facing diagnostics in authorized Admin or
  test evidence; it must not make player UI resemble raw tooling.

Display typography is reserved for brand, game titles, major outcomes, and
short ceremonial moments. Controls, forms, tables, errors, and instructions use
the UI family.

### Type scale

| Token | Size / line height | Typical use |
| --- | --- | --- |
| Display | 40 / 48 | Large game outcome or hero title |
| Heading 1 | 32 / 40 | Page or game title |
| Heading 2 | 24 / 32 | Major panel or stage section |
| Heading 3 | 20 / 28 | Component group heading |
| Body | 16 / 24 | Default reading and instructions |
| Body compact | 14 / 20 | Dense tables, histories, secondary data |
| Label | 12 / 16 | Short control labels and metadata |

- Do not use text smaller than 12 CSS pixels for user-facing content.
- Uppercase is limited to short labels and chips; never use it for paragraphs,
  errors, or instructions.
- Numeric wallet, stake, payout, and result values use tabular numerals where
  alignment matters.
- Important values may be visually dominant, but labels and units remain
  visible and understandable.

## 5. Spacing and sizing

Use a four-pixel base grid:

- `4`: micro separation and icon/text adjustment;
- `8`: tight internal component spacing;
- `12`: standard compact control spacing;
- `16`: default component padding and grid gap;
- `24`: panel and section separation;
- `32`: major section spacing;
- `48`: page and stage separation;
- `64`: exceptional hero spacing.

Do not introduce arbitrary one-off spacing values without documenting a layout
constraint that the shared scale cannot satisfy.

### Touch and control sizing

- Primary and high-frequency actions: minimum 44 by 44 CSS pixels.
- Standard inputs and secondary controls: minimum 40 CSS pixels high, with a
  44-pixel hit area where practical.
- Icon-only controls: minimum 44 by 44 hit area and an accessible name.
- Closely grouped targets preserve sufficient separation to avoid accidental
  activation.

## 6. Shape, border, and depth

### Radius scale

- `6px`: compact chips and small data elements.
- `10px`: buttons, inputs, standard controls.
- `16px`: cards and standard panels.
- `24px`: navigation containers and prominent raised panels.
- `999px`: pills, avatars, and circular medallions only.

### Borders

- Use subtle neutral borders for structural separation.
- Use gold borders for focus, active selection, or deliberate premium emphasis.
- Do not outline every nested region; spacing and surface contrast should carry
  most hierarchy.
- Error and success borders must include text or icon support.

### Shadows and overlays

- Shadows establish elevation, not decoration.
- Stage and modal shadows may be stronger than card and control shadows.
- Inner glows are limited to selected, active, or illuminated game objects.
- Backdrop blur must retain readable contrast and degrade gracefully when
  unsupported.
- Avoid stacking multiple heavy glows, borders, gradients, and shadows on one
  component.

## 7. Layout and hierarchy

The shared hierarchy remains:

1. persistent shell and simulator context;
2. game title and current phase;
3. dominant game stage;
4. primary controls and wager configuration;
5. outcome, history, statistics, bots, and autoplay data.

- The stage is visually stronger and wider than both support rails combined at
  the primary desktop viewport.
- One primary action is visually dominant within a decision region.
- Controls, status, and historical data are visibly separate.
- Essential actions never sit below a rail fold at required desktop viewports.
- Decorative content cannot displace the stage, stake, action, phase, or wallet.
- Alignment follows a consistent grid; near-aligned edges are treated as defects.

## 8. Component guidelines

### Buttons

- **Primary:** red gradient, high contrast, strong weight; one per immediate
  decision region.
- **Secondary:** dark or transparent surface with standard border.
- **Selected/active:** gold treatment with a non-color indicator where practical.
- **Danger:** visually distinct from primary and used only for destructive or
  irreversible Admin actions.
- **Disabled:** readable, clearly unavailable, no hover or pressed effect.
- **Busy:** stable width and position; show progress without replacing the
  accessible action name.

Buttons use specific action verbs. Decorative gold buttons must not compete with
the primary action.

### Inputs and selectors

- Persistent visible label above or beside the control.
- Units and constraints remain visible.
- Focus, error, success, disabled, and read-only states are distinct.
- Placeholder text is supplementary and never replaces a label.
- Numeric token inputs align values and preserve the required precision.

### Panels and cards

- Panels group one coherent purpose.
- A panel has a clear heading when its purpose is not self-evident.
- Internal sections use spacing before adding another border or background.
- Game catalog cards retain consistent title, category, status, and action
  placement even when translated text wraps.

### Navigation

- Active location uses gold plus shape/weight, not color alone.
- Navigation remains readable and reachable at all required viewports.
- Horizontal navigation scrolling, when necessary, uses an intentional themed
  treatment and preserves keyboard access.
- Admin navigation is visually and permission-wise distinct from player routes.

### Wallet

- Shared medallion/icon, `Play token balance` label, consistently formatted
  value, and secondary add-token action.
- The numeric balance is the dominant wallet element.
- No currency symbols, replacement glyphs, unlabeled numbers, or payment visual
  patterns.

### Status chips and badges

- Short, actionable, and subordinate to the title.
- Reserved space prevents stage movement during updates.
- Status color always includes text or icon meaning.
- Do not expose raw internal states.

### Tables, history, and statistics

- Labels and values align predictably.
- Numeric columns align on digits or decimals.
- Dense data uses the compact body style, not tiny text.
- Empty, loading, and error states occupy the same structural region.
- Tables adapt or intentionally scroll without causing page-level horizontal
  overflow.

### Dialogs and confirmations

- Title states the decision.
- Body explains effect and scope.
- Primary and cancel actions are clearly distinct.
- Initial focus, focus containment, Escape behavior, and focus restoration are
  defined.
- Destructive actions are not the default focused action.

### Toasts and inline messages

- Toasts announce transient confirmation.
- Errors requiring user action remain visible inline or at page level.
- Message color, icon, title, and recovery action form one consistent pattern.

## 9. Game-stage visuals

- Physical metaphors—cards, reels, wheels, balls, dice, chips, tables—must be
  recognizable, scaled consistently, and visually subordinate to accurate state.
- Game objects use shared primitives where they represent the same object.
- Selected, winning, losing, held, disabled, and settled objects have distinct
  states beyond color alone.
- Paylines, covered bets, card holds, and result markers must remain legible over
  felt, image, and motion backgrounds.
- The authoritative result remains inspectable after animation completes.
- Decorative realism must not imply real-money value or hide simulator framing.

## 10. Iconography and imagery

- Prefer code-native SVG or tested assets over font glyphs and emoji.
- Icons use consistent stroke weight, corner treatment, optical size, and
  alignment.
- Every unfamiliar or icon-only action has an accessible name and, where useful,
  a tooltip.
- Icons supplement text for critical actions; they do not replace it.
- Background imagery must remain low-contrast enough to protect content
  legibility.
- Avoid generic stock imagery, real currency, payment cards, cash, prizes,
  alcohol-centered imagery, or people presented as gambling winners.

## 11. Motion

### Duration scale

- 120 ms: hover, press, focus, and micro-feedback.
- 180 ms: standard component state change.
- 280 ms: panel, drawer, and route-level transition.
- 450 ms or longer: game-specific outcome motion only when pacing requires it.

Use smooth ease-out for entrances, ease-in for exits, and a consistent
standard easing for state changes. Avoid arbitrary per-game timing.

- Animate transform and opacity where practical.
- Essential controls never move during an active pointer or keyboard action.
- Motion must explain state and end at the authoritative result.
- Continuous decorative animation is restrained and pauses when offscreen.
- Reduced-motion mode removes simulated physical travel while preserving clear
  phase and outcome feedback.

## 12. Responsive visual rules

- Required viewports remain 1920×1080, 1440×900, 1024×900, and 390×844.
- Desktop uses the three-zone composition only while the stage remains dominant.
- Tablet and mobile stack panels in the documented UX order.
- Reading order, focus order, and visual order remain aligned.
- Wallet, phase, stake, action, and result do not collapse into unexplained icons.
- Text and controls wrap intentionally; clipping and page-level horizontal
  overflow are failures.
- Mobile does not inherit fixed desktop heights that create empty panel tails.

## 13. Localization and content fit

- English and Russian are required visual-validation locales.
- Components accommodate translated text expansion without overlapping,
  clipping, or hiding primary actions.
- Do not force long translated labels into all-uppercase or fixed-width chips.
- Numbers, decimals, grouping, dates, and percentages use locale-aware formats
  while preserving documented game conventions.
- Truncation requires a full accessible name and must never hide critical state,
  wager, payout, or action meaning.

## 14. Accessibility and visual states

Every interactive component defines:

- default;
- hover where applicable;
- focus-visible;
- active/pressed;
- selected;
- disabled;
- busy/loading;
- error;
- success where applicable; and
- reduced-motion behavior.

Focus indicators are visible on every supported surface and are not removed by
hover styling. Color-independent indicators are required for selection,
success, loss, warning, and error.

## 15. Visual evidence and review

Every browser-visible pull request lists:

- affected visual guideline IDs;
- visual matrix surfaces and state IDs;
- locales and viewports;
- component states exercised;
- exact branch and commit;
- `after_pass` evidence paths; and
- intentional exceptions with a linked follow-up issue.

Evidence fails when it contains resource keys, internal states, debug labels,
clipped essential content, horizontal overflow, nested primary scrolling, stale
wallet values, inconsistent precision, real-money framing, obscured focus, or an
older/known-failing build.

Shared-shell changes require evidence for the lobby and at least one affected
game or Admin surface. Behavioral claims require browser tests or traces in
addition to screenshots.

## 16. Forbidden visual patterns

- Multiple competing primary actions in one decision region.
- Gold applied to every control until hierarchy disappears.
- Equal visual weight for the stage, controls, and telemetry.
- Tiny uppercase text used for instructions or errors.
- Unlabeled icon-only critical actions.
- Font glyphs, emoji, or replacement-looking symbols used as wallet or critical
  status icons.
- Heavy nested borders, glows, gradients, and shadows on the same component.
- Text placed directly over busy imagery without a tested backing surface.
- Native nested scrollbars in primary game panels.
- Fixed desktop heights producing empty mobile panel tails.
- Animation that moves essential controls or delays safe recovery.
- Real currency, payment, cash-out, prize, or redemption imagery.
- Screenshots from an older or failing state presented as completion evidence.

## 17. Definition of visual done

A browser-visible change is visually complete only when:

1. it uses approved semantic tokens and shared components;
2. hierarchy preserves the stage, phase, wager, primary action, result, and
   wallet;
3. all required component states are designed and tested;
4. contrast, focus, target size, zoom, reduced motion, and color-independent
   meaning pass;
5. English and Russian pass at required viewports;
6. no clipping, collision, page-level overflow, nested primary scrolling, or
   stale state remains;
7. exact-commit `after_pass` evidence covers the affected matrix rows; and
8. the change also satisfies the canonical UX guidelines.

---

# Proposed ticket integration

Recommendation: update the proposed UX ticket to one combined governance issue
rather than create a competing visual-policy lane.

## Revised title

Establish canonical UX and visual design guidelines and enforce them for every browser-visible change

## Additional visual deliverables

1. Retitle and expand `docs/visual_design_standard.md` as the single Visual
   Design Guidelines authority while preserving its stable file path.
2. Reconcile current CSS variables into semantic color, typography, spacing,
   radius, depth, component-state, and motion tokens.
3. Add machine-readable visual token and component-state validation where
   practical.
4. Extend the visual matrix with guideline IDs and missing shared component
   states.
5. Add contrast, focus, target-size, localization expansion, overflow, and
   reduced-motion evidence gates.
6. Update engineering instructions, contributor guidance, issue forms, and the
   pull-request template to require both UX and visual conformance.
7. Add exact-commit reference examples demonstrating an accepted shared shell,
   lobby, one game, and Admin surface.

## Additional visual acceptance criteria

- One visual authority exists; no competing style guide remains.
- The current palette is converted into semantic roles and contrast-tested in
  actual composited states.
- Typography, spacing, sizing, radius, elevation, iconography, motion, and
  component states are explicitly defined.
- Shared components expose default, hover, focus, active, selected, disabled,
  busy, error, success, and reduced-motion states where applicable.
- Required viewport and EN/RU evidence demonstrates no clipping, collision,
  overflow, stale state, or lost hierarchy.
- The 42-versus-44-pixel touch-target rule is resolved in favor of one canonical
  value.
- CI and review instructions require both UX behavior evidence and visual
  presentation evidence for browser-visible changes.

## Review gate

Do not file or implement the combined ticket until the owner approves the visual
identity, document authority model, type and spacing systems, touch-target rule,
theme scope, and single-ticket approach.
