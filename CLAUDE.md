
# AI Dev Agency — CLAUDE.md

> Context file for Claude Code. Read this before doing anything else.

***

## What This Project Is

An AI-powered development agency platform. You submit a project brief and a pipeline of 20 AI agents automatically builds an entire application — research, architecture, design, code generation, testing, and deployment. Think personal Devin/Factory-style tool.

**Current state:** Built by Abacus AI Deep Agent. Multiple bugs exist. When a user starts a project, the pipeline gets stuck and nothing happens.

***

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, FastAPI (port 8000) |
| Frontend | React, TypeScript, Vite, Tailwind CSS (port 5173) |
| Database | PostgreSQL — Supabase in production |
| ORM/Migrations | SQLAlchemy + Alembic |
| Pipeline | LangGraph |
| LLM API | OpenRouter |
| Code Gen (Web) | Vercel v0 Platform API |
| Code Gen (Other) | OpenHands API |
| Repo Delivery | GitHub API |
| Infrastructure | Docker Compose |

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

```
backend/orchestration/pipeline.py   START HERE — LangGraph pipeline, root cause of most bugs
backend/main.py                     FastAPI entry point
backend/agents/base.py              Base class all agents inherit from
backend/config/settings.py          Env var loading
frontend/src/pages/NewProject.tsx   Start button bug lives here
frontend/src/pages/ProjectView.tsx  Pipeline progress visualization
docker-compose.yml
.env
```

***

## Database Tables

```
projects           — status, outputs JSONB (per-agent outputs written here)
agent_logs         — one row per agent per project
cost_tracking      — token usage and cost per agent
deployment_records — deployment status per project
```

***

## Environment Variables Required

```
OPENROUTER_API_KEY      — All LLM calls
VERCEL_V0_API_KEY       — Code Gen v0 agent
GITHUB_TOKEN            — Delivery agent
DATABASE_URL            — Supabase PostgreSQL connection string
OPENAI_API_KEY          — Asset Generation (DALL-E)
OPENHANDS_API_URL       — Code Gen OpenHands agent
SLACK_WEBHOOK_URL       — Optional
NOTION_TOKEN            — Optional
SENTRY_DSN              — Monitoring
UPTIMEROBOT_API_KEY     — Monitoring
```

***

## Known Bugs

1. Start button does nothing — NewProject.tsx click handler not calling POST /api/projects
2. Pipeline never progresses — LangGraph pipeline not running async
3. MCP Servers page freezes and logs user out — redirect/auth bug
4. Integrations page — no API key inputs, keys not saved or used by agents
5. Settings page — no section to add platform API keys
6. Knowledge base — no upload or text input, agents not querying or writing to it
7. Project artifact viewer missing — no way to view completed project outputs
8. Pipeline progress view is sloppy — needs full rework
9. Queue not working — multiple projects can't be queued
10. Backup/export not working
11. Light/dark mode broken — many elements invisible in one or both themes

***

## Do NOT Change

- Agent pipeline order — it is correct
- Docker Compose setup — it is the deployment method
- Database schema — unless a fix absolutely requires it
- OpenRouter as the LLM router — it is intentional
- The goal is to fix existing code, not rewrite the architecture


