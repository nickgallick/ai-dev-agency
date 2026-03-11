
# AI Dev Agency — CLAUDE.md

> Context file for Claude Code. Read this before doing anything else.

***

## What This Project Is

An AI-powered development agency platform. You submit a project brief and a pipeline of 20 AI agents automatically builds an entire application — research, architecture, design, code generation, testing, and deployment. Think personal Devin/Factory-style tool.

**Current state:** Originally built by Abacus AI Deep Agent. Most critical bugs have been fixed. The pipeline runs end-to-end, the queue works, and the UI is functional in both light and dark themes. Several enhancement features have been added (see Implemented Features below).

***

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11, FastAPI (port 8000) |
| Frontend | React 18.2, TypeScript 5.3, Vite 5.1, Tailwind CSS 3.4 (port 5173) |
| Database | PostgreSQL 16 — Supabase in production |
| ORM/Migrations | SQLAlchemy 2.0 + Alembic |
| Pipeline | LangGraph |
| LLM API | OpenRouter (all LLM calls routed through this) |
| Code Gen (Web) | Vercel v0 Platform API |
| Code Gen (Other) | OpenHands API |
| Repo Delivery | GitHub API |
| Graph Visualization | @xyflow/react (React Flow) |
| Charts | Recharts |
| State Management | Zustand, React Query |
| HTTP Client | Axios (frontend), httpx/aiohttp (backend) |
| Icons | Lucide React |
| Infrastructure | Docker Compose (dev), Railway/Render (prod) |

***

## How to Run

```
docker-compose up -d
Dashboard: http://localhost:5173
API: http://localhost:8000

Watch backend logs: docker-compose logs -f api
Restart backend: docker-compose restart api
Run migrations: docker-compose exec api alembic upgrade head
Access DB: docker-compose exec db psql -U postgres -d postgres
Frontend build check: cd frontend && npx vite build
Backend syntax check: cd backend && python -c "import py_compile, glob; [py_compile.compile(f, doraise=True) for f in glob.glob('**/*.py', recursive=True)]"
```

***

## All 20 Agents (in pipeline order)

1. Intake & Classification — backend/agents/intake.py
2. Research — backend/agents/research.py
3. Architect — backend/agents/architect.py
4. Design System — backend/agents/design_system.py
5. Asset Generation — backend/agents/asset_generation.py (parallel with 6)
6. Content Generation — backend/agents/content_generation.py (parallel with 5)
7. Project Manager — backend/agents/project_manager.py (Checkpoint 1)
8. Code Generation v0 — backend/agents/code_generation.py
9. Code Generation OpenHands — backend/agents/code_generation_openhands.py
10. Integration Wiring — backend/agents/integration_wiring.py
11. Project Manager Checkpoint 2 — same file as 7
12. Code Review — backend/agents/code_review.py
13. Security Scanning — backend/agents/security.py (parallel with 14, 15)
14. SEO & Performance — backend/agents/seo.py (parallel with 13, 15)
15. Accessibility — backend/agents/accessibility.py (parallel with 13, 14)
16. QA & Testing — backend/agents/qa.py (bug fix loop max 3x back to Code Gen)
17. Deployment — backend/agents/deploy.py
18. Analytics & Monitoring — backend/agents/analytics.py (parallel with 19)
19. Coding Standards — backend/agents/coding_standards.py (parallel with 18)
20. Post-Deploy Verification — backend/agents/post_deploy_verification.py
21. Delivery — backend/agents/delivery.py

***

## Key Files

### Backend Core
```
backend/main.py                          FastAPI entry point — 17 routers registered, lifespan starts queue worker
backend/orchestration/pipeline.py        LangGraph pipeline — DAG-based agent coordination, error handling, refinement loops
backend/orchestration/executor.py        Pipeline execution runtime — async agent runner with checkpointing
backend/orchestration/checkpointing.py   Checkpoint save/load for crash recovery
backend/orchestration/refinement.py      Agent output quality scoring and refinement feedback loops
backend/orchestration/audit.py           Pipeline audit logging
backend/agents/base.py                   Base class all agents inherit — call_llm() with retry, circuit breaker, model routing
backend/config/settings.py               Env var loading (40+ settings)
backend/config/model_routing.py          Per-agent model selection by complexity × cost profile
backend/config/cost_profiles.py          Budget/balanced/premium cost profile presets
```

