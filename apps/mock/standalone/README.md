# Single-file copy of the app (design reference)

`apps/mock/smart-health-standalone.html` is the current app (`apps/web`) in ONE file. Double-click it; no server, no API, no internet.
Use it to look at the screens and improve the design. **It is not part of the app**: nothing in `apps/web` or `services/api` depends on it,
and building it changes nothing there.

- It shows real data for both people (Demo user, Mr Tan; switch on the Me tab), recorded from the live API on the day it was built.
- Writes (logging, taking a dose, confirming a fact) look like they work but are kept in memory only and vanish on reload.
- A photo analysis always returns the recorded chicken-rice example. Medicine scanning says it needs the live service.
- Addresses use `#`, for example `smart-health-standalone.html#/insights/food`.

## Rebuild after the app changes

```bash
node apps/mock/standalone/capture.mjs   # optional: record fresh data (the API must be running on :8000)
node apps/mock/standalone/build.mjs     # needs `npm install` done in apps/web
```

## How it works

| File | What it does |
|---|---|
| `main.tsx` | Entry. Same as `apps/web/src/main.tsx`, after putting the shim in place of the network. Imports the app from `apps/web/src`. |
| `shim.ts` | Replaces `fetch` for `/api/v1/...` with the recorded answers in `snapshot.json`. |
| `router-shim.js` | Makes `BrowserRouter` a `HashRouter` in this build only, so it works from a file. |
| `capture.mjs` | Records the API's answers (and one real write of each kind, deleted again) into `snapshot.json`. |
| `build.mjs` | Builds with the tools in `apps/web/node_modules`, inlines code, styles and fonts into `index.html`'s shell. |
