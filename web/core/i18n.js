// Copyright 2026 Andrei Vorobiev and Virtual Casino Simulator contributors
// SPDX-License-Identifier: Apache-2.0
// Store RESOURCE_ROOT so all locale files are loaded from one public web path.
const RESOURCE_ROOT = '/i18n';
// Store STORAGE_KEY so browser-local preferences remain isolated from game state.
const STORAGE_KEY = 'casino.locale.settings.v1';
// Store DEFAULT_MANIFEST so the runtime can still boot if the manifest request fails.
const DEFAULT_MANIFEST = { schemaVersion: 1, registryVersion: 'fallback', defaultLocale: 'en-US', fallbackLocale: 'en-US', aliases: { en: 'en-US', ru: 'ru-RU' }, locales: [], domains: ['common'] };
// Store PLACEHOLDER_RE so interpolation only replaces named resource placeholders.
const PLACEHOLDER_RE = /\{([a-zA-Z0-9_]+)\}/g;
// Store manifest so all helpers share the loaded locale catalog.
let manifest = null;
// Store activeLocale so calls to t() stay synchronous after initialization.
let activeLocale = 'en-US';
// Store formatLocale so number/date helpers can differ from the UI language.
let formatLocale = 'en-US';
// Store useBrowserLocale so Admin can show whether browser language resolution is active.
let useBrowserLocale = false;
// Store initPromise so multiple modules can safely initialize the runtime once.
let initPromise = null;
// Store dictionaries so loaded locale domains are reused across switches.
const dictionaries = new Map();
// Store loadedDomains so setLocale() can reload the same domains without remounting views.
const loadedDomains = new Set();
// Store registeredDomains so base resources and catalog-discovered game domains share one diagnostic inventory.
const registeredDomains = new Set();
// Store missingKeys so diagnostics can report fallback coverage without interrupting play.
const missingKeys = new Set();
// Store subscribers so mounted modules can refresh text without being remounted.
const subscribers = new Set();

// Define storageRead to safely load browser-local locale preferences.
function storageRead() {
  // Start protected logic so privacy modes or disabled storage do not break the UI.
  try {
    // Return parsed settings when a previous Admin choice exists.
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
  // Handle storage failures by falling back to defaults.
  } catch (_) {
    // Return an empty object so callers can continue with browser/default locale resolution.
    return {};
  }
}

// Define storageWrite to safely persist browser-local locale preferences.
function storageWrite(settings) {
  // Start protected logic so storage errors never affect gameplay.
  try {
    // Persist only locale settings and never any game or wallet state.
    localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
  // Handle storage failures by leaving the active in-memory locale unchanged.
  } catch (_) {}
}

// Define storageReset to safely remove browser-local locale preferences.
function storageReset() {
  // Start protected logic so storage errors never affect gameplay.
  try {
    // Remove the preference key while leaving all gameplay storage untouched.
    localStorage.removeItem(STORAGE_KEY);
  // Handle storage failures by leaving the active in-memory locale unchanged.
  } catch (_) {}
}

// Define fetchJson to load manifest and resource files with a safe empty fallback.
async function fetchJson(path, fallback = {}) {
  // Start protected logic so missing optional domains degrade through fallback strings.
  try {
    // Store response so status and JSON parsing can be checked together.
    const response = await fetch(path, { cache: 'no-cache' });
    // Branch when the resource is absent or blocked.
    if (!response.ok) return fallback;
    // Return parsed JSON data for the requested resource.
    return await response.json();
  // Handle network or parse failures by returning the supplied fallback.
  } catch (_) {
    // Return fallback so callers can continue through English/key fallback.
    return fallback;
  }
}

// Define loadManifest to initialize the locale catalog once.
async function loadManifest() {
  // Branch when another caller already loaded the manifest.
  if (manifest) return manifest;
  // Store loaded so malformed or missing manifest fields can be merged with defaults.
  const loaded = await fetchJson(`${RESOURCE_ROOT}/manifest.json`, DEFAULT_MANIFEST);
  // Set manifest to a normalized catalog with required fields present.
  manifest = { ...DEFAULT_MANIFEST, ...loaded, aliases: { ...DEFAULT_MANIFEST.aliases, ...(loaded.aliases || {}) }, domains: loaded.domains || DEFAULT_MANIFEST.domains, locales: loaded.locales || [] };
  // Register manifest-owned base domains before the live game catalog contributes route domains.
  (manifest.domains || []).forEach(domain => registeredDomains.add(domain));
  // Return the normalized manifest to the caller.
  return manifest;
}