### Backend Utilities
```
backend/utils/retry.py                   3-layer retry: LLM call retry, agent-level retry, circuit breaker (per-provider)
backend/utils/error_classifier.py        Structured error classification — 10 categories, resolution strategies, model fallback chains
backend/utils/brief_enhancer.py          Brief completeness scoring (8 dimensions) and template-based enhancement
backend/utils/estimation.py              Pre-execution pipeline cost/time estimation with per-agent token profiles
backend/utils/cost_calculator.py         Per-token cost calculation for 7 model families
backend/utils/cost_optimizer.py          Cost optimization and project cost analysis
backend/utils/llm_client.py              OpenRouter, StabilityAI, Vercel V0 API clients
backend/utils/encryption.py              Fernet credential encryption
backend/utils/crypto.py                  AES-256-CBC credential encryption (production)
backend/utils/agent_analytics.py         Agent performance tracking and QA metrics
backend/utils/deployment_helpers.py      GitHub repo setup, Vercel/Railway deployment
backend/utils/monitoring_helpers.py      Sentry/UptimeRobot integration
```

### Backend API Routes
```
backend/api/projects.py                  Project CRUD, analyze-brief, score-brief, enhance-brief, estimate
backend/api/health.py                    Health checks, circuit breaker status, model routing summary
backend/api/activity.py                  SSE streaming for real-time pipeline events
backend/api/agents.py                    Agent status and logs
backend/api/costs.py                     Cost tracking and analytics
backend/api/database.py                  Database utilities
backend/api/routes/checkpoints.py        Checkpoint pause/resume/replay
backend/api/routes/queue.py              Project queue management
backend/api/routes/export.py             Project and system export (JSON/ZIP)
backend/api/routes/integrations.py       3rd-party integration config (Figma, BrowserStack, etc.)
backend/api/routes/api_keys.py           Encrypted API key storage
backend/api/routes/knowledge.py          Knowledge base CRUD and search
backend/api/routes/mcp.py               MCP server management
backend/api/routes/presets.py            Project preset templates
backend/api/routes/templates.py          Project template management
backend/api/routes/revisions.py          Project revision handling
backend/api/routes/analytics.py          Analytics dashboards
```

### Task Queue
```
backend/task_queue/manager.py            Redis-based FIFO project queue with priority levels
backend/task_queue/worker.py             Background async queue worker — dequeues and executes projects
```

### Frontend Pages
```
frontend/src/pages/NewProject.tsx        Multi-step project wizard — brief scoring, enhancement, cost estimate approval
frontend/src/pages/ProjectView.tsx       Pipeline monitor — DAG viz, activity feed, agent outputs, checkpoints
frontend/src/pages/Home.tsx              Dashboard — stats, recent projects, API key status banner
frontend/src/pages/ProjectHistory.tsx    Project list with search, filtering, export
frontend/src/pages/Settings.tsx          API keys, MCP servers, integrations, theme toggle
frontend/src/pages/AgentLogs.tsx         Agent execution log viewer with filtering
frontend/src/pages/CostDashboard.tsx     Cost analytics — trends, per-agent, model comparisons
frontend/src/pages/KnowledgeBase.tsx     Knowledge base viewer — search, upload, manual entry
frontend/src/pages/Queue.tsx             Queue management — priority, reorder, status
frontend/src/pages/SystemBackup.tsx      Backup/restore — local, S3, per-project export
frontend/src/pages/Login.tsx             Auth — admin setup + login
```

