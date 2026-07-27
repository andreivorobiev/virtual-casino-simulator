// Active-brand selection and runtime application so the whole app is one config swap.

// Import the default brand descriptor; a second brand is imported and swapped here.
import { tiltseven } from "../brands/tiltseven.js";

// Expose the single active brand consumed by the shell and PWA metadata.
export const activeBrand = tiltseven;

// Apply one brand's design tokens and identity to the live document.
export function applyBrand(brand = activeBrand) {
  // Read the document root once so custom properties and hooks land on it.
  const root = document.documentElement;
  // Publish each themeable token so CSS reskins from this single source.
  for (const [name, value] of Object.entries(brand.tokens || {})) {
    // Set the custom property that the stylesheet already consumes by name.
    root.style.setProperty(name, value);
  }
  // Record the active brand id so brand-specific overrides can hook off it.
  root.setAttribute("data-brand", brand.id);
  // Align the browser theme colour meta with the active brand ground.
  const meta = document.querySelector('meta[name="theme-color"]');
  // Update the theme colour only when the meta tag and value both exist.
  if (meta && brand.themeColor) meta.setAttribute("content", brand.themeColor);
  // Return the brand so callers can read its name and mark for the lockup.
  return brand;
}
