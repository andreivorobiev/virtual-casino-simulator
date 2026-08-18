// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Model the production escape-by-default template without importing browser-global modules. (CORE-033)

// Brand reviewed markup fragments with one test-private identity.
const RAW_HTML = Symbol('test.raw-html');

// Escape ordinary interpolation values with the production entity mapping.
function escapeHtml(value) {
  // Replace only the five characters significant in HTML text and attributes.
  return String(value ?? '').replace(/[&<>'"]/g, character => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[character]));
}

// Mark one reviewed fragment for nested tagged-template composition.
export function raw(value) {
  // Preserve an existing reviewed wrapper across nested helpers.
  if (value?.[RAW_HTML] === true) return value;
  // Freeze the exact string representation for later composition.
  const markup = String(value ?? '');
  return Object.freeze({
    // Preserve reviewed-fragment identity for nested templates.
    [RAW_HTML]: true,
    // Model browser innerHTML string coercion for direct source assertions.
    includes: (...arguments_) => markup.includes(...arguments_),
    // Publish the exact markup when templates or mock DOM fields coerce it.
    toString: () => markup,
  });
}

// Render arrays, reviewed fragments, and ordinary values through one boundary.
function htmlValue(value) {
  // Flatten arrays without comma insertion.
  if (Array.isArray(value)) return value.map(htmlValue).join('');
  // Preserve only explicitly reviewed markup.
  if (value?.[RAW_HTML] === true) return String(value);
  // Escape every ordinary interpolation by default.
  return escapeHtml(value);
}

// Build one reviewed markup fragment from immutable parser strings.
export function html(strings, ...values) {
  // Start with the first immutable template segment.
  let markup = strings[0];
  // Append each escaped value and following segment in source order.
  values.forEach((value, index) => { markup += htmlValue(value) + strings[index + 1]; });
  // Return one reviewed fragment compatible with browser innerHTML coercion.
  return raw(markup);
}
