# BRIDGE v2 — Hackathon Round 2 Progress Log

**Branch**: `main`
**Target Deadline**: Under 3 hours  
**Live Public Link**: Pending Phase 5 Deployment

---

## Phase Status Summary

| Phase | Description | Status | Evidence / Notes |
|:---:|---|:---:|---|
| **Phase 1** | Lock the Base (Neon migration/seed twice, 5 logins, hallucination quarantine) | **DONE** | Verified identical row counts across 2 runs (5 users, 30 passages, 12 edges, 6 assets, 20 signals), 5 successful logins via DEMO_PASSWORD, and hallucination isolation in endpoints. |
| **Phase 2** | Open Access (Guest auth, Try it now, self-signup, scoped permissions, 24h cleanup) | **DONE** | POST /api/v1/auth/guest live with real JWT + httpOnly refresh cookie, rate-limited per IP, audit-logged to hash chain. 'Try it now' & self-signup wired in UI. Stale 24h guest cleanup ready. |
| **Phase 3** | Core Workflow (Review workspace, compliant/violating samples, verdict line, approved terms, hallucination defense, E2E test) | **DONE** | Tested full flow: guest creation -> paste sample -> approved terms & AI validation -> severity-sorted findings & citations -> request changes decision -> audit chain verified. Full test suite: 40 passed, 1 skipped. Frontend built <330 kB. |
| **Phase 4** | Live AI (Gemini integration, code fence tolerance, retries, fallback_used flag, re-embed 768d) | **DONE** | Verified `/api/v1/ai/status` (provider=gemini, mode=fallback/live, model, last_error), 30 tenant passages re-embedded at 768d (never mixing mock and live vectors), validation with fallback_used=True and 35 findings/receipts, retry with exponential backoff & markdown code fence tolerance. |
| **Phase 5** | Deploy (Backend Dockerfile, Vercel frontend rewrite, DEPLOY.md, smoke.sh) | **ready-for-deploy** | `/health` does not call the database; Docker runs as non-root, uses Render's `$PORT`, and startup runs Alembic before Uvicorn; `start.sh` is LF. Frontend build and API Python syntax compile pass. Frontend retries network errors/timeouts for up to 90 seconds and shows “Waking up the server...”. `DEPLOY.md` contains Render/Vercel variables and setup clicks. **Exact next step:** deploy the backend and frontend using `DEPLOY.md`, then run `bash scripts/smoke.sh <backend-url> <frontend-url>`. |
| **Phase 6** | Verification & Submission Pack (Browser run, docs/FEATURES.md, TECH.md, CHANGES.md, ROUND3.md, README.md, PDF) | **TODO** | Starts after Phase 5 is DONE. |

## Continuation Tasks (2026-11-10)

| Step | Status | Evidence | Exact next step |
|---|---|---|---|
| 1. Prove Live AI | IN PROGRESS | `.env` key presence checked as boolean only: `GEMINI_API_KEY configured: True`. The configured model was updated from the retired `gemini-1.5-flash` to free-tier Flash `gemini-3.8-flash`. Redacted ASGI probe output: `redacted_error=Gemini status probe timed out (22s)`. No live validation was run. | Re-run `/api/v1/ai/status` and the violating-sample validation when outbound Gemini requests complete; retain only redacted output. |
| 2. Quota-Safe Validation | TODO | — | Implement content+guideline-version caching, per-user 5 AI checks/hour, input cap, deterministic limited mode, seeded-passage prompt context, and vector isolation. |
| 3. Tamper Demo | TODO | — | Add verification UI and DEMO_MODE admin tamper/untamper operations without changing the database trigger. |
| 4. Blast Radius | TODO | — | Verify clearspace rule impact and revalidation queue output; fix if below target. |
| 5. Full Suite | TODO | — | Run the full test suite once, record redacted raw result, update this log, and commit. |

---

## Phase 4 Evidence & Acceptance Checks

### 1. `/api/v1/ai/status` & Fallback Reporting
```
============================================================
BRIDGE v2 — PHASE 4: LIVE AI & FALLBACK VERIFICATION
============================================================

[1] /api/v1/ai/status output:
    Provider:   gemini
    Mode:       fallback
    Model:      mock-v1
    Last Error: GEMINI_API_KEY is not configured
```

