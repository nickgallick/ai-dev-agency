# 🚀 AI Dev Agency - Production Deployment Guide

## GitHub Repository
Your code has been pushed to:
**https://github.com/nickgallick/ai-dev-agency**

---

## Option 1: Deploy to Railway (Recommended)

### Step 1: Go to Railway
1. Visit [railway.app](https://railway.app/)
2. Sign in or create an account

### Step 2: Create New Project
1. Click **"New Project"**
2. Select **"Deploy from GitHub repo"**
3. Find and select: `nickgallick/ai-dev-agency`

### Step 3: Add PostgreSQL Database
1. In your Railway project, click **"+ New"**
2. Select **"Database" → "PostgreSQL"**
3. Railway will automatically create a PostgreSQL database

### Step 4: Set Environment Variables
Go to your main service (the one from GitHub), click on **"Variables"**, and add:

```
# Required
DATABASE_URL=${{Postgres.DATABASE_URL}}  # Railway reference to PostgreSQL
OPENROUTER_API_KEY=your-openrouter-api-key
TAVILY_API_KEY=your-tavily-api-key
GITHUB_TOKEN=your-github-personal-access-token
JWT_SECRET=your-secure-jwt-secret-256-bit
PRODUCTION=true
SECRET_KEY=your-secure-random-secret-key

# Optional - fill in as needed
VERCEL_V0_API_KEY=
SENTRY_DSN=
SLACK_WEBHOOK_URL=
```

### Step 5: Configure Build Settings
Railway should auto-detect the Dockerfile. If not:
1. Go to **Settings** → **Build**
2. Set **Builder**: Dockerfile
3. Set **Dockerfile Path**: Dockerfile

### Step 6: Deploy
1. Railway will automatically start building
2. Watch the build logs for any errors
3. Once deployed, click **"Settings" → "Domains" → "Generate Domain"**

### Step 7: Access Your App
Railway will provide a URL like: `https://ai-dev-agency-production.up.railway.app`

---

## Option 2: Deploy to Render

### Step 1: Create New Web Service
1. Visit [render.com](https://render.com/)
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repo: `nickgallick/ai-dev-agency`

### Step 2: Configure Service
```
Name: ai-dev-agency
Environment: Docker
Dockerfile Path: ./Dockerfile
```

### Step 3: Add PostgreSQL
1. Create a new PostgreSQL database on Render
2. Copy the Internal Database URL

### Step 4: Set Environment Variables
Same as Railway (see above)

---

## Option 3: Deploy to Fly.io

```bash
# Install Fly CLI
curl -L https://fly.io/install.sh | sh

# Login
fly auth login

# Create app
fly launch --name ai-dev-agency

# Create PostgreSQL
fly postgres create --name ai-dev-agency-db

# Attach database
fly postgres attach ai-dev-agency-db

# Set secrets
fly secrets set OPENROUTER_API_KEY=your-openrouter-api-key
fly secrets set TAVILY_API_KEY=your-tavily-api-key
fly secrets set JWT_SECRET=your-jwt-secret
fly secrets set PRODUCTION=true

# Deploy
fly deploy
```

---

## Admin Access

After deployment, access:
- **Dashboard**: `https://your-app-url.com`
- **API Docs**: `https://your-app-url.com/docs`
- **Health Check**: `https://your-app-url.com/health`

### Default Admin User
- **Email**: `admin@example.com`
- **Password**: `admin12345`

⚠️ **IMPORTANT**: Change the admin password immediately after first login!

---

## Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | ✅ | PostgreSQL connection string |
| `OPENROUTER_API_KEY` | ✅ | OpenRouter API key for LLM access |
| `JWT_SECRET` | ✅ | Secret key for JWT tokens |
| `PRODUCTION` | ✅ | Set to "true" for production |
| `TAVILY_API_KEY` | ⚠️ | Required for research agent |
| `GITHUB_TOKEN` | ⚠️ | Required for GitHub delivery |
| `SECRET_KEY` | ⚠️ | App secret key |
| `VERCEL_V0_API_KEY` | ❌ | Optional: v0 code generation |
| `SENTRY_DSN` | ❌ | Optional: Error tracking |
| `SLACK_WEBHOOK_URL` | ❌ | Optional: Notifications |

---

## Troubleshooting

### Database Connection Issues
```bash
# Verify DATABASE_URL is set correctly
# Should be: postgresql://user:pass@host:5432/dbname
```

### Build Failures
Check that all required files exist:
```
✅ Dockerfile
✅ backend/requirements.txt
✅ backend/main.py
✅ frontend/package.json
✅ alembic/
```

### API Not Working
1. Check `/health` endpoint
2. Verify CORS is allowing your domain
3. Check Railway/Render logs for errors

---

## Post-Deployment Checklist

- [ ] Verify health check passes (`/health`)
- [ ] Test login with admin credentials
- [ ] Change admin password
- [ ] Create a test project
- [ ] Verify API documentation loads (`/docs`)
- [ ] Set up custom domain (optional)
- [ ] Configure SSL/HTTPS (usually automatic)

---

## Support

Repository: https://github.com/nickgallick/ai-dev-agency
