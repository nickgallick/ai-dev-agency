# API Requirements for AI Dev Agency

This document lists all API keys and credentials needed to run the AI Dev Agency system.

---

## 🔴 Required APIs (Phase 1)

These APIs are **mandatory** - the system will not function without them.

---

### 1. OpenRouter API Key

**What it's used for:**
- Powers ALL AI agents in the system (Intake, Research, Architect, Design System, CodeGen, Delivery)
- Routes requests to various LLM providers (Claude, GPT, DeepSeek, etc.)
- Single API key provides access to 100+ AI models

**How to obtain:**
1. Go to [OpenRouter.ai](https://openrouter.ai/)
2. Click "Sign In" (top right) → Sign up with Google/GitHub/Email
3. Navigate to [API Keys](https://openrouter.ai/keys)
4. Click "Create Key"
5. Name it "AI Dev Agency" and copy the key (starts with `sk-or-`)

**Permissions needed:**
- No special permissions required - standard API key works

**Pricing:**
- Pay-as-you-go based on tokens used
- Claude Sonnet 4: ~$3/$15 per 1M tokens (input/output)
- Claude Opus: ~$15/$75 per 1M tokens
- DeepSeek V3: ~$0.14/$0.28 per 1M tokens (budget option)
- **Estimated cost per simple website:** $1-10 depending on complexity

**Environment variable:**
```bash
OPENROUTER_API_KEY=sk-or-your-key-here
```

---

### 2. Vercel v0 API Key

**What it's used for:**
- Code Generation Agent uses v0 to generate React/Next.js components
- Creates production-ready UI code from design specifications
- Handles frontend code generation for web projects

**How to obtain:**
1. Go to [v0.dev](https://v0.dev/)
2. Sign in with your Vercel account (or create one)
3. Navigate to Settings → API
4. Generate a new API key
5. Copy the key

**Permissions needed:**
- Standard v0 API access
- May require v0 Pro subscription for higher rate limits

**Pricing:**
- v0 has a free tier with limited generations
- Pro plan: ~$20/month for higher limits
- API pricing may vary - check v0.dev for current rates

**Environment variable:**
```bash
VERCEL_V0_API_KEY=your-v0-api-key
```

---

### 3. GitHub Personal Access Token

**What it's used for:**
- Delivery Agent creates GitHub repositories for completed projects
- Pushes generated code to repos
- Manages project versioning and branches
- Required for code delivery and deployment workflows

**How to obtain:**
1. Go to [GitHub Settings → Developer Settings](https://github.com/settings/tokens)
2. Click "Personal access tokens" → "Tokens (classic)"
3. Click "Generate new token" → "Generate new token (classic)"
4. Set expiration (recommend 90 days or no expiration)
5. Name it "AI Dev Agency"
6. Select these scopes:
   - ✅ `repo` (Full control of private repositories)
   - ✅ `workflow` (Update GitHub Action workflows)
   - ✅ `write:packages` (Optional - for package publishing)
7. Click "Generate token" and copy it (starts with `ghp_`)

**Permissions needed:**
- `repo` - Create and push to repositories
- `workflow` - Set up CI/CD pipelines
- `delete_repo` - Optional, for cleanup

**Pricing:**
- FREE - GitHub tokens are free
- GitHub Actions minutes are free for public repos, limited for private

**Environment variable:**
```bash
GITHUB_TOKEN=ghp_your-github-token-here
```

---

## 🟡 Optional APIs (Enhanced Functionality)

These APIs add extra features but the system works without them.

---

### 4. Vercel Token (Deployment)

**What it's used for:**
- Auto-deploy Next.js/React projects to Vercel
- Provides live preview URLs

**How to obtain:**
1. Go to [Vercel Dashboard](https://vercel.com/account/tokens)
2. Click "Create Token"
3. Name it and set scope ("Full Account" or specific team)
4. Copy the token

**Environment variable:**
```bash
VERCEL_TOKEN=your-vercel-token
```

---

### 5. Railway Token (Backend Deployment)

**What it's used for:**
- Deploy backend services (APIs, databases)
- Alternative to Vercel for non-frontend deployments

**How to obtain:**
1. Go to [Railway Dashboard](https://railway.app/account/tokens)
2. Create new token
3. Copy the token

**Environment variable:**
```bash
RAILWAY_TOKEN=your-railway-token
```

---

### 6. Sentry DSN (Error Monitoring)

**What it's used for:**
- Track errors in deployed projects
- Analytics & Monitoring Agent setup

**How to obtain:**
1. Go to [Sentry.io](https://sentry.io/)
2. Create a project
3. Copy the DSN from project settings

**Environment variable:**
```bash
SENTRY_DSN=your-sentry-dsn
```

---

### 7. Slack Webhook URL (Notifications)

**What it's used for:**
- Send project completion notifications
- Alert on build failures

**How to obtain:**
1. Go to [Slack API](https://api.slack.com/apps)
2. Create an app → Incoming Webhooks
3. Add to channel and copy webhook URL

**Environment variable:**
```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
```

---

## 🗄️ Database Configuration

PostgreSQL is handled automatically by Docker Compose.

**Default Configuration (no changes needed):**
```bash
DATABASE_URL=postgresql://postgres:postgres@db:5432/ai_dev_agency
```

**If running PostgreSQL separately:**
- Host: Your PostgreSQL host
- Port: 5432 (default)
- Database: `ai_dev_agency`
- User: Your username
- Password: Your password

**Format:**
```bash
DATABASE_URL=postgresql://USERNAME:PASSWORD@HOST:PORT/DATABASE_NAME
```

---

## 🔐 Security Configuration

### SECRET_KEY

**What it's used for:**
- Encrypting sensitive data stored in database
- Session security
- JWT token signing (if used)

**How to generate:**

**Option 1 - Python:**
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Option 2 - OpenSSL:**
```bash
openssl rand -base64 32
```

**Option 3 - Using /dev/urandom:**
```bash
head -c 32 /dev/urandom | base64
```

**Environment variable:**
```bash
SECRET_KEY=your-generated-secret-key
```

⚠️ **Important:** Keep this secret! If compromised, regenerate and update.

---

## ✅ Quick Setup Checklist

### Step 1: Get Required API Keys

- [ ] **OpenRouter API Key**
  - Sign up at [openrouter.ai](https://openrouter.ai/)
  - Create API key at [openrouter.ai/keys](https://openrouter.ai/keys)
  - Add $10-20 credits to start

- [ ] **Vercel v0 API Key**
  - Sign in at [v0.dev](https://v0.dev/)
  - Generate API key in settings

- [ ] **GitHub Personal Access Token**
  - Go to [github.com/settings/tokens](https://github.com/settings/tokens)
  - Generate classic token with `repo` and `workflow` scopes

### Step 2: Generate Secret Key

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Step 3: Create .env File

```bash
cd /home/ubuntu/ai-dev-agency
cp .env.example .env
```

Edit `.env` and fill in your keys:

```bash
# Required
OPENROUTER_API_KEY=sk-or-your-key
VERCEL_V0_API_KEY=your-v0-key
GITHUB_TOKEN=ghp_your-token
SECRET_KEY=your-generated-secret

# Optional (add as needed)
VERCEL_TOKEN=your-vercel-token
RAILWAY_TOKEN=your-railway-token
SLACK_WEBHOOK_URL=your-webhook-url
```

### Step 4: Verify Configuration

Start the system:
```bash
docker-compose up -d
```

Check services are running:
```bash
docker-compose ps
```

Test API health:
```bash
curl http://localhost:8000/health
```

Test OpenRouter connection:
```bash
curl http://localhost:8000/api/test/openrouter
```

### Step 5: Access Dashboard

Open browser to: http://localhost:5173

---

## 💰 Estimated Costs

| Service | Cost Model | Estimated Monthly Cost |
|---------|------------|------------------------|
| OpenRouter | Pay per token | $10-100+ based on usage |
| v0.dev | Subscription | Free tier or ~$20/month |
| GitHub | Free | $0 |
| Vercel | Free tier available | $0-20/month |
| Railway | Usage based | $5-20/month |
| PostgreSQL (Docker) | Self-hosted | $0 |

**Per Project Estimates:**
- Simple landing page: $1-3
- Multi-page website: $5-10
- Full web application: $10-30

---

## 🔧 Troubleshooting

### "Invalid API Key" errors
- Double-check key is copied correctly (no extra spaces)
- Verify key hasn't expired (GitHub tokens)
- Check API key has sufficient permissions

### OpenRouter rate limits
- Add billing/credits to your account
- Consider using budget cost profile for testing

### GitHub push failures
- Verify token has `repo` scope
- Check token hasn't expired
- Ensure you have write access to the organization (if applicable)

---

## 📚 Quick Reference

| Variable | Required | Format | Where to Get |
|----------|----------|--------|---------------|
| `OPENROUTER_API_KEY` | ✅ Yes | `sk-or-...` | openrouter.ai/keys |
| `VERCEL_V0_API_KEY` | ✅ Yes | string | v0.dev settings |
| `GITHUB_TOKEN` | ✅ Yes | `ghp_...` | github.com/settings/tokens |
| `SECRET_KEY` | ✅ Yes | base64 string | Generate locally |
| `DATABASE_URL` | Auto | postgresql://... | Docker handles this |
| `VERCEL_TOKEN` | ❌ No | string | vercel.com/account/tokens |
| `RAILWAY_TOKEN` | ❌ No | string | railway.app/account/tokens |
| `SENTRY_DSN` | ❌ No | URL | sentry.io project settings |
| `SLACK_WEBHOOK_URL` | ❌ No | URL | api.slack.com |