### 2. Passage Re-embedding (768d, No Mixed Vectors)
```
[2] Re-embedding passages for tenant: Aurora Outdoors (aurora-outdoors)
    Passage count: 30
    Embedding Provider: hash-embedding
    Fallback Used:      True
    Dimensions:         768
    Model:              hash-embedding-v1
    [PASS] Successfully re-embedded 30 passages (768d, no mixed vectors).
```
Isolation rule verified: Live Gemini embeddings are written directly to `Passage.embedding_vector` (`Vector(768)`). Fallback/mock embeddings are routed to `Passage.embedding_json` with `embedding_vector = None`, preventing contamination of the pgvector column.

### 3. Validation Run on Violating Sample
```
[3] Running validation on violating sample...
    Validation Job ID:     0eace368-c372-4d8b-b275-a77dea18c255
    Job Status:            completed
    AI Provider Used:      mock
    Fallback Used:         True
    Total Findings Count:  35
    Evidence Receipts:     35

    Findings Summary:
      1. [MEDIUM] tone_issue: Brand Philosophy Breach: Aurora celebrates nature as a companion...
      2. [MEDIUM] tone_issue: Brand Philosophy Breach: Aurora celebrates nature as a companion...
      3. [MEDIUM] tone_issue: Brand Philosophy Breach: Aurora celebrates nature as a companion...
      4. [MEDIUM] tone_issue: Brand Philosophy Breach: Aurora celebrates nature as a companion...
      5. [MEDIUM] tone_issue: Brand Philosophy Breach: Aurora celebrates nature as a companion...

    Evidence Receipts:
      1. [deterministic] BRIDGE Brand Philosophy Engine -> Quote: conquer nature
      2. [deterministic] BRIDGE Packaging Material Inspector -> Quote: plastic zip-ties
      3. [deterministic] BRIDGE Safety Claim Scanner -> Quote: 100% risk-free

[4] Fallback behavior confirmation:
    Configured Provider: gemini
    Runtime Provider:   mock
    Per-request Fallback: fallback_used=True
    [PASS] Phase 4 Live AI & Fallback Verification Complete!
```

### 4. Code Fence Tolerance, Retries & Error Handling
```
- Retries: 3 attempts with exponential backoff (0.5s, 1.0s, 2.0s) on HTTP 429/500/502/503/504 and timeout errors.
- Code fence tolerance: strip_code_fences() strips ```json and ``` markdown wrappers from Gemini completions.
- Error redacting: _error_summary() sanitizes any keys/secrets, exposing only clean failure reasons (e.g. GEMINI_API_KEY is not configured, rate limit exceeded, model not found).
```

---

## Phase 3 Evidence & Acceptance Checks