// Define localeEntry to resolve one locked registry record without changing its translation identity.
function localeEntry(locale) {
  // Return the exact registry entry or undefined when the identifier is outside the locked program.
  return (manifest?.locales || []).find(item => item.id === locale);
}

// Define readyLocaleIds to expose only locales with complete selectable resource packs.
function readyLocaleIds() {
  // Return locales that explicitly satisfy both the readiness state and compatibility flag.
  return new Set((manifest?.locales || []).filter(locale => locale.readiness === 'ready' && locale.uiReady === true).map(locale => locale.id));
}

// Define canonicalLocale to resolve aliases and browser language tags.
function canonicalLocale(locale) {
  // Store raw so null, undefined, and empty values all resolve predictably.
  const raw = String(locale || '').trim();
  // Branch when callers ask for the browser/default fallback.
  if (!raw || raw === 'browser') return manifest?.defaultLocale || 'en-US';
  // Store aliases so language aliases can be resolved without changing resource ids.
  const aliases = manifest?.aliases || {};
  // Store supported so exact and case-insensitive matches can be detected.
  const supported = readyLocaleIds();
  // Branch when the exact locale id is installed.
  if (supported.has(raw)) return raw;
  // Store lower so aliases such as ru and en are case-insensitive.
  const lower = raw.toLowerCase();
  // Branch when an alias maps directly to an installed locale.
  if (aliases[lower] && supported.has(aliases[lower])) return aliases[lower];
  // Store matched so browser tags with different casing still resolve.
  const matched = [...supported].find(id => id.toLowerCase() === lower);
  // Branch when a case-insensitive installed locale was found.
  if (matched) return matched;
  // Store language so regional browser tags can fall back to the primary language alias.
  const language = lower.split('-')[0];
  // Branch when the language alias is supported.
  if (aliases[language] && supported.has(aliases[language])) return aliases[language];
  // Return the manifest default when no installed locale can satisfy the request.
  return manifest?.defaultLocale || 'en-US';
}

// Define browserLocale to read the user's browser language safely.
function browserLocale() {
  // Return the browser language or the default when navigator data is unavailable.
  return canonicalLocale(navigator.language || (navigator.languages || [])[0] || manifest?.defaultLocale || 'en-US');
}

// Define resourceKey to address a loaded dictionary in the cache.
function resourceKey(locale, domain) {
  // Return a stable cache key for the locale/domain pair.
  return `${locale}|${domain}`;
}

// Define loadResource to fetch and cache one locale domain.
async function loadResource(locale, domain) {
  // Store key so the dictionary cache is checked before network work.
  const key = resourceKey(locale, domain);
  // Branch when the requested dictionary is already available.
  if (dictionaries.has(key)) return dictionaries.get(key);
  // Store dictionary so callers always receive an object.
  const dictionary = await fetchJson(`${RESOURCE_ROOT}/${locale}/${domain}.json`, {});
  // Store the dictionary so future lookups stay synchronous.
  dictionaries.set(key, dictionary);
  // Return the loaded dictionary to the caller.
  return dictionary;
}

// Define lookupIn to read one key from one locale/domain dictionary.
function lookupIn(locale, domain, key) {
  // Store dictionary so a missing cache entry behaves like an empty resource.
  const dictionary = dictionaries.get(resourceKey(locale, domain)) || {};
  // Return the localized value or undefined when this dictionary has no key.
  return dictionary[key];
}

// Define interpolate to replace named placeholders in localized strings.
function interpolate(template, params) {
  // Return the string with each known placeholder replaced by its supplied value.
  return String(template).replace(PLACEHOLDER_RE, (_, name) => (params[name] ?? `{${name}}`));
}

// Define localeDirection to expose the current locale text direction.
function localeDirection(locale) {
  // Store entry so manifest metadata controls html dir.
  const entry = localeEntry(locale);
  // Return ltr unless a locale explicitly declares another direction.
  return entry?.dir || 'ltr';
}

// Define localeFallbackChain so future ready locales use only deliberate installed fallbacks.
function localeFallbackChain(locale) {
  // Read the locale-owned chain while retaining the global source fallback as a final guard.
  const declared = localeEntry(locale)?.fallbackChain || [locale, manifest?.fallbackLocale || 'en-US'];
  // Keep the active locale and ready fallbacks, de-duplicate them, and preserve declared order.
  return [...new Set(declared.filter(candidate => candidate === locale || readyLocaleIds().has(candidate)).concat(manifest?.fallbackLocale || 'en-US'))];
}

