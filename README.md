# AI Dev Agency

> Universal AI Development Agency System - Autonomous software development using 15+ AI agents

[![Phase](https://img.shields.io/badge/Phase-1%20Complete-green)](./PHASE_TRACKER.md)
[![Agents](https://img.shields.io/badge/Agents-6%2F15-blue)](./PHASE_TRACKER.md)
[![License](https://img.shields.io/badge/License-MIT-yellow)](#license)

An AI-powered software development agency that autonomously handles the entire development lifecycle—from project brief to deployed application—using specialized AI agents orchestrated via LangGraph.

---

## 📐 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AI DEV AGENCY SYSTEM                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐     ┌─────────────────────────────────────────────────┐   │
│  │   Frontend  │     │              Backend (FastAPI)                  │   │
│  │   (React)   │────▶│  ┌─────────────────────────────────────────┐   │   │
│  │             │     │  │           LangGraph Pipeline            │   │   │
│  │  Dashboard  │◀────│  │                                         │   │   │
│  │  - Home     │     │  │  ┌────────┐    ┌──────────┐    ┌─────┐ │   │   │
│  │  - New      │     │  │  │ Intake │───▶│ Research │───▶│Arch.│ │   │   │
│  │  - Projects │     │  │  └────────┘    └──────────┘    └──┬──┘ │   │   │
│  │  - Settings │     │  │                                   │    │   │   │
│  │  - Logs     │     │  │  ┌─────────┐   ┌──────────┐   ┌──▼──┐ │   │   │
│  │  - Costs    │     │  │  │Delivery │◀──│ Code Gen │◀──│Design│ │   │   │
│  └─────────────┘     │  │  └─────────┘   └──────────┘   └─────┘ │   │   │
│        │             │  └─────────────────────────────────────────┘   │   │
│        │             └────────────────────────────────────────────────┘   │
│        │                              │                                    │
│        ▼                              ▼                                    │
│  ┌───────────┐              ┌─────────────────┐                           │
│  │  Nginx    │              │   PostgreSQL    │                           │
│  │  :5173    │              │     :5432       │                           │
│  └───────────┘              └─────────────────┘                           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
             ┌───────────┐     ┌───────────┐     ┌───────────┐
             │ OpenRouter│     │  v0 API   │     │  GitHub   │
             │   (LLM)   │     │ (CodeGen) │     │   API     │
             └───────────┘     └───────────┘     └───────────┘
```

### Agent Pipeline Flow

```
┌──────────────────────────────────────────────────────────────────────┐
│                        PHASE 1 PIPELINE (Current)                    │
└──────────────────────────────────────────────────────────────────────┘

  ┌─────────┐   ┌──────────┐   ┌───────────┐   ┌────────────┐
  │ INTAKE  │──▶│ RESEARCH │──▶│ ARCHITECT │──▶│  DESIGN    │
  │ Agent 1 │   │ Agent 2  │   │  Agent 3  │   │  SYSTEM    │
  └─────────┘   └──────────┘   └───────────┘   │  Agent 4   │
                                                └─────┬──────┘
                                                      │
                    ┌─────────────────────────────────┘
                    ▼
  ┌──────────┐   ┌──────────┐
  │ DELIVERY │◀──│ CODE GEN │
  │ Agent 6  │   │ Agent 5  │
  └──────────┘   │  (v0)    │
                 └──────────┘

┌──────────────────────────────────────────────────────────────────────┐
│                    FULL PIPELINE (Phases 2-7)                        │
└──────────────────────────────────────────────────────────────────────┘

  Intake → Research → Architect → Design System
                                       │
                    ┌──────────────────┼──────────────────┐
                    ▼                  ▼                  ▼
              ┌───────────┐     ┌───────────┐     ┌───────────┐
              │  ASSETS   │     │  CONTENT  │     │    ...    │
              │ (Parallel)│     │ (Parallel)│     │           │
              └─────┬─────┘     └─────┬─────┘     └───────────┘
                    │                 │
                    └────────┬────────┘
                             ▼
              ┌──────────────────────────┐
              │      CODE GENERATION     │
              │  v0 (web) / OpenHands    │
              └────────────┬─────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
  ┌──────────┐      ┌──────────┐      ┌──────────┐
  │ SECURITY │      │   SEO    │      │  A11Y    │
  │(Parallel)│      │(Parallel)│      │(Parallel)│
  └────┬─────┘      └────┬─────┘      └────┬─────┘
       │                 │                 │
       └─────────────────┼─────────────────┘
                         ▼
                    ┌─────────┐     ┌──────────┐
                    │   QA    │◀───▶│ Bug Fix  │
                    │         │     │  Loop    │
                    └────┬────┘     │ (max 3x) │
                         │          └──────────┘
                         ▼
  Deployment → Analytics → Coding Standards → Delivery
```

---

## 🏗️ Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | Python 3.11, FastAPI, SQLAlchemy, Pydantic |
| **Frontend** | React 18, TypeScript, Vite, Tailwind CSS |
| **Database** | PostgreSQL 16 |
| **Orchestration** | LangGraph (LangChain) |
| **Containerization** | Docker, Docker Compose |
| **External APIs** | OpenRouter (LLM), v0 Platform (CodeGen), GitHub |

---

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose (v2.0+)
- Git
- API Keys:
  - [OpenRouter API Key](https://openrouter.ai/)
  - [Vercel v0 API Key](https://v0.dev/)
  - [GitHub Personal Access Token](https://github.com/settings/tokens)

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/ai-dev-agency.git
cd ai-dev-agency

# 2. Copy and configure environment
cp .env.example .env

# 3. Edit .env and add your API keys
nano .env  # or use your preferred editor

# 4. Start all services
docker-compose up -d

# 5. Wait for services to be healthy (about 30 seconds)
docker-compose ps

# 6. Initialize database (first run only)
docker-compose exec api alembic upgrade head
```

### Access Points

| Service | URL | Description |
|---------|-----|-------------|
| **Dashboard** | http://localhost:5173 | React frontend |
| **API** | http://localhost:8000 | FastAPI backend |
| **API Docs** | http://localhost:8000/docs | Swagger UI |
| **Database** | localhost:5432 | PostgreSQL |

---

## 📁 Project Structure

```
ai-dev-agency/
├── backend/
│   ├── agents/                 # Agent implementations
│   │   ├── __init__.py
│   │   ├── base.py            # Base agent class
│   │   ├── intake.py          # Agent 1: Intake & Classification
│   │   ├── research.py        # Agent 2: Research
│   │   ├── architect.py       # Agent 3: Architect
│   │   ├── design_system.py   # Agent 4: Design System
│   │   ├── code_generation.py # Agent 5: Code Gen (v0)
│   │   └── delivery.py        # Agent 6: Delivery
│   ├── api/                   # FastAPI routes
│   │   ├── __init__.py
│   │   ├── projects.py        # Project CRUD endpoints
│   │   ├── agents.py          # Agent test endpoints
│   │   ├── costs.py           # Cost tracking endpoints
│   │   └── health.py          # Health check
│   ├── config/                # Configuration
│   │   ├── settings.py        # App settings
│   │   └── cost_profiles.py   # Model cost configs
│   ├── models/                # SQLAlchemy models
│   │   ├── project.py         # Project model
│   │   ├── agent_log.py       # Agent log model
│   │   ├── cost_tracking.py   # Cost tracking model
│   │   └── deployment_record.py
│   ├── orchestration/         # LangGraph pipeline
│   │   ├── pipeline.py        # Main pipeline definition
│   │   └── executor.py        # Pipeline executor
│   ├── utils/                 # Utilities
│   │   ├── encryption.py      # Credential encryption
│   │   └── cost_calculator.py # Token cost calculation
│   ├── main.py               # FastAPI app entry
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/        # React components
│   │   │   ├── Layout.tsx
│   │   │   ├── Card.tsx
│   │   │   ├── Button.tsx
│   │   │   ├── Input.tsx
│   │   │   ├── Badge.tsx
│   │   │   └── PipelineVisualization.tsx
│   │   ├── pages/             # Page components
│   │   │   ├── Home.tsx
│   │   │   ├── NewProject.tsx
│   │   │   ├── ProjectView.tsx
│   │   │   ├── ProjectHistory.tsx
│   │   │   ├── Settings.tsx
│   │   │   ├── AgentLogs.tsx
│   │   │   └── CostDashboard.tsx
│   │   ├── lib/
│   │   │   └── api.ts         # API client
│   │   ├── types/
│   │   │   └── index.ts       # TypeScript types
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── tailwind.config.js
│   ├── vite.config.ts
│   ├── package.json
│   └── Dockerfile
├── alembic/                   # Database migrations
│   ├── versions/
│   └── env.py
├── docker-compose.yml
├── .env.example
├── PHASE_TRACKER.md          # Development roadmap
└── README.md
```

---

## 📚 API Documentation

### Core Endpoints

#### Projects

```http
POST /api/projects
Content-Type: application/json

{
  "name": "My Dental Website",
  "brief": "Build a landing page for a dental clinic in Austin, TX",
  "cost_profile": "balanced"
}
```

```http
GET /api/projects
GET /api/projects/{project_id}
DELETE /api/projects/{project_id}
GET /api/projects/{project_id}/logs
GET /api/projects/{project_id}/pipeline
```

#### Agents

```http
GET /api/agents                    # List all agents
POST /api/agents/{name}/test       # Test single agent
```

#### Costs

```http
GET /api/costs                     # Cost summary
GET /api/costs/projects/{id}       # Project costs
GET /api/costs/breakdown           # Cost by agent/model
```

### Response Formats

All responses follow this structure:

```json
{
  "success": true,
  "data": { ... },
  "error": null
}
```

For full API documentation, visit http://localhost:8000/docs after starting the system.

---

## 💰 Cost Profiles

| Profile | Models Used | Est. Cost (Simple Site) | Best For |
|---------|-------------|------------------------|----------|
| **Budget** | DeepSeek V3.2, Claude Sonnet | $1-3 | MVPs, prototypes |
| **Balanced** | GPT-5, Claude Sonnet | $5-10 | Production sites |
| **Premium** | Claude Opus everywhere | $15-30 | Complex applications |

---

## 🎨 Design System

The dashboard uses a Perplexity-style dark theme:

```css
/* Colors */
--background-primary: #191A1A;
--background-secondary: #202222;
--accent-primary: #20B8CD;
--accent-secondary: #5B9EF4;
--text-primary: #ECECEC;

/* Typography */
--font-family: 'Inter', sans-serif;
--font-mono: 'JetBrains Mono', monospace;
```

---

## 🛠️ Development

### Running Locally (Without Docker)

#### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/ai_dev_agency
export OPENROUTER_API_KEY=your-key

# Run
uvicorn main:app --reload --port 8000
```

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Database Migrations

```bash
# Create new migration
cd backend
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Testing Individual Agents

```bash
# Test Intake Agent
curl -X POST http://localhost:8000/api/agents/intake/test \
  -H "Content-Type: application/json" \
  -d '{"brief": "Build a landing page for a dental clinic"}'

# Test Research Agent
curl -X POST http://localhost:8000/api/agents/research/test \
  -H "Content-Type: application/json" \
  -d '{"brief": "Build a landing page for a dental clinic", "intake_output": {...}}'
```

---

## 🔧 Troubleshooting

### Common Issues

#### Docker containers won't start

```bash
# Check logs
docker-compose logs api
docker-compose logs db

# Rebuild containers
docker-compose down -v
docker-compose up --build -d
```

#### Database connection errors

```bash
# Check if database is ready
docker-compose exec db pg_isready -U postgres

# Reset database
docker-compose down -v
docker-compose up -d db
sleep 10
docker-compose up -d
```

#### API returns 500 errors

```bash
# Check API logs
docker-compose logs -f api

# Verify environment variables
docker-compose exec api env | grep -E "OPENROUTER|GITHUB|V0"
```

#### Frontend not loading

```bash
# Check frontend build
docker-compose logs dashboard

# Rebuild frontend
docker-compose build dashboard
docker-compose up -d dashboard
```

### Health Checks

```bash
# API health
curl http://localhost:8000/health

# Database health
docker-compose exec db pg_isready -U postgres

# All services
docker-compose ps
```

---

## 📊 Monitoring

### Viewing Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api

# Last 100 lines
docker-compose logs --tail=100 api
```

### Cost Tracking

Access the Cost Dashboard at http://localhost:5173/costs to view:
- Total spend by model
- Cost per project
- Agent-level breakdown
- Spending trends

---

## 🗺️ Roadmap

See [PHASE_TRACKER.md](./PHASE_TRACKER.md) for the complete development roadmap.

### Phase Status

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Core Infrastructure (6 agents) | ✅ Complete |
| 2 | Asset & Content Generation | ⏳ Pending |
| 3 | MCP Server Integration (8 servers) | ⏳ Pending |
| 4 | Quality & Compliance (Security, SEO, A11y) | ⏳ Pending |
| 5 | QA & Deployment | ⏳ Pending |
| 6 | Monitoring & Standards | ⏳ Pending |
| 7 | Advanced Features (8 more project types) | ⏳ Pending |

---

## 📄 Environment Variables

```bash
# Required
DATABASE_URL=postgresql://user:pass@db:5432/ai_dev_agency
OPENROUTER_API_KEY=your-openrouter-key
VERCEL_V0_API_KEY=your-v0-key
GITHUB_TOKEN=your-github-pat

# Optional (Phase 2+)
OPENAI_API_KEY=your-openai-key-for-dalle
TAVILY_API_KEY=your-tavily-key
VERCEL_TOKEN=your-vercel-token
RAILWAY_TOKEN=your-railway-token
SENTRY_DSN=your-sentry-dsn
SLACK_WEBHOOK_URL=your-slack-webhook
```

---

## 🤝 Contributing

1. Check [PHASE_TRACKER.md](./PHASE_TRACKER.md) for current priorities
2. Fork the repository
3. Create a feature branch
4. Make your changes
5. Submit a pull request

---

## 📄 License

MIT License - see [LICENSE](./LICENSE) for details.

---

## 🔗 Links

- [Phase Tracker](./PHASE_TRACKER.md) - Detailed development roadmap
- [API Documentation](http://localhost:8000/docs) - Swagger UI (when running)
- [OpenRouter](https://openrouter.ai/) - LLM API provider
- [v0 by Vercel](https://v0.dev/) - Code generation platform
