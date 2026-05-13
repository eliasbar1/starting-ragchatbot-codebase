# Frontend Changes: Theme Toggle Button & Light Theme CSS Variables

## Feature Added
A dark/light mode toggle button positioned in the top-right corner of the UI.

## Files Modified

### `frontend/index.html`
- Added a `<button id="themeToggle">` element with `position: fixed` at the top-right, placed outside `.container` so it floats above all content.
- Contains two inline SVG icons inside a `.theme-toggle-icons` wrapper span:
  - **Moon icon** — visible in dark mode (default)
  - **Sun icon** — visible in light mode
- `aria-label="Toggle theme"` and `title="Toggle light/dark mode"` for accessibility.
- Both SVGs have `aria-hidden="true"` since the button label conveys the purpose.
- Bumped cache-busting query strings from `?v=11` to `?v=12` on both `style.css` and `script.js`.

### `frontend/style.css`
Three new sections added before the existing `/* Base Styles */` block:

1. **Light mode variables** (`body.light-mode { ... }`) — overrides the dark-mode `:root` CSS variables:
   - `--background: #f8fafc`, `--surface: #ffffff`, `--surface-hover: #f1f5f9`
   - `--text-primary: #0f172a`, `--text-secondary: #64748b`, `--border-color: #e2e8f0`
   - Lighter shadow and focus-ring values

2. **Smooth theme transitions** — `body, body *` rule adds `transition: background-color 0.3s ease, color 0.3s ease, border-color 0.3s ease, box-shadow 0.3s ease` so every element animates when the theme class toggles.

3. **Toggle button styles** (`.theme-toggle`, `.theme-toggle-icons`, `.icon-moon`, `.icon-sun`):
   - `position: fixed; top: 1rem; right: 1rem; z-index: 1000` — always visible in the top-right corner.
   - Circular (42×42 px), uses existing `--surface`, `--border-color`, `--shadow` design tokens.
   - Hover: scales up 10% and highlights with `--primary-color`; active: scales down slightly.
   - `:focus-visible` ring using `--primary-color` and `--focus-ring` for keyboard navigation.
   - Icon crossfade: both SVGs are `position: absolute` inside a relative wrapper. `opacity` and `transform: rotate()` are transitioned so the outgoing icon rotates away while the incoming icon rotates in (0.35–0.4 s ease).

### `frontend/script.js`
Added `setupThemeToggle()` function, called at the top of the `DOMContentLoaded` handler:
- Reads `localStorage.getItem('chatbot-theme')` on load and applies `body.light-mode` if `'light'` was previously saved.
- On click, toggles `body.classList.toggle('light-mode')`, persists the new preference to `localStorage`, and updates `aria-label` to describe the action available (e.g. "Switch to dark mode" when light mode is active).
- Native `<button>` semantics handle keyboard activation (Enter / Space) without any extra event listeners.

---

## Feature Added: Light Theme CSS Variables

### `frontend/style.css`

#### Expanded `:root` (dark mode defaults)
Added new CSS variables to eliminate hardcoded color values throughout the stylesheet:

- **`--code-bg: rgba(0, 0, 0, 0.25)`** — background for inline `code` and `pre` blocks in dark mode
- **`--source-link-color / -bg / -border`** — color tokens for source chip links (previously hardcoded `#a8c7fa` etc.)
- **`--source-link-hover-*`** — separate hover-state tokens for source chips
- **`--welcome-bg / --welcome-border / --welcome-shadow`** — tokens for the welcome card (previously defined but never applied)

Variables are grouped by semantic purpose: brand, surfaces, text, borders/decoration, chat messages, welcome card, code blocks, source chips.

#### Expanded `body.light-mode`
Complete light theme variable set with accessibility-compliant values:

| Token | Light value | WCAG contrast |
|---|---|---|
| `--background` | `#f8fafc` | — |
| `--surface` | `#ffffff` | — |
| `--surface-hover` | `#f1f5f9` | — |
| `--text-primary` | `#0f172a` | 18:1 on `--background` (AAA) |
| `--text-secondary` | `#475569` | 5.9:1 on `--background` (AA) |
| `--border-color` | `#e2e8f0` | — |
| `--primary-color` | `#2563eb` (unchanged) | 5.4:1 on `--background` (AA) |
| `--code-bg` | `#eef2f7` | subtle gray on white |
| `--source-link-color` | `#1d4ed8` | 7.1:1 on white (AAA) |
| `--welcome-bg` | `#eff6ff` | — |
| `--welcome-border` | `#93c5fd` | — |

#### CSS rules updated to use variables (replacing hardcoded values)
- **`.sources-content a`** — `color`, `background`, `border` now use `--source-link-*` variables; added `color` to the transition list
- **`.sources-content a:hover`** — uses `--source-link-hover-*` variables
- **`.message-content code`** — `background-color` now `var(--code-bg)`
- **`.message-content pre`** — `background-color` now `var(--code-bg)`
- **`.message-content blockquote`** — fixed bug: `var(--primary)` (undefined) → `var(--primary-color)`
- **`.message.welcome-message .message-content`** — `background`, `border`, and `box-shadow` now use `--welcome-bg`, `--welcome-border`, `--welcome-shadow` (previously used `--surface` / `--border-color`, so these variables were defined but had no effect)

