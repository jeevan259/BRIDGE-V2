# BRIDGE v2

**Brand Rules, Intelligence, Dependency, Governance & Evidence**

An AI-assisted brand governance platform built for hackathon demonstration.

## Stack

- **API**: FastAPI + SQLAlchemy (async) + PostgreSQL (pgvector) + Alembic
- **Frontend**: React 18 + TypeScript + Vite + Tailwind CSS + React Query
- **AI**: Gemini API (live) / Mock / Adversarial Mock providers
- **Auth**: JWT (access) + httpOnly cookie (refresh) + bcrypt passwords

## Quick Start

```bash
# 1. Copy and configure environment
cp .env.example .env

# 2. Start all services
docker-compose up --build

# 3. Run initial migration (first time only)
docker-compose exec api alembic upgrade head

# 4. Access
#    API docs:  http://localhost:8000/docs
#    Frontend:  http://localhost:3000
```

## Development (without Docker)

### API

```bash
cd api
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd web
npm install
npm run dev
```

## Architecture

```
BRIDGE v2
├── Knowledge Management    — ingest docs, extract items, version everything
├── Validation Engine       — AI checks content against brand guidelines
├── Evidence System         — citation receipts, hallucination detection
├── Brand Continuity        — dependency graph, impact analysis, revalidation queue
├── GuidelineX              — review signals → ambiguity analysis → recommendations
└── Audit Log               — append-only, hash-chained, tamper-evident
```

## AI Providers

| Provider       | Description                                          |
|----------------|------------------------------------------------------|
| `mock`         | Deterministic responses based on input hash          |
| `adversarial`  | Fabricates citations to demonstrate hallucination trap |
| `gemini`       | Live Gemini API (requires `GEMINI_API_KEY`)          |

## RBAC Roles

| Role            | Permissions                                           |
|-----------------|-------------------------------------------------------|
| `administrator` | Full access                                           |
| `brand_manager` | Approve/reject items, manage knowledge, guidelines   |
| `reviewer`      | Read all, create signals, confirm edges               |
| `creator`       | Submit jobs, read findings, read knowledge            |
| `auditor`       | Read-only including audit log                         |
