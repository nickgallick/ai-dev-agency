# AI Dev Agency - Access Guide

## 🌐 Preview URLs

Access the application using these public preview URLs:

| Service | URL |
|---------|-----|
| **Frontend Dashboard** | https://2c64d7fe0-5173.preview.abacusai.app |
| **Backend API** | https://2c64d7fe0-8000.preview.abacusai.app |
| **API Documentation** | https://2c64d7fe0-8000.preview.abacusai.app/docs |

## ✅ Service Status

Both services are currently running:
- ✅ Backend API (FastAPI) - Port 8000
- ✅ Frontend (React/Vite) - Port 5173  
- ✅ PostgreSQL Database - Port 5432

## 🎯 What You Can Do

### Dashboard Features
- **Create Projects**: Start new AI-generated web projects
- **View Project Status**: Track progress of running projects
- **Agent Logs**: View detailed logs from each AI agent
- **Cost Tracking**: Monitor API usage costs

### API Endpoints
- `GET /health` - Health check
- `GET /api/projects` - List all projects
- `POST /api/projects` - Create new project
- `GET /api/projects/{id}` - Get project details
- `GET /api/agents/logs` - View agent execution logs
- `GET /api/costs` - View cost breakdown

## 🔑 Configuration

The following API keys are configured (check `.env` for values):
- `OPENROUTER_API_KEY` - For LLM interactions
- `GITHUB_TOKEN` - For code delivery
- `TAVILY_API_KEY` - For research tools
- `VERCEL_V0_API_KEY` - For code generation

## 🔧 Troubleshooting

### If services stop:
```bash
# Restart backend
cd /home/ubuntu/ai-dev-agency/backend
nohup uvicorn main:app --host 0.0.0.0 --port 8000 --reload &

# Restart frontend
cd /home/ubuntu/ai-dev-agency/frontend
npx vite --host 0.0.0.0 --port 5173 &

# Start PostgreSQL (if stopped)
sudo pg_ctlcluster 15 main start
```

### Check logs:
```bash
tail -f /tmp/backend.log   # Backend logs
tail -f /tmp/frontend.log  # Frontend logs
```

## ⚠️ Important Notes

- These preview URLs are temporary and tied to the VM lifecycle
- The VM will shut down after a period of inactivity
- For persistent deployment, deploy to your own infrastructure

---
*Generated: March 10, 2026*
