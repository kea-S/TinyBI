# Frontend Workspace

This directory contains a standalone React + Vite + TypeScript frontend set up to sit in front of the Python backend.

## Stack

- React 19
- Vite 8
- TypeScript 5
- Tailwind CSS v4
- shadcn UI

## Commands

```bash
npm install
npm run dev
```

The dev server runs on Vite defaults and proxies `/api/*` to `http://127.0.0.1:8000` unless you override it.

## Environment

Create a local env file if you need to change the backend target:

```bash
cp .env.example .env.local
```

Available variables:

- `VITE_BACKEND_URL`: target used by the Vite dev proxy. Default is `http://127.0.0.1:8000`.
- `VITE_API_BASE_URL`: optional browser-side base URL. Default is `/api`.

## Verification

```bash
npm run check
```
