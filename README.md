# AI Dev Agency

> Universal AI Development Agency System - Phase 1

An AI-powered software development agency that autonomously handles the entire development lifecycle using 6 core agents.

## 🏗️ Architecture

### Core Agents (Phase 1)

1. **Intake & Classification** - Analyzes project briefs, classifies project type
2. **Research** - Researches competitors, design trends, best practices
3. **Architect** - Creates detailed technical architecture and build plans
4. **Design System** - Generates comprehensive design tokens and styles
5. **Code Generation** - Uses v0 Platform API for frontend code generation
6. **Delivery** - Creates GitHub repo, prepares delivery package

### Tech Stack

- **Backend**: Python FastAPI, SQLAlchemy, LangGraph
- **Frontend**: React, Vite, Tailwind CSS
- **Database**: PostgreSQL
- **Orchestration**: LangGraph pipeline
- **External APIs**: OpenRouter (LLM), v0 Platform API (code gen), GitHub

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- API keys for: OpenRouter, v0 Platform, GitHub

### Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/ai-dev-agency.git
cd ai-dev-agency

# Copy and configure environment
cp .env.example .env
# Edit .env and add your API keys

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f
```

### Access

- **Dashboard**: http://localhost:5173
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## 📁 Project Structure

```
ai-dev-agency/
├── backend/
│   ├── agents/          # Agent implementations
│   ├── api/             # FastAPI routes
│   ├── config/          # Configuration
│   ├── models/          # SQLAlchemy models
│   ├── orchestration/   # LangGraph pipeline
│   ├── utils/           # Helper functions
│   ├── main.py          # FastAPI app
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/  # React components
│   │   ├── pages/       # Page components
│   │   ├── hooks/       # Custom hooks
│   │   ├── lib/         # API client
│   │   └── types/       # TypeScript types
│   ├── package.json
│   └── tailwind.config.js
├── alembic/             # Database migrations
├── docker-compose.yml
├── .env.example
└── README.md
```

## 📊 Database Schema

### Tables

- **projects** - Project records with brief, status, outputs
- **agent_logs** - LLM call logs for debugging and cost tracking
- **cost_tracking** - Aggregated cost data per project
- **deployment_records** - Deployment history

## 💰 Cost Profiles

| Profile  | Description                     | Est. Cost (Simple) |
|----------|--------------------------------|--------------------|
| Budget   | Cheapest models, basic quality | $1-3              |
| Balanced | Good quality, reasonable cost  | $5-10             |
| Premium  | Best models everywhere         | $15-30            |

## 🎨 Design System

The frontend uses a Perplexity-style dark theme:

- **Background**: #191A1A (primary), #202222 (secondary)
- **Accent**: #20B8CD (primary), #5B9EF4 (secondary)
- **Text**: #ECECEC (primary), #989898 (secondary)

## 🔧 Development

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Database Migrations

```bash
cd backend
alembic upgrade head
alembic revision --autogenerate -m "description"
```

## 📄 License

MIT
