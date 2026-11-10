# BRIDGE v2 — Baseline Audit & Gap Analysis

**Date**: 2026-11-10  
**Scope**: Codebase audit covering Environment Configuration, RBAC enforcement, Audit Event coverage, Query performance (N+1), and URL portability across local and production deployments.

---

## Executive Summary

| Category | Total Identified | Fixed in Baseline (<5 min) | Remaining / Backlog |
|---|:---:|:---:|:---:|
| **Environment Variables** | 7 | 7 | 0 |
| **RBAC Enforcement** | 4 | 4 | 0 |
| **Audit Events on State Mutation** | 14 | 14 | 0 |
| **N+1 Query Patterns** | 3 | 1 | 2 (remaining performance work) |
| **Hardcoded URLs / Ports** | 5 | 3 | 2 (Alembic default) |

---

## 1. Missing Environment Variables

### Resolved in Baseline (<5 min)
- [x] **`DEMO_MODE`** (`bool`, default: `false`): Enables zero-downtime offline demonstration mode when PostgreSQL is not reachable or unseeded. Added to `Settings`, `.env.example`, and `.env`.
- [x] **`COOKIE_SECURE`** (`bool`, default: `false` in dev, `true` in prod): Configures `Secure` attribute on JWT refresh cookies. Added to `Settings` and `.env.example`.
- [x] **`COOKIE_SAMESITE`** (`str`, default: `lax`): Configures `SameSite` attribute (`lax`, `strict`, `none`). Cross-site production configurations can now set `COOKIE_SAMESITE=none` and `COOKIE_SECURE=true`.
- [x] **`COOKIE_DOMAIN`** (`str | None`, default: `None`): Allows sharing refresh token cookies across subdomains (e.g., `.brandbridge.internal`).
- [x] **`VITE_API_URL`** (`str`, default: `""` / relative `/api`): Allows frontend production build to communicate with distinct API backend host without proxying.
- [x] **`VITE_PORT`** (`int`, default: `3000`): Environment-driven port for the web dev server.
- [x] **`CORS_ORIGINS`** (`str`): Multi-origin support enabled via comma-separated list.

---

## 2. Endpoints Without RBAC Checks

### Resolved in Baseline (<5 min)
- [x] **`GET /api/v1/audit/events`**: Previously accessible to any authenticated user (including `creator`). Now explicitly restricted via `require_role(administrator, brand_manager, reviewer, auditor)`. Verified via new test `test_audit_log_rbac_permissions`.
- [x] **`GET /api/v1/audit/verify`**: Previously accessible to all roles. Now restricted via `require_role(administrator, brand_manager, auditor)`. Verified via test.

### Resolved in this branch
- `GET /api/v1/users` is restricted to `administrator` and `brand_manager`.
- `GET /api/v1/continuity/edges` is restricted to non-creator roles.

---

## 3. Endpoints Mutating State Without Writing an Audit Event

Every state mutation in an ISO 27001 / tamper-evident compliance system must produce a cryptographically chained audit log entry.

### Resolved in Baseline (<5 min)
- [x] **`POST /api/v1/validation/jobs`** (`submit_validation_job`): Added `VALIDATION_JOB_SUBMITTED` audit event.
- [x] **`POST /api/v1/guidelines/signals`** (`create_review_signal`): Added `REVIEW_SIGNAL_CREATED` audit event.
- [x] **`POST /api/v1/continuity/edges`** (`create_edge`): Added `DEPENDENCY_EDGE_CREATED` audit event.
- [x] **`POST /api/v1/continuity/edges/{edge_id}/confirm`** (`confirm_edge`): Added `DEPENDENCY_EDGE_CONFIRMED` audit event.
- [x] **`PATCH /api/v1/continuity/revalidation-tasks/{task_id}`** (`update_revalidation_task`): Added `REVALIDATION_TASK_UPDATED` audit event.
- [x] **`POST /api/v1/knowledge/sources`** (`create_source`): Added `SOURCE_CREATED` audit event.
- [x] **`PATCH /api/v1/knowledge/sources/{source_id}`** (`update_source`): Added `SOURCE_UPDATED` audit event.
- [x] **`POST /api/v1/knowledge/items`** (`create_item`): Added `ITEM_CREATED` audit event.
- [x] **`POST /api/v1/users`** (`create_user`): Added `USER_CREATED` audit event.
- [x] **`PATCH /api/v1/users/{user_id}`** (`update_user`): Added `USER_UPDATED` audit event.
- [x] **`POST /api/v1/organisations`** (`create_organisation`): Added `ORGANISATION_CREATED` audit event.
- [x] **`PATCH /api/v1/organisations/{org_id}`** (`update_organisation`): Added `ORGANISATION_UPDATED` audit event.

### Resolved in this branch
- `POST /api/v1/auth/login` appends `AUTH_LOGIN_SUCCESS` to the tenant audit chain.
- `POST /api/v1/auth/logout` appends `AUTH_LOGOUT` to the tenant audit chain.

---

## 4. N+1 Queries & Database Performance

### Identified Items with Severity

- **Resolved in this branch** — `api/app/services/validation.py` citation resolution now batch-resolves candidate item-version and passage IDs in two queries instead of two queries per candidate.

- **Severity: Medium** — `api/app/services/validation.py` (lines 98, 108, 127):
  - *Location*: Deterministic check findings creation.
  - *Issue*: `await db.flush()` is called 3 times per violation (Finding -> Citation -> Receipt) inside loop iterations rather than bulk inserting with a single final flush.
  - *Fix*: Collect all models in memory and perform `db.add_all()` followed by a single flush.

- **Severity: Low** — `api/app/api/v1/validation.py` (`list_job_findings`):
  - *Location*: Finding listing.
  - *Issue*: Citations and evidence receipts are loaded via separate API calls per finding (`/findings/{id}/citations`, `/findings/{id}/evidence`) rather than eager-loading via `joinedload` or combined payload for the UI.
  - *Fix*: Provide `include_citations=true` query parameter for composite response.

---

## 5. Hardcoded Localhost URLs and Ports

### Resolved in Baseline (<5 min)
- [x] **`web/src/lib/api.ts`**: Replaced hardcoded relative `/api/v1` with `import.meta.env.VITE_API_URL` dynamic prefix (`${VITE_API_URL}/api/v1`), falling back cleanly to `/api/v1`.
- [x] **`web/vite.config.ts`**: Port is now driven by `VITE_PORT` / `PORT` environment variables (defaulting to 3000). Proxy target is driven by `VITE_API_URL` (defaulting to `http://localhost:8000`).
- [x] **`api/app/core/config.py`**: CORS origins split into a configurable list from `CORS_ORIGINS`.

### Remaining Items with Severity
- **Severity: Low** — `api/alembic.ini` and `api/alembic/env.py`: Default connection strings contain `localhost:5432`. Overridden at runtime via `DATABASE_URL` environment variable, but fallback text remains.
- **Severity: Low** — `docker-compose.yml`: Health check uses `curl -f http://localhost:8000/health`. Standard within container network, but host port mapping should remain aligned with `API_PORT`.

---

## 6. Verification & Health Probes

- **Liveness**: `GET /health` returns application operational status. `GET /api/v1/ai/status` returns cached provider, mode, model, and last error; Gemini status is based on a real test request.
- **Readiness**: `GET /ready` checks live database connectivity (`SELECT 1`) and verifies the `vector` extension exists in `pg_extension`. Returns 200 OK when ready or in demo mode, and 503 Service Unavailable when degraded in production.