// Define normalizeFormatLocale so persisted formatter choices remain inside the locked registry.
function normalizeFormatLocale(candidate, displayLocale = activeLocale) {
  // Preserve explicit browser formatting while avoiding any translation-resource implication.
  if (candidate === 'browser') return navigator.language || localeEntry(displayLocale)?.formatLocale || displayLocale;
  // Match either a translation identity or one of its declared deterministic formatter identities.
  const entry = (manifest?.locales || []).find(locale => locale.id === candidate || locale.formatLocale === candidate);
  // Prefer the configured formatter and fall back to the active locale's deterministic formatter.
  return entry?.formatLocale || localeEntry(displayLocale)?.formatLocale || displayLocale || manifest?.defaultLocale || 'en-US';
}

// Define applyDocumentLocale to keep the root document metadata in sync.
function applyDocumentLocale() {
  // Read active metadata once so direction, script, and readiness never drift independently.
  const entry = localeEntry(activeLocale);
  // Set html lang so assistive technology sees the resolved UI locale.
  document.documentElement.lang = activeLocale;
  // Set html dir so future RTL locales can be activated deliberately.
  document.documentElement.dir = localeDirection(activeLocale);
  // Expose the active script for generic font and visual-test policies without game-owned assumptions.
  document.documentElement.dataset.localeScript = entry?.script || 'Latn';
  // Expose only the non-linguistic readiness state and never claim certification.
  document.documentElement.dataset.localeReadiness = entry?.readiness || 'fallback';
}

// Export registerI18nDomains so the live game catalog owns route-domain discovery.
export function registerI18nDomains(domains = []) {
  // Normalize and accept only resource-relative domain identifiers supplied by trusted catalog descriptors.
  domains.map(domain => String(domain || '').trim()).filter(domain => /^[a-z0-9][a-z0-9/_-]*$/.test(domain)).forEach(domain => registeredDomains.add(domain));
  // Return deterministic diagnostics for tests and Admin without loading unvisited games.
  return [...registeredDomains].sort();
}

// Export initI18n so pages can load the domains they own before rendering.
export async function initI18n({ domains = [] } = {}) {
  // Branch when base initialization is already in progress or complete.
  if (initPromise) {
    // Wait for base locale state before loading domains requested by a lazy route.
    await initPromise;
    // Load every newly requested domain so late-mounted games never render raw keys.
    await Promise.all([...new Set(domains)].map(domain => loadI18nDomain(domain)));
    // Refresh declarative strings after late domain resources become available.
    applyTranslations(document);
    // Return current state so repeated initialization matches the first-call contract.
    return getLocaleState();
  }
  // Set initPromise so concurrent module imports share the same startup work.
  initPromise = (async () => {
    // Call manifest loading before resolving locales.
    await loadManifest();
    // Store saved so browser-local Admin preferences are honored.
    const saved = storageRead();
    // Set useBrowserLocale from saved preferences before choosing the active language.
    useBrowserLocale = saved.useBrowserLocale === true;
    // Store urlLocale so QA can force a locale without saving a preference.
    const urlLocale = new URLSearchParams(location.search).get('locale') || new URLSearchParams(location.search).get('lang');
    // Set activeLocale using URL, browser, saved, and default resolution order.
    activeLocale = canonicalLocale(urlLocale || (useBrowserLocale ? browserLocale() : saved.language) || manifest.defaultLocale);
    // Set formatLocale using saved format settings or the active display locale.
    formatLocale = normalizeFormatLocale(saved.formatLocale || activeLocale, activeLocale);
    // Apply document metadata before rendering localized strings.
    applyDocumentLocale();
    // Store requestedDomains so common is always available for fallback strings.
    const requestedDomains = [...new Set(['common', ...domains])];
    // Load every requested domain for the active and fallback locales.
    await Promise.all(requestedDomains.map(domain => loadI18nDomain(domain)));
    // Apply declarative translations after dictionaries are ready.
    applyTranslations(document);
    // Return the public locale state for callers that need diagnostics.
    return getLocaleState();
  // Finish the shared initialization closure.
  })();
  // Return the shared initialization promise.
  return initPromise;
}

