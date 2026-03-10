# AI Dev Agency - Phase Handoff Messages

> Ready-to-copy messages for continuing development in new conversations.
> Just copy the entire code block and paste into a new DeepAgent session.

---

## 📋 Message to Start Phase 2

**What this phase accomplishes:** Adds Asset Generation (DALL-E) and Content Generation agents that run in parallel after the Design System agent completes. These create images (logos, hero images, icons) and SEO-optimized copy (headlines, CTAs, body text).

```
Continue developing the AI Dev Agency project at /home/ubuntu/ai-dev-agency

First, read /home/ubuntu/ai-dev-agency/PHASE_TRACKER.md to understand the full project scope and current status.

Your task is to implement **Phase 2: Asset & Content Generation**

### Key Deliverables:

1. **Create `backend/agents/asset_generation.py`**
   - Integrate with OpenAI DALL-E API (add OPENAI_API_KEY to .env)
   - Generate: logo, hero images, feature icons, social preview images
   - Save images to project `assets/` folder
   - Return asset manifest with paths and descriptions
   - Follow the existing agent pattern in `backend/agents/base.py`

2. **Create `backend/agents/content_generation.py`**
   - Generate headlines, body copy, CTAs per page
   - Use research output for tone and keywords
   - Support multiple content variants
   - Output structured JSON with content by section

3. **Update `backend/orchestration/pipeline.py`**
   - Add Asset & Content nodes to the LangGraph pipeline
   - Configure parallel execution (use LangGraph's parallel primitive)
   - Both agents receive Design System output as input
   - Both must complete before Code Generation begins

4. **Update `.env.example`** to include:
   ```
   OPENAI_API_KEY=your-openai-key-for-dalle
   ```

5. **Update Frontend**
   - Update pipeline visualization to show parallel agents
   - Add asset preview to Project View page
   - Add content preview/edit capability

### Reference Files:
- Agent base class: `backend/agents/base.py`
- Example agent: `backend/agents/intake.py`
- Pipeline: `backend/orchestration/pipeline.py`
- Cost profiles: `backend/config/cost_profiles.py`

### Quick Start:
```bash
cd /home/ubuntu/ai-dev-agency
git status
docker-compose up -d
# Dashboard: http://localhost:5173
# API: http://localhost:8000
```

After completing, update PHASE_TRACKER.md to mark Phase 2 as complete and commit all changes.
```

---

## 📋 Message to Start Phase 3

**What this phase accomplishes:** Integrates 8 MCP (Model Context Protocol) servers to give agents access to external tools like filesystem, GitHub, PostgreSQL, browser automation, Slack, Notion, memory persistence, and HTTP fetch capabilities.

```
Continue developing the AI Dev Agency project at /home/ubuntu/ai-dev-agency

First, read /home/ubuntu/ai-dev-agency/PHASE_TRACKER.md to understand the full project scope and current status.

Your task is to implement **Phase 3: MCP Server Integration Layer**

### Key Deliverables:

1. **Create MCP directory structure:**
   ```
   backend/mcp/
   ├── __init__.py
   ├── manager.py          # MCP connection manager
   ├── servers/
   │   ├── __init__.py
   │   ├── filesystem.py   # @modelcontextprotocol/server-filesystem
   │   ├── github_mcp.py   # @modelcontextprotocol/server-github
   │   ├── postgres_mcp.py # @modelcontextprotocol/server-postgres
   │   ├── browser.py      # @anthropic/mcp-server-puppeteer
   │   ├── slack.py        # @modelcontextprotocol/server-slack
   │   ├── notion.py       # notion-mcp-server
   │   ├── memory.py       # @modelcontextprotocol/server-memory
   │   └── fetch.py        # @modelcontextprotocol/server-fetch
   └── config.py           # MCP server configurations
   ```

2. **Implement MCP Manager class:**
   - Connection pooling and lifecycle management
   - Health checks per server
   - Request routing to appropriate servers
   - Error handling and fallbacks

3. **Create `backend/config/mcp_config.py`:**
   ```python
   MCP_SERVERS = {
       "filesystem": {
           "enabled": True,
           "source": "@modelcontextprotocol/server-filesystem",
           "config": {"allowed_paths": ["/tmp/projects"]},
       },
       "github": {...},
       "postgres": {...},
       "browser": {...},
       "slack": {...},
       "notion": {...},
       "memory": {...},
       "fetch": {...}
   }
   ```

4. **Update agents to use MCP tools:**
   - Research agent: Browser MCP for competitor scraping
   - Architect agent: Filesystem MCP for reading existing projects
   - Delivery agent: GitHub MCP for repo operations

5. **Update Frontend Settings page:**
   - Add MCP Server Management UI
   - List all configured MCP servers with status
   - Show which agents use each server
   - Add "Test Connection" button for each server
   - "Add Custom MCP Server" functionality

6. **Add environment variables to `.env.example`:**
   ```
   SLACK_WEBHOOK_URL=your-slack-webhook
   NOTION_TOKEN=your-notion-token
   ```

7. **Update Docker Compose** if MCP servers need containers

### Reference Files:
- Settings page: `frontend/src/pages/Settings.tsx`
- Example agent: `backend/agents/research.py`
- Config system: `backend/config/settings.py`

### Quick Start:
```bash
cd /home/ubuntu/ai-dev-agency
git status
docker-compose up -d
```

After completing, update PHASE_TRACKER.md to mark Phase 3 as complete and commit all changes.
```

