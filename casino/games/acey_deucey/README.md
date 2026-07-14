# Acey-Deucey / In-Between game module

This is the issue #149 isolated draft slice. It intentionally does not edit the shared catalog, router, shell, aggregate manifest, permanent requirements, compatibility matrix, visual matrix, central test discovery, or long-suite registry.

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

## #77 integration blockers

- Add `modules/acey_deucey.json` only through #77.
- Add aggregate `modules/module-manifest.json` revision only through #77.
- Add permanent requirements, compatibility-matrix entries, visual-matrix rows, browser acceptance, and long-suite discovery only through #77.