### Frontend Components
```
frontend/src/components/Layout.tsx               Glassmorphic sidebar, mobile header, nav
frontend/src/components/PipelineDAG.tsx           React Flow interactive DAG with SSE live status
frontend/src/components/PipelineVisualization.tsx Linear pipeline progress bar
frontend/src/components/ActivityFeed.tsx          SSE-powered live event stream with error-category icons
frontend/src/components/ArtifactViewer.tsx        Project output display — preview, files, GitHub link
frontend/src/components/AgentOutputTimeline.tsx   Vertical timeline of all 21 agent outputs
frontend/src/components/TemplateBrowser.tsx       Template gallery modal with search and filtering
frontend/src/components/VoiceInput.tsx            Voice-to-text via Web Speech API
frontend/src/components/RevisionPanel.tsx         Revision request panel
frontend/src/components/ScoreGauge.tsx            Animated SVG circular gauge
frontend/src/lib/api.ts                          Axios API client — 60+ functions, all TypeScript types
frontend/src/contexts/AuthContext.tsx             JWT auth with idle timeout
frontend/src/contexts/ThemeContext.tsx            Light/dark/system theme
```

### Infrastructure
```
docker-compose.yml                       3 services: api (8000), dashboard (5173), db (5432)
.env / .env.example                      50+ env vars
Dockerfile                               Python 3.11-slim
start.sh                                 Production startup (Railway)
railway.toml                             Railway deployment config
render.yaml                              Render deployment config
alembic/                                 6 migration files
```

***

## Frontend Routes

| Route | Page | Purpose |
|---|---|---|
| `/` | Home | Dashboard with stats and recent projects |
| `/new` | NewProject | Multi-step project creation wizard |
| `/project/:id` | ProjectView | Pipeline monitor with DAG, activity, outputs |
| `/projects` | ProjectHistory | Browseable project list |
| `/settings` | Settings | API keys, integrations, MCP, theme |
| `/logs` | AgentLogs | Agent execution logs |
| `/costs` | CostDashboard | Cost analytics and trends |
| `/knowledge` | KnowledgeBase | Knowledge base management |
| `/queue` | Queue | Project queue management |
| `/backup` | SystemBackup | Backup and export |
| `/login` | Login | Authentication |

***

## API Endpoints

### Projects
```
POST   /api/projects/                    Create project and enqueue for processing
GET    /api/projects/                    List projects (filter by status, type)
GET    /api/projects/{id}               Get project by ID
DELETE /api/projects/{id}               Delete project
POST   /api/projects/analyze-brief      Real-time brief analysis (keyword-based, no LLM)
POST   /api/projects/score-brief        Brief completeness scoring (8 dimensions)
POST   /api/projects/enhance-brief      Brief enhancement with template-based gap filling
POST   /api/projects/estimate           Pre-execution cost/time estimate (per-agent breakdown)
GET    /api/projects/{id}/outputs       Get agent outputs
POST   /api/projects/{id}/resume        Resume failed/paused project from checkpoint
GET    /api/projects/{id}/checkpoints   Get checkpoint history
GET    /api/projects/{id}/audit-log     Get structured audit log
```

### Health & Monitoring
```
GET    /health                          Basic health check
GET    /health/ready                    Readiness check (DB + API keys)
GET    /health/circuit-breaker          Circuit breaker status per provider
POST   /health/circuit-breaker/reset    Reset circuit breaker (optionally per provider)
GET    /health/model-routing            Full model routing table (agent × cost profile)
```

### Activity
```
GET    /api/activity/{id}/stream        SSE event stream for real-time pipeline progress
```

***

## Database Tables

```
projects              — id, brief, name, status, cost_profile, project_type, agent_outputs JSONB,
                        requirements JSONB, figma_url, integration_config, project_metadata
agent_logs            — per-agent execution (model, tokens, cost, duration, status)
cost_tracking         — token usage and cost per agent per project
deployment_records    — deployment status, URLs, logs
agent_performance     — success rates, QA metrics
qa_failure_patterns   — QA failure pattern tracking
cost_accuracy_tracking — estimated vs actual cost accuracy
pipeline_checkpoints  — checkpoint state for crash recovery
audit_logs            — pipeline event audit trail
knowledge_base        — vector embeddings, knowledge chunks
mcp_credentials       — encrypted MCP server credentials
presets               — project preset templates
project_templates     — reusable project templates
users                 — single-user JWT auth
refresh_tokens        — JWT refresh token storage
```

***

## Environment Variables Required