---

## 📋 Message to Start Phase 4

**What this phase accomplishes:** Adds 3 parallel-executing quality agents - Security Scanning (Semgrep), SEO & Performance (Lighthouse), and Accessibility (axe-core). These run after Code Generation to validate quality before QA.

```
Continue developing the AI Dev Agency project at /home/ubuntu/ai-dev-agency

First, read /home/ubuntu/ai-dev-agency/PHASE_TRACKER.md to understand the full project scope and current status.

Your task is to implement **Phase 4: Quality & Compliance**

### Key Deliverables:

1. **Create `backend/agents/security.py`**
   - Integrate with Semgrep CLI (Docker container)
   - Scan generated code for vulnerabilities
   - Check npm dependencies for known CVEs
   - Generate security report with severity levels
   - Auto-fix common issues where possible

2. **Create `backend/agents/seo.py`**
   - Integrate with Lighthouse CLI (Docker container)
   - Audit SEO score, performance, best practices
   - Generate optimized meta tags
   - Create sitemap.xml and robots.txt
   - Validate structured data (JSON-LD)

3. **Create `backend/agents/accessibility.py`**
   - Integrate with Playwright + axe-core
   - Scan all pages for WCAG 2.1 AA compliance
   - Generate accessibility report
   - Suggest fixes for common issues

4. **Update `backend/orchestration/pipeline.py`:**
   - Add Security, SEO, Accessibility nodes
   - Configure parallel execution (all 3 run simultaneously)
   - All receive Code Generation output as input
   - All must complete before QA Agent

5. **Add Docker services to `docker-compose.yml`:**
   ```yaml
   semgrep:
     image: semgrep/semgrep:latest
     volumes:
       - ./tmp:/tmp
   
   playwright:
     image: mcr.microsoft.com/playwright:latest
   
   lighthouse:
     image: femtopixel/google-lighthouse:latest
   ```

6. **Add environment variables to `.env.example`:**
   ```
   SEMGREP_API_TOKEN=optional-for-pro-features
   ```

7. **Update Frontend:**
   - Show Quality Reports section in Project View
   - Display security vulnerabilities with severity badges
   - Show Lighthouse scores with visual gauges
   - Show accessibility issues with WCAG references

### Reference Files:
- Agent base class: `backend/agents/base.py`
- Pipeline: `backend/orchestration/pipeline.py`
- Project View page: `frontend/src/pages/Project.tsx`

### Quick Start:
```bash
cd /home/ubuntu/ai-dev-agency
git status
docker-compose up -d
```

After completing, update PHASE_TRACKER.md to mark Phase 4 as complete and commit all changes.
```

---

## 📋 Message to Start Phase 5

**What this phase accomplishes:** Adds QA & Testing agent with a bug fix loop (max 3 iterations) and multi-platform Deployment agent supporting Vercel, Railway, and Supabase.

