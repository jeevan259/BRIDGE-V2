# BRIDGE Architecture

BRIDGE (Brand Rules, Intelligence, Dependency, Governance & Evidence) is an enterprise brand governance and continuous brand compliance platform. It bridges normative brand guidelines, product specifications, and legal rules with downstream digital asset creation.

```mermaid
flowchart TD
    subgraph Client ["Frontend Shell (React 18 + TS + Vite + Tailwind)"]
        UI["Role-Aware UI (Overview, Knowledge, Submissions, Review, Continuity, GuidelineX, Audit, Admin)"]
        AuthStore["Zustand Auth Store (JWT + Cookie Rotation)"]
        ApiClient["Axios Interceptor (X-Correlation-ID, Token Refresh)"]
    end

    subgraph API ["Backend API (FastAPI Modular Monolith)"]
        Middleware["Correlation ID & Sanitized Structured Logging Middleware"]
        Router["/api/v1 Router"]
        
        subgraph CoreServices ["Core Services & Engines"]
            AuthService["Auth & RBAC Service (JWT + Revocation)"]
            KnowledgeEngine["Knowledge Engine (Record & Immutable Versioning)"]
            ValidationEngine["Validation Engine (Deterministic Rules + AI Adversarial)"]
            ContinuityEngine["Continuity Engine (Dependency Graph & Blast Radius)"]
            GuidelineX["GuidelineX (Friction Signals & Ambiguity Radar)"]
            AuditService["Tamper-Evident Audit Service (SHA-256 Hash Chain)"]
        end
    end

    subgraph Storage ["Persistence Layer"]
        Postgres[("PostgreSQL 16 + pgvector")]
        AuditTrigger["PostgreSQL Trigger (BLOCK UPDATE / DELETE on audit_events)"]
        VectorExt["pgvector (Passage Semantic Search)"]
    end

    subgraph External ["AI Providers"]
        Gemini["Google Gemini 1.5 Pro / Flash"]
        MockAI["Offline Mode / Deterministic Fallback"]
    end

    UI --> ApiClient
    ApiClient --> Middleware
    Middleware --> Router
    Router --> AuthService
    Router --> KnowledgeEngine
    Router --> ValidationEngine
    Router --> ContinuityEngine
    Router --> GuidelineX
    Router --> AuditService

    AuthService --> Postgres
    KnowledgeEngine --> Postgres
    ValidationEngine --> Postgres
    ValidationEngine --> Gemini
    ValidationEngine --> MockAI
    ContinuityEngine --> Postgres
    GuidelineX --> Postgres
    AuditService --> Postgres
    Postgres --> AuditTrigger
    Postgres --> VectorExt
```

## System Components

1. **Frontend (`frontend/` or `web/`)**:
   - Single Page Application built with React 18, TypeScript, Tailwind CSS, and Vite.
   - Real-time React Flow interactive dependency topology.
   - Role-aware routing and navigation for 5 enterprise personas.
   - Offline-aware AI status badge in TopBar.

2. **Backend API (`backend/` or `api/`)**:
   - High-throughput asynchronous FastAPI monolith.
   - Pydantic v2 schemas with standardized error envelopes.
   - Startup environment validation ensuring graceful offline AI degradation.
   - Structured JSON logging with `X-Correlation-ID` tracing across all requests.
   - Sanitizer preventing credential or document payload leakage.

3. **Database & Storage (`db`)**:
   - PostgreSQL 16 with `pgvector` and `pgcrypto` extensions enabled.
   - Strict tenant isolation enforced on every query (`org_id`).
   - Append-only audit table protected by PostgreSQL triggers blocking UPDATE and DELETE statements.
   - Partial unique index enforcing exactly one active approved version per knowledge record.

