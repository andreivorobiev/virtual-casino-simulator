// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// TiltSeven "Neon Pit" brand definition. Adding another brand is a copy of this file.

// Export the immutable TiltSeven brand descriptor consumed by core/brand.js.
export const tiltseven = {
  // Identify the brand for diagnostics and the optional data-brand root hook.
  id: "tiltseven",
  // Provide the visible wordmark shown in the shell brand lockup.
  name: "TiltSeven",
  // Provide the compact mark glyph rendered inside the brand badge.
  mark: "7",
  // Provide the lobby hero venue name, kept distinct from the app wordmark above.
  venue: "The Neon Pit",
  // Provide the design language name for internal reference only.
  direction: "Neon Pit",
  // Map every themeable CSS custom property to this brand's value.
  tokens: {
    // Drive every emphasis colour from the brand accent.
    "--brand": "#ff3b6b",
    // Provide the deeper brand shade for gradients and pressed states.
    "--brand-strong": "#e01e52",
    // Provide the secondary electric accent for positive and live cues.
    "--accent": "#22e0c3",
    // Provide the tertiary warm accent for occasional highlights.
    "--accent-2": "#ff7a2f",
    // Set the ground colour for the whole application.
    "--bg": "#0a0712",
    // Set the darker table felt used by game surfaces.
    "--felt": "#150a24",
    // Set the lighter felt gradient stop.
    "--felt2": "#23113d",
    // Set the translucent glass panel background.
    "--panel": "rgba(20, 10, 34, 0.72)",
    // Set the stronger glass panel background for emphasis.
    "--panel-strong": "rgba(14, 7, 24, 0.9)",
    // Set the hairline border colour used around panels.
    "--border": "rgba(255, 255, 255, 0.1)",
    // Set the softer hairline used inside dense controls.
    "--border-soft": "rgba(255, 255, 255, 0.09)",
    // Set the primary text colour.
    "--text": "#f4eeff",
    // Set the muted secondary text colour.
    "--muted": "#9e93bc",
    // Set the shared corner radius for the brand.
    "--radius": "14px",
    // Set the signature glow used only on the primary action.
    "--glow": "0 0 24px rgba(255, 59, 107, 0.5)",
  },
  // Publish the browser theme colour that matches the ground.
  themeColor: "#0a0712",
};