```
# Required — pipeline won't work without these
OPENROUTER_API_KEY      — All LLM calls (routed via OpenRouter)
VERCEL_V0_API_KEY       — Code Gen v0 agent (web projects)
GITHUB_TOKEN            — Delivery agent (repo creation)
DATABASE_URL            — PostgreSQL connection string
SECRET_KEY              — JWT authentication secret

# Required for specific agents
OPENAI_API_KEY          — Asset Generation (DALL-E)
OPENHANDS_API_URL       — Code Gen OpenHands agent (non-web projects)
TAVILY_API_KEY          — Research agent queries

# Deployment
VERCEL_TOKEN            — Vercel deployment
RAILWAY_TOKEN           — Railway deployment

# Optional integrations
FIGMA_ACCESS_TOKEN      — Figma design extraction
BROWSERSTACK_USERNAME   — Cross-browser QA
BROWSERSTACK_ACCESS_KEY — Cross-browser QA
RESEND_API_KEY          — Email for SaaS projects
R2_ENDPOINT / R2_ACCESS_KEY_ID / R2_SECRET_ACCESS_KEY / R2_BUCKET — Cloudflare R2 storage
INNGEST_EVENT_KEY       — Background job queue
SLACK_WEBHOOK_URL       — Slack notifications
NOTION_TOKEN            — Notion integration

# Monitoring (optional)
SENTRY_DSN              — Error tracking
PLAUSIBLE_API_KEY       — Privacy-focused analytics
GA4_MEASUREMENT_ID      — Google Analytics 4
UPTIMEROBOT_API_KEY     — Uptime monitoring
LIGHTHOUSE_CI_TOKEN     — Performance CI

# Redis (optional but recommended for queue/cache)
REDIS_URL               — Full Redis connection URL
```

***

## Implemented Features

These features are complete and integrated. Do not re-implement them.

### Multi-Layer Retry with Circuit Breakers (#15)
- **Where:** `backend/utils/retry.py`, `backend/agents/base.py`
- 3 layers: LLM call retry (exponential backoff), agent-level retry, per-provider circuit breaker
- Circuit breaker: CLOSED → OPEN (5 failures in 120s) → HALF_OPEN (60s cooldown)
- Health endpoint: `GET /health/circuit-breaker`

### Multi-Model Routing (#7)
- **Where:** `backend/config/model_routing.py`, `backend/agents/base.py`
- All 20 agents classified by complexity (low/medium/high)
- Routes to appropriate model per cost profile (budget/balanced/premium)
- Budget: DeepSeek for cheap agents, Sonnet for critical ones
- Agent overrides: architect, code_generation, code_review always get strong models
- Health endpoint: `GET /health/model-routing`

### Iterative Refinement Loops (#9)
- **Where:** `backend/orchestration/refinement.py`, `backend/orchestration/pipeline.py`
- Quality scoring: completeness, content quality, error-free checks
- Re-runs agent with feedback if score < 0.7 (max 2 iterations)
- Skip list for agents that don't benefit from refinement

### Pre-Execution Cost Estimation (#8)
- **Where:** `backend/utils/estimation.py`, `frontend/src/pages/NewProject.tsx`
- Per-agent token profiles for all 20 agents
- Accounts for project type multiplier, feature/page count, parallel groups
- Shows approval modal with cost breakdown before pipeline starts
- Tiktoken when available, ~4 chars/token fallback

### Self-Healing Error Classification (#27)
- **Where:** `backend/utils/error_classifier.py`
- 10 error categories: transient, rate_limit, auth, quota, validation, model, content, upstream, logic, unknown
- Resolution strategies: retry_backoff, wait_and_retry, fallback_model, rewrite_prompt, fail_fast, notify_user
- Model fallback chains: opus → sonnet → deepseek, gpt-4o → gpt-4o-mini → deepseek
- Integrated into retry system, pipeline error handling, and ActivityFeed UI (category-aware icons)

### Brief Wizard with Prompt Enhancement (#2)
- **Where:** `backend/utils/brief_enhancer.py`, `frontend/src/pages/NewProject.tsx`
- 8-dimension scoring: purpose, audience, features, design, tech_stack, data, pages, scale
- Weighted scoring with project-type-specific boosts
- Template-based enhancement fills missing dimensions without rewriting user text
- Frontend: completeness meter, quality label, suggestions, "Enhance" button
- Endpoints: `POST /projects/score-brief`, `POST /projects/enhance-brief`