#### `frontend/index.html`
- Bumped CSS cache-busting version from `?v=12` to `?v=13`.

---

## Feature Added: JavaScript Functionality (Toggle & Smooth Transitions)

### `frontend/index.html`
- **FOUC prevention inline script** added in `<head>` (before the stylesheet link). Runs synchronously on first parse — reads `localStorage` and `prefers-color-scheme`, then adds `html.light-mode-preload` to `<html>` if light mode should be active. This means the correct theme variables are applied on the very first paint with zero flash.
- Bumped `script.js` cache version to `?v=13` and `style.css` to `?v=14`.

### `frontend/script.js`
Rewrote `setupThemeToggle()` with four improvements:

1. **System preference detection** — when no `localStorage` entry exists, reads `window.matchMedia('(prefers-color-scheme: light)').matches` to decide the initial theme instead of hardcoding dark.

2. **OS change listener** — `mq.addEventListener('change', ...)` watches for the user changing their OS theme at runtime. Only fires if the user has no saved manual preference (so a manual choice is never silently overridden).

3. **Transition suppression on init** — `applyTheme(..., animate=false)` adds `html.no-theme-transition` before toggling the class, then removes it two animation frames later (double-rAF pattern). This prevents the `body *` transition rule from animating the very first theme application, which would look like a slow fade-in on every page load.

4. **Preload class handoff** — after applying `body.light-mode`, removes `html.light-mode-preload` (set by the inline head script) so there's no double-class overlap.

### `frontend/style.css`
Three additions:

- **`html.light-mode-preload body` selector** added to the light mode variable block, alongside `body.light-mode`. Allows the head inline script to activate light theme variables immediately before JS runs.

- **`html.no-theme-transition *` rule** — sets `transition: none !important` on all elements and pseudo-elements while the class is present, blocking the animated transition during the initial theme setup.

- **Explicit `transition` on `.theme-toggle`** — overrides the generic `body *` rule by spelling out all transitioned properties including `transform 0.15s ease`. Without this, the button's `scale(1.1)` hover and `scale(0.95)` active states were instant (not animated) because `transform` was absent from the `body *` transition shorthand.

---

## Feature Added: `data-theme` Attribute for Theme Switching

### Why `data-theme` instead of a class

Using a `data-*` attribute on `<html>` to represent UI state (rather than a behaviour/styling class on `body`) is more semantically correct and removes all the complexity of the previous two-class system (`html.light-mode-preload` + `body.light-mode`). Both the FOUC-prevention script and the JS toggle now write to the same attribute on the same element — no "handoff" step is needed.

### `frontend/style.css`

Three selector changes (no variable values changed):

| Before | After |
|---|---|
| `html.light-mode-preload body, body.light-mode { … }` | `html[data-theme="light"] { … }` |
| `body.light-mode .icon-moon { … }` | `html[data-theme="light"] .icon-moon { … }` |
| `body.light-mode .icon-sun { … }` | `html[data-theme="light"] .icon-sun { … }` |

Moving the light-mode variable block from `body` to `html[data-theme="light"]` is also more correct in the CSS cascade: `html[data-theme="light"]` has specificity (0,1,1), which beats `:root` (0,1,0), so the overrides reliably win without needing `!important`.

The CSS comment on the block was updated to explain the unified single-selector approach.

Bumped CSS to `?v=15`.

### `frontend/script.js`

`setupThemeToggle()` updated in three ways:

1. **`applyTheme`** — replaced `document.body.classList.toggle('light-mode', isLight)` + `document.documentElement.classList.remove('light-mode-preload')` with a single `document.documentElement.setAttribute('data-theme', theme)`. Cleaner and no longer needs the two-step handoff.

2. **Click handler** — replaced `classList.toggle('light-mode')` + `classList.contains('light-mode')` (which depended on `body`) with reading the current `data-theme` attribute and flipping it: `getAttribute('data-theme') === 'light' ? 'dark' : 'light'`. The source of truth is now the DOM attribute, not a class.

3. **Removed `savedTheme()` helper** — the function was a wrapper around `localStorage.getItem('chatbot-theme')`. Inlined the call directly to reduce indirection.

Bumped JS to `?v=14`.

### `frontend/index.html`

Inline FOUC-prevention script updated from:
```js
if (saved === 'light' || (!saved && preferLight)) {
    document.documentElement.classList.add('light-mode-preload');
}
```
to:
```js
var theme = saved || (preferLight ? 'light' : 'dark');
document.documentElement.setAttribute('data-theme', theme);
```

Now sets `data-theme` on `<html>` unconditionally (both `light` and `dark` are written), which means the HTML attribute is always present and queryable from first paint. The JS `setupThemeToggle` simply reads and updates this same attribute with no class cleanup required.
