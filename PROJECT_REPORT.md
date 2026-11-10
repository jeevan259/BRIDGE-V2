# BRIDGE v2 Project Report

**Reviewed:** 10 November 2026  
**Scope:** API, frontend, migrations, seed data, authorization, AI providers, tests, and live Neon verification.

## Project contents

BRIDGE is a multi-tenant brand governance application. The API is FastAPI in `api/`, the frontend is React/TypeScript in `web/`, and migrations use Alembic. Tests are in `tests/` and `e2e/`.

| Area | Present in the code |
|---|---|
| Identity and access | JWT login, refresh, logout, password hashing, five tenant roles, organization scoping, role checks, and login/logout audit events. |
| Tenant administration | Organization and user APIs, role-aware admin screens, and tenant-scoped records. `GET /users` is limited to administrators and brand managers. |
| Knowledge | Source ingestion/extraction support, knowledge items and versions, approval status, and passages used as governed evidence. |
| Validation | Job submission, background worker queue, deterministic checks, AI providers, findings, overrides, citations, and evidence receipts. Citation resolution batches reference lookups. |
| Continuity | Dependency edges, change events, impact reports, and revalidation tasks. Creators cannot list continuity edges. |
| GuidelineX | Review signals, ambiguity analyses, recommendations, and review/adoption routes. |
| Audit | Hash-chained audit events, event listing, and chain verification. |
| AI and embeddings | Mock, adversarial, and Gemini providers; per-request fallback; `fallback_used`; cached `/api/v1/ai/status`; and 768-dimensional Gemini vectors with tenant provider metadata. Production startup rejects Gemini configuration without a key. |
| Operations and UI | `/health`, database/pgvector `/ready`, Docker Compose, Alembic, one demo seeder (`api/app/seed_demo.py`), and screens for dashboard, knowledge, validation, review, continuity, governance, and administration. |

## Verified against Neon

The configured direct Neon endpoint was used for migrations and database checks. The vector extension was already present; migrations do not create it. Migration head is `003_ai_provider_metadata`. BRIDGE readiness reported database and pgvector healthy with `demo_mode=false`.

```text
alembic upgrade head
INFO  Running upgrade 001_initial -> 002_model_schema_alignment
INFO  Running upgrade 002_model_schema_alignment -> 003_ai_provider_metadata
alembic current
003_ai_provider_metadata (head)
READY HTTP 200: {"status":"ok","checks":{"database":"ok","pgvector":"ok"},"environment":"development","demo_mode":false}
```

The single demo seeder was invoked twice. Both calls returned `already_seeded`; the table counts stayed identical:

```text
COUNTS AFTER RUN 1: users=5, passages=30, knowledge_items=12, dependency_edges=12, validation_jobs_total=8, findings=10, evidence_receipts=8, review_signals=20, audit_events=26
COUNTS AFTER RUN 2: users=5, passages=30, knowledge_items=12, dependency_edges=12, validation_jobs_total=8, findings=10, evidence_receipts=8, review_signals=20, audit_events=26
IDEMPOTENT: PASS
```

Seed data includes six example validation jobs. Two more jobs in the totals were created by API round-trip verification. Requested seed targets are met: 5 users, 30 passages, 12 dependency edges, 20 review signals, and 6 example jobs.

All five seeded accounts authenticated and returned the expected roles:

```text
admin@aurora.local: login=200 me=200 role=administrator
brand_manager@aurora.local: login=200 me=200 role=brand_manager
reviewer@aurora.local: login=200 me=200 role=reviewer
creator@aurora.local: login=200 me=200 role=creator
auditor@aurora.local: login=200 me=200 role=auditor
```

Live role restrictions and logout after the final handler fix:

```text
RBAC administrator: users=200 continuity_edges=200
RBAC creator: users=403 continuity_edges=403
LOGOUT creator: HTTP 204
RBAC reviewer: users=403 continuity_edges=200
```

A creator submitted a violating asset. The Neon-backed worker completed it and returned citations and evidence receipts:

```text
JOB FINAL status=completed provider=mock fallback_used=False error=None
FINDINGS total=2
FINDING type=tone_issue severity=medium evidence_backed=True citations=1 receipts=1
  CITATION quote=revolutionary
  RECEIPT rule_grounding_type=deterministic item_title=Prohibited Hype & Marketing Buzzwords quote=revolutionary
FINDING type=brand_violation severity=high evidence_backed=True citations=1 receipts=1
  CITATION quote=#FF0000 / red gradient
  RECEIPT rule_grounding_type=deterministic item_title=Prohibited Red Color Palette quote=#FF0000 / red gradient
```

Adversarial mode completed another worker job and the server-side resolver quarantined two fabricated references:

```text
ADVERSARIAL JOB status=completed provider=adversarial fallback_used=False error=None
ADVERSARIAL FINDINGS total=2 quarantined_hallucinations=2
QUARANTINED status=pending evidence_backed=False description=[HALLUCINATION TRAP TRIGGERED] ...
```

Audit verification after API activity: `valid=True total_events=26 broken_at=None`.

## Automated and frontend checks

```text
# Neon integration enabled, before the final explicit logout 204 fix
31 passed in 1.94s
# Final local rerun after logout fix
30 passed, 1 skipped in 2.11s
4 passed in 2.32s
# Frontend build
✓ 1738 modules transformed.
✓ built in 9.22s
```

Earlier totals of 28 backend and 4 E2E tests predated the new coverage. The Neon-enabled run passed all 31 tests. After the small logout response fix, the local suite passed 30 tests and skipped the opt-in Neon integration; E2E passed all 4. A fresh database-enabled rerun after that last change was blocked by the command approval check. The opt-in integration requires `BRIDGE_RUN_SEED_INTEGRATION=1` and live database access.

## Implemented fixes verified in this run

- Removed automatic demo login and fabricated frontend sessions; login now uses the real API and displays API/network errors.
- Removed backend demo-user authentication fallback.
- Restricted user and continuity-edge listing by role.
- Added login/logout audit events and batched citation ID resolution.
- Fixed API session commit/rollback behavior. This was required because requests had returned success while rolling back writes, leaving the worker without validation jobs.
- Added authenticated AI status and a status-driven frontend badge.
- Added per-request Gemini fallback and `fallback_used`; vector metadata is tenant-specific and the Gemini vector field is 768 dimensions.
- Added forward migrations for ORM/schema alignment and AI/vector metadata.

## Limits and remaining work

- No Gemini key is configured and `AI_PROVIDER=mock`; live Gemini generation and embeddings could not be exercised. Missing-key fallback and production refusal are covered by tests, but live Gemini remains unverified.
- Port 8000 was occupied (`[Errno 10048] ... only one usage ...`). The unrelated listener was left intact; BRIDGE ran on 8001. The web dev server ran on 3000 and returned HTTP 200. Vite warns that the main minified JavaScript chunk exceeds 500 kB.
- Docker Compose was not launched; the live API, Neon database, migration, seeder, worker, and frontend were checked directly.
- The working tree had user modifications before this verification. They were preserved; no commit was made to avoid bundling those unreviewed changes. The feature branch diff remains available for review.
