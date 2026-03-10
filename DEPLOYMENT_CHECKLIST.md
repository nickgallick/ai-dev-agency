# Deployment Checklist for AI Dev Agency

Use this checklist to verify everything is properly configured before deployment.

---

## 🔑 Pre-Deployment: API Keys

### Required APIs
- [ ] **OpenRouter API Key** obtained and tested
  - Key format: `sk-or-...`
  - Added credits/billing configured
  - Test: `curl -H "Authorization: Bearer $OPENROUTER_API_KEY" https://openrouter.ai/api/v1/models`

- [ ] **Vercel v0 API Key** obtained
  - Key configured in settings
  - Rate limits understood

- [ ] **GitHub Personal Access Token** created
  - Key format: `ghp_...`
  - Scopes: `repo`, `workflow`
  - Test: `curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user`

- [ ] **SECRET_KEY** generated
  - At least 32 characters
  - Randomly generated (not a simple password)

---

## 📁 File Configuration

### Environment File
- [ ] `.env` file created from `.env.example`
- [ ] All required variables filled in:
  ```
  OPENROUTER_API_KEY=✓
  VERCEL_V0_API_KEY=✓
  GITHUB_TOKEN=✓
  SECRET_KEY=✓
  DATABASE_URL=✓ (default is fine)
  ```
- [ ] No placeholder values remaining (search for "your-", "change-me")
- [ ] `.env` file NOT committed to git (check `.gitignore`)

### Project Files
- [ ] `docker-compose.yml` present and valid
- [ ] `backend/Dockerfile` present
- [ ] `frontend/Dockerfile` present
- [ ] `backend/requirements.txt` present
- [ ] `frontend/package.json` present

---

## 🐳 Docker Configuration

### Docker Installation
- [ ] Docker installed: `docker --version`
- [ ] Docker Compose installed: `docker-compose --version`
- [ ] Docker daemon running: `docker ps`

### Build Verification
```bash
# Build all images
docker-compose build
```
- [ ] Backend image builds successfully
- [ ] Frontend image builds successfully
- [ ] No build errors or warnings

---

## 🚀 Deployment Steps

### Step 1: Clone and Configure
```bash
git clone <your-repo-url>
cd ai-dev-agency
cp .env.example .env
# Edit .env with your API keys
```
- [ ] Repository cloned
- [ ] .env file configured

### Step 2: Start Services
```bash
docker-compose up -d
```
- [ ] Command executed without errors

### Step 3: Verify Services Running
```bash
docker-compose ps
```
- [ ] `api` service: Running (healthy)
- [ ] `dashboard` service: Running
- [ ] `db` service: Running (healthy)

### Step 4: Check Logs for Errors
```bash
# Check all logs
docker-compose logs

# Check specific service
docker-compose logs api
docker-compose logs dashboard
docker-compose logs db
```
- [ ] No critical errors in logs
- [ ] Database connection successful
- [ ] API started on port 8000

### Step 5: Run Database Migrations
```bash
docker-compose exec api alembic upgrade head
```
- [ ] Migrations completed successfully
- [ ] All tables created

---

## ✅ Health Checks

### API Health
```bash
curl http://localhost:8000/health
```
- [ ] Returns `{"status": "healthy"}`

### Frontend Access
```bash
curl -I http://localhost:5173
```
- [ ] Returns HTTP 200
- [ ] Open browser to http://localhost:5173
- [ ] Dashboard loads correctly

### Database Connection
```bash
docker-compose exec db psql -U postgres -d ai_dev_agency -c "\dt"
```
- [ ] Tables displayed (projects, agent_logs, etc.)

### API Endpoints
```bash
# List projects
curl http://localhost:8000/api/projects

# Test agent endpoint
curl -X POST http://localhost:8000/api/test/intake \
  -H "Content-Type: application/json" \
  -d '{"brief": "Test project"}'
```
- [ ] Projects endpoint returns JSON (even if empty array)
- [ ] Test endpoint responds (may return error if API key not set)

---

## 🔒 Security Checklist

- [ ] SECRET_KEY is unique and random
- [ ] `.env` file has restricted permissions: `chmod 600 .env`
- [ ] API keys are not exposed in logs
- [ ] Database password changed from default (for production)
- [ ] HTTPS configured (for production deployment)

---

## 📊 Post-Deployment Verification

### Functional Tests
- [ ] Can create a new project from dashboard
- [ ] Project appears in project list
- [ ] Agent logs are being recorded
- [ ] Can view project details

### Integration Tests
- [ ] OpenRouter API connection working
  - Create test project, verify Intake Agent runs
- [ ] GitHub integration working (if configured)
  - Check repo creation capability

---

## 🛠️ Common Issues & Solutions

### Issue: Database connection refused
```bash
# Check if db is running
docker-compose ps db

# Restart db service
docker-compose restart db

# Check db logs
docker-compose logs db
```

### Issue: API health check failing
```bash
# Check API logs
docker-compose logs api

# Restart API service
docker-compose restart api

# Rebuild if needed
docker-compose build api
docker-compose up -d api
```

### Issue: Frontend not loading
```bash
# Check nginx config
docker-compose exec dashboard cat /etc/nginx/conf.d/default.conf

# Rebuild frontend
docker-compose build dashboard
docker-compose up -d dashboard
```

### Issue: "Invalid API Key" errors
- Verify key is correct in `.env`
- Check for extra spaces or newlines
- Verify key hasn't expired
- Check billing/credits on API provider

---

## 📋 Quick Commands Reference

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# View logs (follow mode)
docker-compose logs -f

# Restart a service
docker-compose restart <service-name>

# Rebuild and restart
docker-compose up -d --build

# Check service status
docker-compose ps

# Execute command in container
docker-compose exec api bash
docker-compose exec db psql -U postgres

# Remove all data and start fresh
docker-compose down -v
docker-compose up -d
```

---

## ✅ Final Checklist

Before considering deployment complete:

- [ ] All required API keys configured
- [ ] All Docker services running and healthy
- [ ] Database migrations applied
- [ ] API health check passing
- [ ] Dashboard accessible and functional
- [ ] Can create and track a test project
- [ ] Logs show no critical errors
- [ ] Security measures in place

---

**Deployment Status:** ⬜ Not Started | 🟡 In Progress | ✅ Complete

**Date:** _______________

**Deployed by:** _______________

**Notes:**
```

```
