# 2nd-ext

> **ByteSized — Extension #2 Placeholder**

This is the scaffold for the second ByteSized IBM Bob / VS Code extension.
Replace this README with your extension's description.

## Getting Started

```bash
cd extensions/2nd-ext
npm install
npm run compile
```

Press **`F5`** in Bob / VS Code to launch the Extension Development Host.

## Backend

Your backend routes live in `backend/routers/second_ext/router.py`.  
Health check: `GET http://localhost:8000/2nd-ext/health`

## Adding Commands

1. Create a handler in `src/commands/<yourCommand>.ts`
2. Register it in `src/extension.ts`
3. Add the command to `contributes.commands` in `package.json`
