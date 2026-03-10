# Phase 10: Integrations

This document details the integration capabilities added in Phase 10 of the AI Dev Agency.

## Overview

Phase 10 introduces two categories of integrations:

1. **Agency System Integrations** - Used by agents during project generation
2. **Generated Project Defaults** - Auto-injected into generated SaaS projects

---

## Agency System Integrations

These integrations enhance the AI agents' capabilities during the build process.

### 1. Figma MCP Integration

**Purpose**: Extract design context directly from Figma design files.

**Used By**:
- Research Agent - Analyzes design structure and components
- Design System Agent - Extracts design tokens (colors, typography, spacing)
- Architect Agent - Uses layout information for accurate v0 prompts

**Features**:
- `get_design_context()` - Extract layout, hierarchy, and structure
- `get_screenshot()` - Capture visual screenshots of frames/components
- `get_variable_defs()` - Extract design tokens (colors, typography, spacing)

**How to Get API Key**:
1. Go to [Figma Developer Settings](https://www.figma.com/developers/api#access-tokens)
2. Click "Create a new personal access token"
3. Copy the token (starts with `figd_`)

**Environment Variable**:
```bash
FIGMA_ACCESS_TOKEN=figd_your-figma-personal-access-token
```

**Usage in Projects**:
- Add a Figma URL in the "Advanced Options" when creating a new project
- The agents will automatically extract design context

---

### 2. BrowserStack Integration

**Purpose**: Run cross-browser tests on real devices during QA.

**Used By**:
- QA Agent (optional upgrade from local Playwright)

**Supported Browsers**:
| Browser | Platform |
|---------|----------|
| Chrome | Windows 11 |
| Safari | macOS Sonoma |
| Firefox | Windows 11 |
| Edge | Windows 11 |
| Mobile Safari | iPhone 15 Pro (iOS 17) |
| Mobile Chrome | Samsung Galaxy S24 (Android 14) |

**How to Get Credentials**:
1. Sign up at [BrowserStack](https://www.browserstack.com/)
2. Go to [Account Settings](https://www.browserstack.com/accounts/settings)
3. Find your Username and Access Key

**Environment Variables**:
```bash
BROWSERSTACK_USERNAME=your-browserstack-username
BROWSERSTACK_ACCESS_KEY=your-browserstack-access-key
```

**Fallback Behavior**:
If BrowserStack is not configured, QA Agent falls back to local Playwright testing.

---

## Generated Project Defaults

These integrations are automatically added to generated projects when applicable.

### 3. Resend Email Integration

**Purpose**: Add email functionality to SaaS projects with authentication.

**Auto-Integrated For**:
- `web_complex` projects with authentication
- `python_saas` projects

**Generated Code**:
- `lib/email.ts` - Email sending utility
- `emails/*.tsx` - React Email templates (welcome, password reset, verification, invoice)
- `emails/index.ts` - Template exports

**How to Get API Key**:
1. Sign up at [Resend](https://resend.com/)
2. Go to [API Keys](https://resend.com/api-keys)
3. Create a new API key

**Environment Variable** (for generated project):
```bash
RESEND_API_KEY=re_your-resend-api-key
```

**NPM Packages Added**:
```json
{
  "resend": "^2.0.0",
  "@react-email/components": "^0.0.15",
  "react-email": "^2.0.0"
}
```

---

### 4. Cloudflare R2 Storage Integration

**Purpose**: Add file storage with presigned URLs for projects with file uploads.

**Auto-Integrated For**:
- `web_complex` projects with file upload features
- `python_saas` projects with file upload features

**Generated Code**:
- `lib/r2.ts` - R2 upload/download utility
- `lib/r2.types.ts` - TypeScript types
- `hooks/useFileUpload.ts` - React hook for uploads
- `app/api/upload/presigned/route.ts` - API endpoint for presigned URLs

**How to Get Credentials**:
1. Log in to [Cloudflare Dashboard](https://dash.cloudflare.com/)
2. Go to R2 Object Storage
3. Click "Manage R2 API Tokens"
4. Create a token with read/write permissions

**Environment Variables** (for generated project):
```bash
R2_ACCESS_KEY_ID=your-r2-access-key-id
R2_SECRET_ACCESS_KEY=your-r2-secret-access-key
R2_BUCKET_NAME=your-bucket-name
R2_ACCOUNT_ID=your-cloudflare-account-id
```

**NPM Packages Added**:
```json
{
  "@aws-sdk/client-s3": "^3.500.0",
  "@aws-sdk/s3-request-presigner": "^3.500.0"
}
```

---

### 5. Inngest Background Jobs Integration

**Purpose**: Add background job processing for SaaS projects with async tasks.

**Auto-Integrated For**:
- `python_saas` projects
- `web_complex` projects with async task requirements

**Generated Code**:
- `lib/inngest/client.ts` - Inngest client setup
- `lib/inngest/events.ts` - Event type definitions
- `lib/inngest/functions/*.ts` - Background job functions
- `lib/inngest/send.ts` - Event sending utility
- `app/api/inngest/route.ts` - Inngest API handler

**Default Background Jobs**:
| Job | Event | Description |
|-----|-------|-------------|
| sendWelcomeEmail | user/created | Send welcome email to new users |
| processPayment | payment/initiated | Process payment and update subscription |
| generateReport | report/requested | Generate and email reports asynchronously |
| syncData | sync/triggered | Sync data with external services |
| cleanupExpired | cron/daily | Clean up expired sessions and data |

**How to Get Event Key**:
1. Sign up at [Inngest](https://www.inngest.com/)
2. Go to [Manage Keys](https://app.inngest.com/env/production/manage/keys)
3. Copy the Event Key

**Environment Variables** (for generated project):
```bash
INNGEST_EVENT_KEY=your-inngest-event-key
INNGEST_SIGNING_KEY=optional-for-webhook-verification
```

**NPM Packages Added**:
```json
{
  "inngest": "^3.0.0"
}
```

---

## Configuration

### Via Environment Variables

Add the required variables to your `.env` file. See `.env.example` for the complete list.

### Via Settings Page

1. Navigate to Settings in the dashboard
2. Click on the "Integrations" tab
3. View status of all integrations (configured/not configured)
4. Click "Docs" links for each integration to get API keys

---

## API Endpoints

### Get Integration Status

```bash
GET /api/integrations/status
```

Returns status of all integrations:

```json
{
  "integrations": {
    "figma": {
      "name": "Figma MCP",
      "configured": true,
      "description": "Extract design context from Figma files",
      "category": "agency_system",
      "required_vars": ["FIGMA_ACCESS_TOKEN"]
    },
    ...
  },
  "agency_system_count": 2,
  "generated_project_count": 3,
  "total_configured": 5
}
```

### Test Figma Connection

```bash
POST /api/integrations/test/figma
Content-Type: application/json

{
  "figma_url": "https://www.figma.com/file/abc123/..."
}
```

### Test BrowserStack Connection

```bash
POST /api/integrations/test/browserstack
```

---

## Graceful Degradation

All integrations are optional and the system gracefully degrades:

| Integration | If Not Configured |
|-------------|-------------------|
| Figma MCP | Agents use brief and reference URLs only |
| BrowserStack | QA uses local Playwright |
| Resend | Email templates not generated |
| R2 | File upload code not generated |
| Inngest | Background jobs not generated |

---

## Architecture

```
backend/
├── integrations/
│   ├── __init__.py       # Package exports
│   ├── figma_mcp.py      # Figma MCP client
│   ├── browserstack.py   # BrowserStack API client
│   ├── resend.py         # Resend code generator
│   ├── cloudflare_r2.py  # R2 code generator
│   └── inngest.py        # Inngest code generator
├── config/
│   └── settings.py       # Integration settings
└── api/routes/
    └── integrations.py   # Integration API endpoints
```

---

## Future Enhancements

Planned for future phases:
- Stripe integration for payments
- Supabase auth integration
- PostHog analytics integration
- Linear issue tracking integration
