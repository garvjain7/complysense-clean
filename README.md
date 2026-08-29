# ComplySense

ComplySense is an AI-assisted Governance, Risk, and Compliance platform for institutions that need to manage controls, evidence, assessments, vendors, incidents, policies, audits, notifications, and role-specific compliance workflows from one workspace.

The project is a full-stack application with a React/Vite frontend, a FastAPI main API, and a separate FastAPI AI service for role-aware chat, RAG retrieval, document context, and regulatory guidance.

## What It Includes

- Role-based dashboards and route guards for 9 roles:
  - Super Admin
  - Institution Admin
  - Compliance Officer
  - IT Security Officer
  - Auditor
  - Department Reviewer
  - Vendor Reviewer
  - Policy Approver
  - Read-Only Assessor
- Authentication with refresh sessions, password reset, login throttling, and account unlock flows.
- Core GRC modules for controls, assessments, gaps, evidence, policies, vendors, incidents, tasks, departments, institutions, users, notifications, calendars, and audit logs.
- Operational audit trail logging across major system actions.
- Role-specific AI assistants routed through the main API and backed by the AI service.
- Hybrid RAG using local FAISS and BM25 indexes, local sentence-transformer embeddings, Supabase-hosted knowledge files, MongoDB document metadata, and Gemini model responses.
- Frontend pages, navigation, and shared components tailored to each organizational role.

## Architecture

```text
ComplySense
+-- Frontend: React 19 + TypeScript + Vite
+-- Main API: FastAPI + PostgreSQL + MongoDB + Supabase
`-- AI Service: FastAPI + Gemini + LangChain + FAISS + BM25
```

The main API exposes business endpoints under `/api/v1/*` and proxies role-specific AI requests under `/api/v1/ai/*`. The AI service runs separately on port `8001` and owns retrieval, prompt construction, model calls, and RAG index lifecycle.

## Tech Stack

### Frontend

- React 19
- TypeScript
- Vite 6
- React Router 7
- Zustand
- Axios
- Radix UI primitives
- Lucide React icons
- Recharts
- Custom CSS design system in `frontend/src/styles.css`

### Backend

- FastAPI
- SQLAlchemy Async IO
- Asyncpg
- PostgreSQL
- MongoDB with Motor
- Supabase Storage
- Pydantic Settings
- JWT/session authentication
- Structured logging

### AI and Retrieval

- Gemini via `langchain-google-genai`
- LangChain
- FAISS
- BM25
- Sentence Transformers with `BAAI/bge-m3`
- Local vectorstore artifacts in `backend/ai_service/vectorstore`
- Knowledge base markdown files in `backend/ai_service/knowledge-base`

## Repository Layout

```text
complysense-clean/
+-- README.md
+-- package.json                 # Root scripts for installing and running all services
+-- .env.example                 # Environment variable template
+-- schema.sql                   # PostgreSQL schema snapshot
+-- seed.py                      # Seed data helper
+-- docs/                        # Architecture notes, UI specs, contracts, audits
+-- backend/
|   +-- requirements.txt
|   +-- app/                     # Main FastAPI API
|   |   +-- main.py
|   |   +-- config.py
|   |   +-- database.py
|   |   +-- mongodb.py
|   |   +-- routers/
|   |   +-- repositories/
|   |   +-- services/
|   |   +-- schemas/
|   |   `-- core/
|   +-- ai_service/              # Independent FastAPI AI/RAG service
|   |   +-- main.py
|   |   +-- config.py
|   |   +-- agents/
|   |   +-- rag/
|   |   +-- routers/
|   |   +-- prompts/
|   |   +-- knowledge-base/
|   |   `-- vectorstore/
|   +-- migrations/
|   `-- tests/
`-- frontend/
    +-- package.json
    +-- index.html
    `-- src/
        +-- App.tsx
        +-- main.tsx
        +-- styles.css
        +-- components/
        +-- hooks/
        +-- layouts/
        +-- lib/
        +-- pages/
        +-- routes/
        +-- store/
        `-- types/
```

## Prerequisites

- Node.js 20 or newer
- npm
- Python 3.11 or newer
- PostgreSQL database
- MongoDB database
- Supabase project and storage bucket
- Gemini API key for AI features

## Environment Setup

Copy the example environment file:

```bash
cp .env.example .env
```

Fill in the required values:

```env
DATABASE_URL=postgresql+asyncpg://user:password@host/complysense?ssl=require
MONGODB_URI=mongodb+srv://user:password@cluster.mongodb.net/complysense
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key
SECRET_KEY=replace-with-a-strong-secret-at-least-32-characters
GEMINI_API_KEY=your-gemini-api-key
LLM_MODEL=gemini-2.5-flash-lite
AI_SERVICE_URL=http://localhost:8001
MAIN_API_URL=http://localhost:8000
VITE_API_URL=http://localhost:8000
FRONTEND_URL=http://localhost:5173
```

Optional values include SMTP credentials for password reset email delivery and `ADMIN_REINDEX_KEY` for protecting AI reindex operations.

## Install

Install root and frontend dependencies:

```bash
npm run install:all
```

Install Python dependencies:

```bash
npm run install:python
```

## Database Setup

Create a PostgreSQL database, then apply the schema:

```bash
psql -h <host> -U <user> -d <database> -f schema.sql
```

If you need local demo data, review and run:

```bash
python seed.py
```

## Run Locally

Start the frontend, main API, and AI service together:

```bash
npm run dev
```

Service URLs:

- Frontend: http://localhost:5173
- Main API docs: http://localhost:8000/docs
- AI Service docs: http://localhost:8001/docs
- AI readiness: http://localhost:8001/health/ready

You can also run each service separately:

```bash
npm run dev:frontend
npm run dev:backend
npm run dev:ai
```

## Useful Commands

```bash
npm run build        # Type-check and build the frontend
npm run typecheck    # Run frontend TypeScript checks
npm run lint         # Run frontend ESLint
```

Backend tests can be run from the repository root or the `backend` folder, depending on the test target:

```bash
python -m pytest backend/tests
```

## AI Service Notes

The AI service loads FAISS and BM25 indexes during startup. If existing vectorstore files are present, they are loaded into memory. If not, the service attempts a cold-start reindex from the configured knowledge sources.

Important local paths:

- `backend/ai_service/knowledge-base/` contains bundled markdown knowledge files.
- `backend/ai_service/vectorstore/` contains generated FAISS, BM25, and item metadata artifacts.
- `backend/ai_service/rag/` contains indexing, retrieval, confidence, and generation logic.

## Documentation

Start with these docs when changing behavior:

- `docs/system-audits/00-overview.md`
- `docs/system-audits/18-project-status.md`
- `docs/design-review.md`
- `docs/RAG_Architecture_v2.md`
- `docs/chat_contract.md`
- `docs/notification_contract.md`

## Development Guidelines

- Keep frontend styling in the existing CSS design system instead of adding one-off inline styles.
- Keep role navigation centralized through shared layout/navigation components.
- Route AI calls through the main API proxy unless a low-level AI service endpoint is being tested directly.
- Document significant architecture, security, database, and endpoint changes in `docs/design-review.md`.
- Preserve audit logging and RBAC checks when adding or changing backend workflows.
