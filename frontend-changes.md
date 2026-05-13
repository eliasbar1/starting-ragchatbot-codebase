# Frontend Changes

## Code Quality Tooling

### What was added

**Prettier** (`^3.5.3`) was added as the frontend auto-formatter, the JS/HTML/CSS equivalent of Black for Python.

| File | Purpose |
|------|---------|
| `package.json` | npm project manifest; declares Prettier as a devDependency and exposes `format`, `format:check`, and `lint` scripts |
| `.prettierrc` | Prettier config: 2-space indent, single quotes, 100-char print width, LF line endings, ES5 trailing commas |
| `.prettierignore` | Excludes `node_modules/`, `.venv/`, and pre-minified assets from formatting |
| `scripts/check-frontend.sh` | Dev script that runs Prettier in check mode (or `--fix` mode) with clear pass/fail output |

### Formatting rules applied (`.prettierrc`)

```json
{
  "semi": true,
  "singleQuote": true,
  "tabWidth": 2,
  "printWidth": 100,
  "trailingComma": "es5",
  "bracketSpacing": true,
  "arrowParens": "always",
  "htmlWhitespaceSensitivity": "css",
  "endOfLine": "lf"
}
```

### Files reformatted

All three frontend files were reformatted on initial setup:

- `frontend/index.html` — consistent 2-space indentation, self-closing void elements (`<meta />`, `<link />`), lowercase `<!doctype html>`
- `frontend/script.js` — 2-space indentation, single quotes, trailing commas, removed extra blank lines
- `frontend/style.css` — consistent spacing and property ordering

### How to use

```bash
# Check formatting (CI-style, exits non-zero if anything is unformatted)
npm run format:check
# or
./scripts/check-frontend.sh

# Auto-fix formatting
npm run format
# or
./scripts/check-frontend.sh --fix
```
