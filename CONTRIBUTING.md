# Contributing to ByteSized

Thank you for considering a contribution! This document explains how to set up your environment, submit changes, and add new AST rules or extensions.

---

## Table of Contents

1. [Development Setup](#development-setup)
2. [Project Layout](#project-layout)
3. [Backend: Adding a New AST Rule](#backend-adding-a-new-ast-rule)
4. [Backend: Adding a New Extension Router](#backend-adding-a-new-extension-router)
5. [Extension: Adding a New VS Code Command](#extension-adding-a-new-vs-code-command)
6. [Tests](#tests)
7. [Code Style](#code-style)
8. [Pull Request Checklist](#pull-request-checklist)

---

## Development Setup

### Prerequisites

| Tool | Min version |
|------|-------------|
| Python | 3.11 |
| Node.js | 20 LTS |
| npm | 10 |
| Docker (optional) | 24 |

### Backend

```bash
# 1. Create a virtual environment
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r backend/requirements.txt

# 3. Copy and configure environment
cp .env.example .env               # fill in GEMINI_API_KEY, CORS_ORIGINS, etc.

# 4. Start the dev server
uvicorn backend.main:app --reload --port 8000
# Swagger UI: http://localhost:8000/docs
```

### Extensions

```bash
# Build the shared utilities package first (once)
cd extensions/shared && npm install && npm run compile

# Then build whichever extension you are working on
cd extensions/siliconbob-rtl && npm install && npm run compile
# Press F5 in IBM Bob / VS Code to launch the Extension Development Host
```

---

## Project Layout

```
ByteSized/
├── .github/workflows/ci.yml       ← CI pipeline (lint + test + audit)
├── backend/
│   ├── config.py                  ← Pydantic-Settings typed config
│   ├── main.py                    ← App factory (CORS, logging, rate-limit)
│   ├── shared/models.py           ← Pydantic request/response models
│   └── routers/
│       ├── rtl/engine.py          ← Language-specific AST rule implementations
│       ├── rtl/router.py          ← FastAPI routes for RTL / code analysis
│       └── blueprintbob/          ← Architecture diagram engine
├── extensions/
│   ├── shared/                    ← @bytesized/shared npm package
│   ├── siliconbob-rtl/            ← RTL code optimizer extension
│   └── blueprintbob/              ← Architecture visualizer extension
└── deploy/
    ├── Dockerfile                 ← Multi-stage production image
    └── docker-compose.yml         ← Redis + backend + nginx
```

---

## Backend: Adding a New AST Rule

Rules live in [`backend/routers/rtl/engine.py`](backend/routers/rtl/engine.py).

1. **Choose a rule ID** following the existing convention: `<LANG>-<NNN>-<SLUG>` (e.g., `PY-005-PRINT-DEBUG`).

2. **Add detection logic** inside the appropriate `optimize_<language>` function.  
   Return an [`RTLIssue`](backend/shared/models.py) with `fixed_line` populated if an auto-fix is possible.

3. **Write a test** in [`backend/tests/test_engine.py`](backend/tests/test_engine.py) — one `_BAD` and one `_CLEAN` snippet, following the existing pattern.

4. Run the tests to confirm:
   ```bash
   pytest backend/tests/test_engine.py -v -k "<your_rule_id>"
   ```

---

## Backend: Adding a New Extension Router

Follow the four-step pattern in the README:

1. Create `backend/routers/<your_ext>/router.py` — copy `blueprintbob/router.py` as a template.
2. Mount it in `backend/main.py`:
   ```python
   from backend.routers.<your_ext>.router import router as your_ext_router
   app.include_router(your_ext_router)
   ```
3. Add Pydantic request/response models to `backend/shared/models.py`.
4. Add integration tests (copy `backend/test_blueprintbob.py` as a template).

---

## Extension: Adding a New VS Code Command

1. Register the command in `extensions/<ext>/package.json` under `"contributes.commands"`.
2. Create `extensions/<ext>/src/commands/<yourCommand>.ts`.
3. Wire it up in `extensions/<ext>/src/extension.ts` inside `activate()`.
4. Rebuild: `npm run compile`.

---

## Tests

```bash
# Backend unit tests
pytest backend/tests/ -v

# Backend integration tests
pytest backend/test_blueprintbob.py -v

# All backend tests with coverage
pytest backend/ --cov=backend --cov-report=term-missing

# TypeScript compile check
cd extensions/siliconbob-rtl && npm run compile
```

---

## Code Style

### Python

- Formatter: **Ruff** (`ruff check backend/` and `ruff format backend/`)
- Line length: 100
- Target: Python 3.11+
- All new modules must have a module-level docstring.

A `ruff.toml` (or `pyproject.toml` `[tool.ruff]` section) will enforce this in CI.

### TypeScript

- ESLint with the existing `.eslintrc.json` in each extension.
- No `any` types without a justifying comment.
- Prefer `const` over `let`; never use `var`.

---

## Pull Request Checklist

Before opening a PR, confirm all of the following:

- [ ] `pytest backend/` passes with no new failures
- [ ] `npm run compile` passes for affected extensions
- [ ] `ruff check backend/` reports no new errors
- [ ] New public functions/endpoints have docstrings / JSDoc
- [ ] New AST rules have a corresponding test (`_BAD` + `_CLEAN`)
- [ ] No secrets, API keys, or `.env` files are committed
- [ ] `CHANGELOG.md` entry added (if user-facing change)

---

## Questions?

Open an issue or start a Discussion on GitHub. We follow a [Code of Conduct](CODE_OF_CONDUCT.md) — please be kind and constructive.