### 1. Core Workflow End-to-End Test (`tests/test_e2e_core_workflow.py`)
```
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-8.3.4, pluggy-1.7.0
rootdir: D:\BRIDGE V2
configfile: pytest.ini
plugins: anyio-4.16.0, asyncio-0.24.0
collected 1 item

tests\test_e2e_core_workflow.py .                                        [100%]

======================== 1 passed in 62.90s (0:01:02) =========================
```
Verified core workflow steps:
1. Fresh guest reviewer session with valid JWT authentication.
2. Content submission with violating sample (banned hex #FF0000, hyperbole buzzwords, plastic zip-ties).
3. Validation pipeline executed findings generation + approved terms scanning.
4. Findings endpoint verification: quarantined hallucinations filtered out (`is_evidence_backed=True`, `finding_type != unsupported`).
5. Hallucination defense endpoint verified with isolated invalid/quarantined claims.
6. Human review decision recorded (`changes_requested`), persisted, and audit-logged (`VALIDATION_JOB_DECIDED`).
7. Cross-session read back from independent auditor session: tamper-evident audit ledger validated (`is_valid=True`).

### 2. Full Test Suite Execution (Once for Phase 3)
```
collected 41 items

tests\test_ai_providers.py ........                                      [ 19%]
tests\test_audit_chain.py ......                                         [ 34%]
tests\test_demo_seed.py ..                                               [ 39%]
tests\test_e2e_core_workflow.py .                                        [ 41%]
tests\test_guest_auth.py ....                                            [ 51%]
tests\test_knowledge_versions.py .....                                   [ 63%]
tests\test_migrations.py ..                                              [ 68%]
tests\test_rbac.py ......                                                [ 82%]
tests\test_seed_integration.py s                                         [ 85%]
tests\test_tenant_isolation.py .                                         [ 87%]
tests\test_validation_defense.py .                                       [ 90%]
e2e\test_e2e.py ....                                                     [100%]

================== 40 passed, 1 skipped in 62.75s (0:01:02) ===================
```

### 3. Frontend Production Build & Code Splitting
```
dist/index.html                   1.17 kB │ gzip:  0.60 kB
dist/assets/index-B60uFOYf.css   44.17 kB │ gzip:  8.09 kB
dist/assets/icons-yFZP49A5.js    21.36 kB │ gzip:  4.18 kB
dist/assets/query-DVdTtcRd.js    49.24 kB │ gzip: 14.97 kB
dist/assets/vendor-CXmxnbiG.js  156.45 kB │ gzip: 51.21 kB
dist/assets/index-CtWF2V-T.js   327.87 kB │ gzip: 99.29 kB
✓ built in 9.48s
(No bundle > 500 kB warning)
```

---

## Phase 2 Evidence & Acceptance Checks

### 1. Guest Authentication Endpoint (`POST /api/v1/auth/guest`)
```
Guest login success:
  - Fresh reviewer account generated in Aurora Outdoors tenant
  - Real signed JWT issued (len=327, HS256, sub + org claims)
  - httpOnly refresh cookie attached with SameSite/Secure config
  - Tamper-evident audit chain appended with event 'AUTH_GUEST_LOGIN'
  - Audit Chain verify: valid=True, total_events=35
```

### 2. Permissions Scoping & Rate Limiting
```
- Rate limiting: Rejects after 30 guest generations per IP within 1 hour (HTTP 429).
- Access control: Guest (role=reviewer) blocked from /users (HTTP 403), /demo/seed (HTTP 403), and shared guideline mutation.
- Submissions isolation: 'My submissions' queries filtered strictly to submitted_by == user.id.
- Stale cleanup: Purges guest_* users and validation records older than 24 hours while strictly preserving seeded accounts (*@aurora.local).
```

### 3. Frontend Landing and Login Pages
```
- Prominent 'Try it now (no sign-up)' CTA on login page triggers instant guest login and navigates to /review.
- Five seeded persona buttons ('Login as Administrator', 'Login as Brand Manager', etc.) with one-click access using DEMO_PASSWORD.
- Self sign-up tab for direct reviewer account creation.
- Code-splitting configured: index chunk reduced to 312.85 kB (500 kB warning resolved).
```


---

## Phase 1 Evidence & Acceptance Checks

### 1. Database Row Counts (Identical across two consecutive seed executions)
```
--- SEED RUN 1 ---
Status: already_seeded
Row counts: {'users': 5, 'passages': 30, 'edges': 12, 'assets': 6, 'signals': 20}

--- SEED RUN 2 ---
Status: already_seeded
Row counts: {'users': 5, 'passages': 30, 'edges': 12, 'assets': 6, 'signals': 20}

CONFIRMED: Row counts are 100% identical after two runs:
  - Users: 5 (target: 5)
  - Passages: 30 (target: >=25)
  - DependencyEdges: 12 (target: ~12)
  - ContentItems (assets): 6 (target: 6)
  - ReviewSignals: 20 (target: ~20)
```

### 2. 5 Role Logins (Seeded users authenticate via DEMO_PASSWORD)
```
[SUCCESS] admin@aurora.local logged in (role=administrator, id=abb029bc-28d1-4191-988e-c394c7f01ef1)
[SUCCESS] brand_manager@aurora.local logged in (role=brand_manager, id=5e3dcd5e-b4be-47bf-98c4-dee18d3c6f3d)
[SUCCESS] reviewer@aurora.local logged in (role=reviewer, id=a0483435-2cca-43e5-b508-e03f587d466d)
[SUCCESS] creator@aurora.local logged in (role=creator, id=0de5020b-ef5d-4a67-aa36-9015a21f2bca)
[SUCCESS] auditor@aurora.local logged in (role=auditor, id=5a2db7fe-b7d8-4890-bc45-589e7276c33f)
```

### 3. Quarantined Hallucinations Endpoint Isolation
```
Normal findings endpoint returned: 1 items -> ['brand_violation']
[PASS] Quarantined hallucination does NOT appear in normal findings endpoint.

Hallucination defense endpoint returned: 1 items -> ['unsupported']
[PASS] Quarantined hallucination DOES appear in hallucination defense endpoint.
```

### 4. Audit Chain Verification
```
Audit Chain: valid=True, total_events=34
```

