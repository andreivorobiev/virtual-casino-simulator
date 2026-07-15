# Acey-Deucey / In-Between game module

Issue #149 is catalog-integrated through shared sequencing issue #77. The game remains isolated while its canonical descriptor, requirements, compatibility, visual, and discovered-test metadata live in the shared integration surfaces.

## Distinctness proof

Acey-Deucey is implemented as a distinct countable proposal from existing Red Dog and Hi-Lo:

- Hi-Lo exposes one card, asks for higher/lower, and wagers before the hidden card is known.
- Red Dog uses six decks, an ante before the boundary cards, spread odds, pair/consecutive automatic outcomes, and an optional matching raise.
- This profile deals two free exposed boundary cards first, then the player either passes or chooses a wager before the third card is revealed. Strict inside pays even money plus returned stake. Outside ranks and boundary ties lose the play wager.

# Rules profile

- One standard deck from `casino.core.cards`.
- Two boundary cards are exposed before the player risks tokens.
- The third card is prepared privately at deal time for reload safety.
- A strict rank inside the two boundaries returns `2x` total.
- A third card matching either boundary is a `boundary_tie` and returns `0x`.
- A third card outside the boundaries returns `0x`.
- Equal or adjacent boundaries have zero inside ranks; the player may pass.

## #77 integration

- `modules/acey_deucey.json` owns version `1.0.0`, sort order `260`, and catalog discovery.
- Permanent requirements `AD-001` through `AD-005` cover rules, private state, ledger actions, localization, and evidence.
- Compatibility, visual-matrix, browser, restart, and Long Suite 100 evidence are centrally traceable.