### Pipeline DAG Visualization
- **Where:** `frontend/src/components/PipelineDAG.tsx`
- React Flow interactive DAG with live SSE status updates
- Color-coded nodes for queued/running/complete/failed/parallel states

### HITL Approval Gates & Cost Dashboard
- **Where:** `frontend/src/pages/CostDashboard.tsx`
- Per-agent cost tracking, model comparison, build time waterfall
- QA failure pattern analytics

### Checkpointing & Audit Logging
- **Where:** `backend/orchestration/checkpointing.py`, `backend/models/audit_log.py`
- Save/restore pipeline state at checkpoints
- Resume from last checkpoint on failure
- Structured audit trail for all pipeline events

***

## Known Bugs (Updated)

### Fixed
1. ~~Start button does nothing~~ — Fixed: NewProject.tsx now calls POST /api/projects with estimate approval flow
2. ~~Pipeline never progresses~~ — Fixed: async pipeline execution via queue worker
3. ~~MCP Servers page freezes~~ — Fixed: redirect/auth bug resolved
4. ~~Integrations page no API key inputs~~ — Fixed: key inputs, encrypted storage, agent usage
5. ~~Settings page no API key section~~ — Fixed: platform API key management added
6. ~~Knowledge base no upload~~ — Fixed: file upload, text input, agent capture/query
7. ~~Artifact viewer missing~~ — Fixed: ArtifactViewer + AgentOutputTimeline components
8. ~~Pipeline progress view sloppy~~ — Fixed: PipelineDAG (React Flow) + PipelineVisualization
9. ~~Queue not working~~ — Fixed: Redis-based queue with worker, priority, reorder
10. ~~Backup/export not working~~ — Fixed: JSON/ZIP export, backup/restore
11. ~~Light/dark mode broken~~ — Fixed: theme system with glassmorphism CSS variables

### Remaining / Watch For
- MCP server integration is scaffolded but depends on external MCP server processes being available
- Voice input (VoiceInput.tsx) depends on browser Web Speech API support
- Cost estimation accuracy improves with real pipeline runs (confidence starts at 0.75)
- Tiktoken requires network access to download encoding files on first use; falls back to heuristic

***

## Architecture Overview

```
┌──────────────────────────────────────────────────┐
│  React Frontend (Vite, port 5173)                │
│  - 11 pages, 19 components                       │
│  - SSE for real-time pipeline events              │
│  - Axios API client (60+ functions)               │
│  - Auth context (JWT), Theme context              │
└──────────────────────┬───────────────────────────┘
                       │ HTTP / SSE
┌──────────────────────▼───────────────────────────┐
│  FastAPI Backend (port 8000)                      │
│  - 17 routers registered                          │
│  - JWT auth middleware                             │
│  - CORS for localhost:5173/3000                    │
├───────────────────────────────────────────────────┤
│  Project Flow:                                    │
│  1. POST /api/projects → creates DB record        │
│  2. Enqueues to Redis task queue                  │
│  3. QueueWorker dequeues and calls executor       │
│  4. PipelineExecutor runs 20 agents (DAG order)   │
│  5. Each agent: get_model() → call_llm() → save   │
│  6. Retry/circuit breaker/refinement per agent     │
│  7. SSE events streamed to frontend in real-time   │
└──────────────────────┬───────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────┐
│  External Services                                │
│  - PostgreSQL (14+ tables)                        │
│  - Redis (queue + cache)                          │
│  - OpenRouter (LLM API)                           │
│  - Vercel v0 (code generation)                    │
│  - GitHub API (repo delivery)                     │
│  - MCP Servers (8 implementations)                │
└───────────────────────────────────────────────────┘
```

***

## Do NOT Change

- Agent pipeline order — it is correct
- Docker Compose setup — it is the deployment method
- Database schema — unless a fix absolutely requires it
- OpenRouter as the LLM router — it is intentional
- Model routing architecture — centralized in config/model_routing.py
- Error classification categories — they map to specific resolution strategies
- Brief scoring dimensions and weights — tuned for project quality