// Export loadI18nDomain so game and Admin modules can lazy-load their owned strings.
export async function loadI18nDomain(domain) {
  // Call manifest loading so fallback locale is known before resource fetches.
  await loadManifest();
  // Add the domain to the active set so future locale switches reload it.
  loadedDomains.add(domain);
  // Register the requested domain so lazy core modules and live catalog games share diagnostics.
  registerI18nDomains([domain]);
  // Load the active locale and every ready declared fallback for this domain.
  await Promise.all(localeFallbackChain(activeLocale).map(locale => loadResource(locale, domain)));
  // Return the loaded active dictionary for convenience.
  return dictionaries.get(resourceKey(activeLocale, domain)) || {};
}

// Export t so modules can synchronously resolve plain text strings.
export function t(key, params = {}, domainHint = 'common') {
  // Store domain so callers can omit the hint for common strings.
  const domain = domainHint || 'common';
  // Resolve the first value from the active locale and its deliberate installed fallback chain.
  const value = localeFallbackChain(activeLocale).map(locale => lookupIn(locale, domain, key) ?? lookupIn(locale, 'common', key)).find(candidate => candidate !== undefined);
  // Branch when no resource contains the requested key.
  if (value === undefined) {
    // Store the missing key once so diagnostics are stable.
    missingKeys.add(`${activeLocale}|${domain}|${key}`);
    // Return the visible key so missing text never creates a blank control.
    return key;
  }
  // Return the localized string with named placeholders applied.
  return interpolate(value, params);
}

// Export applyTranslations so static HTML can refresh without page reloads.
export function applyTranslations(root = document) {
  // Translate text content for declarative i18n elements.
  root.querySelectorAll?.('[data-i18n]').forEach(element => {
    // Set element text to the translated key in its declared domain.
    element.textContent = t(element.dataset.i18n, {}, element.dataset.i18nDomain || 'common');
  });
  // Translate title attributes for declarative i18n elements.
  root.querySelectorAll?.('[data-i18n-title]').forEach(element => {
    // Set title to the translated key in its declared domain.
    element.title = t(element.dataset.i18nTitle, {}, element.dataset.i18nDomain || 'common');
  });
  // Translate placeholder attributes for declarative i18n inputs.
  root.querySelectorAll?.('[data-i18n-placeholder]').forEach(element => {
    // Set placeholder to the translated key in its declared domain.
    element.placeholder = t(element.dataset.i18nPlaceholder, {}, element.dataset.i18nDomain || 'common');
  });
  // Translate aria-label attributes for icon or compact controls.
  root.querySelectorAll?.('[data-i18n-aria-label]').forEach(element => {
    // Set aria-label to the translated key in its declared domain.
    element.setAttribute('aria-label', t(element.dataset.i18nAriaLabel, {}, element.dataset.i18nDomain || 'common'));
  });
}

// Export setLocale so controls can switch language without navigation or remounting.
export async function setLocale(locale, { persistLocal = true, nextFormatLocale, nextUseBrowserLocale } = {}) {
  // Call initialization so dictionaries and manifest are available.
  await initI18n({ domains: [...loadedDomains] });
  // Detect a concrete selector choice separately from an explicit browser-default sentinel.
  const explicitLocale = Boolean(String(locale || '').trim()) && locale !== 'browser';
  // Resolve browser-default ownership without exposing a partially switched public state.
  const resolvedUseBrowserLocale = nextUseBrowserLocale === undefined ? (explicitLocale ? false : useBrowserLocale) : nextUseBrowserLocale === true;
  // Resolve the target display locale while the current UI remains internally consistent.
  const resolvedLocale = resolvedUseBrowserLocale ? browserLocale() : canonicalLocale(locale);
  // Resolve formatting against the target display identity before committing either value.
  const resolvedFormatLocale = normalizeFormatLocale(nextFormatLocale || formatLocale || resolvedLocale, resolvedLocale);
  // Preload every active domain and deliberate fallback before public locale state can change.
  await Promise.all([...loadedDomains].flatMap(domain => localeFallbackChain(resolvedLocale).map(fallback => loadResource(fallback, domain))));
  // Commit browser-default ownership only after all target resources are available.
  useBrowserLocale = resolvedUseBrowserLocale;
  // Commit the display locale atomically with its ready dictionaries.
  activeLocale = resolvedLocale;
  // Commit the matching deterministic formatter in the same state transition.
  formatLocale = resolvedFormatLocale;
  // Apply document metadata immediately without touching mounted game state.
  applyDocumentLocale();
  // Persist only the browser-local preference when requested.
  if (persistLocal) storageWrite({ language: activeLocale, formatLocale: nextFormatLocale === 'browser' ? 'browser' : formatLocale, useBrowserLocale });
  // Refresh declarative text in place without navigation.
  applyTranslations(document);
  // Store state so event listeners and subscribers receive the same snapshot.
  const state = getLocaleState();
  // Dispatch a browser event so mounted modules can rerender text while preserving state.
  window.dispatchEvent(new CustomEvent('casino-locale-changed', { detail: state }));
  // Notify direct subscribers after the browser event is emitted.
  subscribers.forEach(callback => callback(state));
  // Return the public state to the caller.
  return state;
}