```
Continue developing the AI Dev Agency project at /home/ubuntu/ai-dev-agency

First, read /home/ubuntu/ai-dev-agency/PHASE_TRACKER.md to understand the full project scope and current status.

Your task is to implement **Phase 5: QA & Deployment**

### Key Deliverables:

1. **Create `backend/agents/qa.py`**
   - Run Playwright e2e tests on generated code
   - Visual regression testing (screenshot comparison)
   - Check design compliance vs Design System output
   - Implement bug fix loop:
     - If bugs found, send back to Code Generation agent
     - Maximum 3 fix loops before marking as "needs-manual-review"
     - Track bug history in project metadata
   - Regression testing after each fix

2. **Create `backend/agents/deploy.py`**
   - Vercel deployment integration (frontend)
   - Railway deployment for backend services
   - Supabase setup for database projects
   - Environment variable configuration
   - Custom domain setup (if provided by user)
   - Health check after deployment

3. **Update pipeline with bug fix loop logic:**
   ```
   Code Gen → Security/SEO/A11y → QA 
       ↑__________________________|
            (if bugs, max 3x)
   ```

4. **Add environment variables to `.env.example`:**
   ```
   VERCEL_TOKEN=your-vercel-token
   RAILWAY_TOKEN=your-railway-token
   SUPABASE_ACCESS_TOKEN=your-supabase-token
   ```

5. **Update Frontend:**
   - Add deployment controls to Project View (Deploy button, platform selector)
   - Show QA results and bug fix history with iteration count
   - Display live URL after deployment
   - Show deployment logs in real-time

### Pipeline Flow After This Phase:
```
Intake → Research → Architect → Design System 
    → Asset Gen + Content Gen (parallel)
    → Code Gen → Security + SEO + A11y (parallel) 
    → QA (with bug fix loop back to Code Gen, max 3x)
    → Deploy → Delivery
```

### Reference Files:
- Pipeline: `backend/orchestration/pipeline.py`
- Code Gen agent: `backend/agents/code_generation.py`
- Project View: `frontend/src/pages/Project.tsx`

### Quick Start:
```bash
cd /home/ubuntu/ai-dev-agency
git status
docker-compose up -d
```

After completing, update PHASE_TRACKER.md to mark Phase 5 as complete and commit all changes.
```

---

## 📋 Message to Start Phase 6

**What this phase accomplishes:** Adds Analytics & Monitoring agent (Plausible, Sentry, UptimeRobot integration) and Coding Standards agent (README, API docs, architecture diagrams, linting configs).

```
Continue developing the AI Dev Agency project at /home/ubuntu/ai-dev-agency

First, read /home/ubuntu/ai-dev-agency/PHASE_TRACKER.md to understand the full project scope and current status.

Your task is to implement **Phase 6: Monitoring & Standards**

### Key Deliverables:

1. **Create `backend/agents/analytics.py`**
   - Integrate Plausible Analytics (self-hosted or cloud)
   - Set up Sentry error tracking in generated projects
   - Configure UptimeRobot monitoring for deployed URLs
   - Generate analytics dashboard config
   - Add monitoring scripts to generated project

2. **Create `backend/agents/coding_standards.py`**
   - Generate comprehensive README.md for the project
   - Create API documentation (OpenAPI spec if applicable)
   - Generate architecture diagrams using Mermaid syntax
   - Create CONTRIBUTING.md with contribution guidelines
   - Generate CHANGELOG.md template
   - Set up linting configs (ESLint, Prettier, .editorconfig)
   - Add pre-commit hooks configuration

3. **Add environment variables to `.env.example`:**
   ```
   SENTRY_DSN=your-sentry-dsn
   PLAUSIBLE_INSTANCE_URL=https://plausible.yourdomain.com
   UPTIMEROBOT_API_KEY=your-uptimerobot-key
   ```

4. **Update Delivery Agent:**
   - Include monitoring config in delivery package
   - Add setup instructions for analytics

5. **Update Frontend:**
   - Show monitoring status in Project View
   - Display generated documentation preview
   - Link to Sentry/Plausible dashboards if configured

### Pipeline Flow After This Phase:
```
... → QA → Deploy → Analytics & Monitoring → Coding Standards → Delivery
```

### Reference Files:
- Delivery agent: `backend/agents/delivery.py`
- Project View: `frontend/src/pages/Project.tsx`

### Quick Start:
```bash
cd /home/ubuntu/ai-dev-agency
git status
docker-compose up -d
```

After completing, update PHASE_TRACKER.md to mark Phase 6 as complete and commit all changes.
```

---

## 📋 Message to Start Phase 7

**What this phase accomplishes:** The final and most complex phase. Adds 8 new project types (mobile, desktop, CLI, browser extension), OpenHands/Codex integration for non-web code generation, project revision system with chat-like interface, smart cost optimization, and mobile/desktop deployment credentials management.

