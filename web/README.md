# VAYNEX Web — AI Resilience OS (frontend)

Next.js 15 (App Router) + TypeScript command-center UI for the Vaynex backend in this repo.
Every screen reads the real FastAPI API (`/api/v1`); the contract is documented in
[`../../docs/frontend-backend-contract.md`](../../docs/frontend-backend-contract.md).

## Run

```bash
# terminal 1 — backend (from the repo root)
docker compose up --build            # API on :8000, Postgres/PostGIS, Redis, demo seed

# terminal 2 — frontend
cd apps/web
cp .env.example .env.local           # NEXT_PUBLIC_API_URL=http://localhost:8000
npm install
npm run dev                          # http://localhost:3000
```

Sign in with a seeded account (development only), e.g. `operator@vaynex.local` / `VaynexOperator!2026`.
In `npm run dev` the login screen has one-click fill buttons for the three seed accounts.

Open the app at **http://localhost:3000** (the backend's default CORS allows exactly that origin;
if you use another origin, add it to `CORS_ALLOWED_ORIGINS` in the backend `.env`).

Optional container: `docker compose --profile web up --build`.

## Scripts

| Command | Purpose |
|---|---|
| `npm run dev` | dev server on :3000 |
| `npm run build` / `npm start` | production build / serve |
| `npm run lint` | ESLint (next/core-web-vitals + typescript) |
| `npm run typecheck` | `tsc --noEmit` |

## Environment

| Variable | Required | Notes |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | yes | Backend origin, no `/api/v1`. Default `http://localhost:8000`. |
| `NEXT_PUBLIC_MAPBOX_TOKEN` | no | Not used by default — the app plots real coordinates on its own geo grid and 3D network. |

No secrets live in the frontend. The JWT is kept in `localStorage` (`vaynex.session.v1`) so a page refresh
mid-demo keeps the session; it is never logged and is cleared on logout or any 401.

## Structure

```
src/
  app/                 routes: /login, /command (+ incidents, incidents/[id], infrastructure, network,
                       intelligence, simulation, recommendations, audit)
  components/
    shell/             sidebar, topbar, status bar, auth guard
    command-center/    metrics strip, live incidents, bottom panels
    3d/                React Three Fiber resilience network (+ 2D SVG fallback)
    network/           React Flow dependency graph, node inspector
    simulation/        simulation center + timeline-driven intelligence feed
    incidents/         risk gauge/factors, impact lists, create-event + resolve dialogs
    intelligence/      AI analysis view, pipeline rail
    recommendations/   recommendation card + human decision dialog
    ui/                panel, badge, button, dialog, field, states, toast
  lib/api/             fetch client (JWT, error envelope), endpoints, query keys
  lib/auth/            session storage
  hooks/               TanStack Query hooks + mutations with invalidation
  store/               Zustand UI state (selection, simulation playback, highlight)
  types/               TypeScript mirrors of the backend Pydantic schemas
```

## Demo

Click **RUN VAYNEX DEMO** (top bar or command center; OPERATOR/ADMIN). It:

1. fetches `GET /simulation/scenarios` and picks `hospital_power_failure` if the backend offers it,
2. calls `POST /simulation/run` with `apply_status_changes: true`,
3. replays the backend's `timeline[]` step by step — the 3D network lights the cascade depth by depth using
   each `ImpactNode.depth`, and the feed reveals event, context, affected assets/services, incident, risk,
   AI analysis, recommendations and audit exactly as returned,
4. hands off to the human decision (accept / reject recommendations inline),
5. returns to the command center, which now shows the changed state from live API data.

Resolve the incident from its detail page to restore asset statuses.