// Export resetLocaleSettings so Admin can return to browser-default language resolution.
export async function resetLocaleSettings() {
  // Remove browser-local locale settings while leaving gameplay storage untouched.
  storageReset();
  // Switch to browser resolution and persist that mode for future page loads.
  return setLocale(browserLocale(), { persistLocal: true, nextFormatLocale: 'browser', nextUseBrowserLocale: true });
}

// Export getLocaleSettings so Admin can render the persisted preference controls.
export function getLocaleSettings() {
  // Store saved settings so current in-memory state can fill missing fields.
  const saved = storageRead();
  // Return combined settings for the Admin Language/Locale view.
  return { language: saved.language || activeLocale, formatLocale: saved.formatLocale || formatLocale, useBrowserLocale: saved.useBrowserLocale === true };
}

// Export getLocaleState so diagnostics and tests can inspect the active runtime.
export function getLocaleState() {
  // Store the complete registry separately so metadata-only entries never become selectable accidentally.
  const localeRegistry = manifest?.locales || [];
  // Return a serializable snapshot with ready selectors, complete metadata, and catalog-driven domains.
  return { locale: activeLocale, fallbackLocale: manifest?.fallbackLocale || 'en-US', formatLocale, useBrowserLocale, schemaVersion: manifest?.schemaVersion || 1, registryVersion: manifest?.registryVersion || 'fallback', loadedDomains: [...loadedDomains].sort(), registeredDomains: [...registeredDomains].sort(), missingKeyCount: missingKeys.size, locales: localeRegistry.filter(locale => readyLocaleIds().has(locale.id)), localeRegistry, plannedLocales: localeRegistry.filter(locale => !readyLocaleIds().has(locale.id)).map(locale => locale.id), domains: [...registeredDomains].sort() };
}

// Export formatNumber as the locale-aware numeric formatter.
export function formatNumber(value, options = {}) {
  // Return an Intl-formatted number using the active format locale.
  return new Intl.NumberFormat(formatLocale || activeLocale, options).format(Number(value || 0));
}

// Export formatMoney as the play-token amount formatter for UI display only.
export function formatMoney(value, options = {}) {
  // Resolve a full localized play-token label so the decorative mark never solely carries meaning. (UX-017)
  const unit = String(activeLocale || '').toLowerCase().startsWith('ru') ? 'игровых токенов' : 'play tokens';
  // Return a token-marked, unit-labeled numeric value without changing ledger semantics.
  return `◈${new Intl.NumberFormat(formatLocale || activeLocale, { minimumFractionDigits: 2, maximumFractionDigits: 2, ...options }).format(Number(value || 0))} ${unit}`;
}

// Export formatDate as the locale-aware date/time formatter.
export function formatDate(value, options = {}) {
  // Store date so timestamps, Date objects, and ISO strings all format consistently.
  const date = value instanceof Date ? value : new Date(value);
  // Return an Intl-formatted date using the active format locale.
  return new Intl.DateTimeFormat(formatLocale || activeLocale, options).format(date);
}

// Export onLocaleChange so mounted modules can subscribe without owning global events.
export function onLocaleChange(callback) {
  // Add the callback to the subscriber set.
  subscribers.add(callback);
  // Return an unsubscribe helper to avoid leaks when modules unmount.
  return () => subscribers.delete(callback);
}

// Expose the runtime for browser smoke tests and future non-module hooks.
window.CasinoI18n = { initI18n, registerI18nDomains, loadI18nDomain, t, setLocale, resetLocaleSettings, getLocaleSettings, getLocaleState, formatNumber, formatMoney, formatDate, onLocaleChange };