```
Continue developing the AI Dev Agency project at /home/ubuntu/ai-dev-agency

First, read /home/ubuntu/ai-dev-agency/PHASE_TRACKER.md to understand the full project scope and current status.

Your task is to implement **Phase 7: Advanced Features**

This is the largest phase with multiple sub-components. Implement in this order:

### Part A: Additional Project Types (8 new types)

Add support for these project types in the Intake agent and throughout the pipeline:

| Type | Key | Description |
|------|-----|-------------|
| Mobile App (React Native) | `mobile_react_native` | Cross-platform mobile apps |
| Mobile App (Flutter) | `mobile_flutter` | Cross-platform with Dart |
| iOS Native | `mobile_ios` | Swift/SwiftUI apps |
| Android Native | `mobile_android` | Kotlin apps |
| Desktop (Electron) | `desktop_electron` | Cross-platform desktop |
| Desktop (Tauri) | `desktop_tauri` | Lightweight Rust-based desktop |
| CLI Tool | `cli` | Command-line tools |
| Browser Extension | `browser_extension` | Chrome/Firefox extensions |

### Part B: OpenHands/Codex Integration

1. **Create `backend/agents/code_generation_openhands.py`**
   - Integrate with OpenHands API for backend/mobile/desktop code
   - Support for all non-web project types
   - Coordinate with v0 agent for full-stack projects

2. **Add Docker service:**
   ```yaml
   openhands:
     image: ghcr.io/all-hands-ai/openhands:latest
   ```

3. **Create `backend/agents/integration_wiring.py`**
   - Wire frontend (v0) to backend (OpenHands) when both exist
   - API endpoint connection and environment variable setup

### Part C: Project Revision System

1. **Database changes:**
   ```sql
   ALTER TABLE projects ADD COLUMN revision_history JSONB DEFAULT '[]';
   ALTER TABLE projects ADD COLUMN parent_project_id UUID;
   ALTER TABLE projects ADD COLUMN revision_number INTEGER DEFAULT 0;
   ```

2. **Implement revision workflow:**
   - "Request Changes" button in Project View
   - Chat-like interface for revision requests
   - Pull latest code from project GitHub repo
   - Classify revision scope (small/medium/major)
   - Only activate relevant agents for the change
   - QA tests new feature + regression tests
   - Push update to same deployment

3. **Implement rollback:**
   - Show full revision history
   - Rollback to any previous version via Git checkout

### Part D: Smart Cost Optimization Engine

1. **Create `backend/utils/cost_optimizer.py`:**
   - Track quality outcomes per agent per model
   - Record: did output pass QA on first try?
   - Record: how many revisions needed?
   - Dynamically adjust model selection based on history

2. **Implement learning cost profiles:**
   - If model X consistently works for simple projects, prefer it
   - Escalate to better models only when needed
   - Show estimated cost BEFORE starting project

### Part E: Deployment Credentials (Mobile & Desktop)

1. **Database:** Add encrypted credentials storage

2. **Settings page sections:**
   - Apple Developer credentials (iOS/macOS)
   - Google Play credentials (Android)
   - Expo credentials
   - Windows code signing certificate
   - Mac notarization setup

### Part F: Additional Frontend Features

- Voice input via browser speech-to-text API
- PWA support with service worker
- Push notifications for project events
- Offline support for viewing project history

### Environment Variables:
```
OPENHANDS_API_URL=http://openhands:3000
```

### Quick Start:
```bash
cd /home/ubuntu/ai-dev-agency
git status
docker-compose up -d
```

After completing, update PHASE_TRACKER.md to mark Phase 7 as complete and the project as feature-complete. Commit all changes.
```

---

## 🔄 General Session Resume Message

Use this if you just need to quickly resume work without a specific phase focus:

```
Resume working on the AI Dev Agency project at /home/ubuntu/ai-dev-agency

Please:
1. Read /home/ubuntu/ai-dev-agency/PHASE_TRACKER.md to understand current status
2. Run `git status` to check for any uncommitted changes
3. Run `docker-compose ps` to check service status
4. Start the services if not running: `docker-compose up -d`
5. Let me know the current state and what phase we should work on next

Quick links after startup:
- Dashboard: http://localhost:5173
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
```

---

## 🐛 Debugging Session Message

Use this if something is broken and you need to troubleshoot:

```
Debug issues with the AI Dev Agency project at /home/ubuntu/ai-dev-agency

Please:
1. Read /home/ubuntu/ai-dev-agency/PHASE_TRACKER.md for context
2. Check service status: `docker-compose ps`
3. Check logs: `docker-compose logs --tail=100`
4. Check API health: `curl http://localhost:8000/health`
5. Check database: `docker-compose exec db psql -U postgres -d aidev -c "SELECT * FROM projects LIMIT 5;"`

Identify and fix any issues found. The system should have:
- API running on port 8000
- Frontend dashboard on port 5173  
- PostgreSQL database on port 5432

After fixing, test by creating a simple project through the API or dashboard.
```

---

*Last updated: March 9, 2026*
