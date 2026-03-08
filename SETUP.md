# NSU Transcript Audit — Environment Setup Guide

> Follow these steps exactly **in order**. Each section is self-contained.

---

## Prerequisites

| Tool | Min Version | Install |
|---|---|---|
| Node.js | 20+ | [nodejs.org](https://nodejs.org) |
| npm | 10+ | bundled with Node |
| Python | 3.11+ | [python.org](https://python.org) |
| Git | any | [git-scm.com](https://git-scm.com) |
| Supabase CLI | latest | `npm i -g supabase` |
| k6 | latest | [k6.io/docs/get-started/installation](https://k6.io/docs/get-started/installation/) |

---

## Step 1 — Clone the Repository

```bash
git clone https://github.com/<your-org>/nsu-transcript-audit.git
cd nsu-transcript-audit
```

---

## Step 2 — Supabase Project Setup

### 2.1 Create a Supabase project
1. Go to [supabase.com](https://supabase.com) → **New Project**
2. Choose a name, region closest to Bangladesh (Singapore), and a strong DB password
3. Note your **Project URL** and **anon public key** from **Settings → API**

### 2.2 Run the database migration
Option A — Supabase Dashboard (easiest):
1. Go to **SQL Editor** in your project dashboard
2. Paste the contents of [`supabase/migrations/001_initial.sql`](./supabase/migrations/001_initial.sql)
3. Click **Run**

Option B — Supabase CLI:
```bash
supabase login
supabase link --project-ref <your-project-ref>
supabase db push
```

### 2.3 Set up Google OAuth
1. Go to [console.cloud.google.com](https://console.cloud.google.com) → **APIs & Services → Credentials**
2. Create an **OAuth 2.0 Client ID** (Web Application)
3. Add Authorized redirect URIs:
   - `https://<your-project-ref>.supabase.co/auth/v1/callback`
   - `http://localhost:3000/auth/callback` (for local dev)
4. Copy the **Client ID** and **Client Secret**
5. In Supabase: go to **Authentication → Providers → Google**
6. Paste your Client ID and Secret → **Save**

### 2.4 Get a Google Vision API key
1. In Google Cloud Console → **Enable APIs → Cloud Vision API**
2. Go to **Credentials → + Create Credentials → API Key**
3. Restrict it to the **Cloud Vision API** for security

---

## Step 3 — Deploy the Edge Function

```bash
# Set the secrets on your Supabase project
supabase secrets set GOOGLE_VISION_API_KEY=<your-key>

# Deploy the function
supabase functions deploy process-transcript --no-verify-jwt=false
```

> [!TIP]
> To test the function locally before deploying: `supabase functions serve`

---

## Step 4 — Web App (Next.js on Vercel)

### 4.1 Local development

```bash
cd web

# Copy env file and fill in your values
cp .env.local.example .env.local
# Edit .env.local:
#   NEXT_PUBLIC_SUPABASE_URL=https://<ref>.supabase.co
#   NEXT_PUBLIC_SUPABASE_ANON_KEY=<anon-key>

npm install
npm run dev
# → Open http://localhost:3000
```

### 4.2 Deploy to Vercel
1. Go to [vercel.com](https://vercel.com) → **New Project → Import Git Repository**
2. Set **Root Directory** → `web`
3. Set environment variables:
   | Name | Value |
   |---|---|
   | `NEXT_PUBLIC_SUPABASE_URL` | your Supabase project URL |
   | `NEXT_PUBLIC_SUPABASE_ANON_KEY` | your Supabase anon key |
4. Click **Deploy**
5. Copy your production URL (e.g. `https://nsu-audit.vercel.app`)
6. Add it to Supabase → **Authentication → URL Configuration → Site URL**
7. Add `https://nsu-audit.vercel.app/auth/callback` to **Redirect URLs**

---

## Step 5 — Mobile App (Expo)

### 5.1 Install dependencies

```bash
cd mobile
npm install
```

### 5.2 Configure env

Create `mobile/.env`:
```
EXPO_PUBLIC_SUPABASE_URL=https://<ref>.supabase.co
EXPO_PUBLIC_SUPABASE_ANON_KEY=<anon-key>
```

### 5.3 Add mobile redirect URL to Supabase
In Supabase → **Authentication → URL Configuration → Redirect URLs**, add:
```
nsu-audit://
```

### 5.4 Run on device/emulator

```bash
# iOS (Mac only)
npx expo run:ios

# Android
npx expo run:android

# Expo Go (quickest, scan QR with Expo Go app)
npx expo start
```

---

## Step 6 — Python CLI

```bash
cd cli

# Create and activate a virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

Create `cli/.env` (or ensure root `.env` exists):
```
SUPABASE_URL=https://<ref>.supabase.co
SUPABASE_ANON_KEY=<anon-key>
```

### CLI usage

```bash
# From the cli/ directory
python main.py login                          # opens browser for Google OAuth
python main.py scan ../transcript.csv -p CSE  # scan a CSV transcript
python main.py scan ../transcript.pdf -p EEE  # scan a PDF (uses OCR)
python main.py history                        # list past scans
python main.py report <scan-uuid>             # show full JSON for a scan
```

---

## Step 7 — GitHub Actions CI/CD Setup

### 7.1 Add repository secrets
In your GitHub repo → **Settings → Secrets and variables → Actions → New repository secret**:

| Secret name | Value |
|---|---|
| `SUPABASE_URL` | your Supabase project URL |
| `SUPABASE_ANON_KEY` | your Supabase anon key |
| `SONAR_TOKEN` | from [sonarcloud.io](https://sonarcloud.io) → My Account → Security |
| `TEST_USER_JWT` | JWT from a dedicated test account (see §7.2) |

### 7.2 Create a test user JWT for load tests
```bash
# In Supabase SQL editor — create a test user and get their JWT
# Or use Supabase Dashboard → Authentication → Users → "Invite user" → sign in as them
# Then in browser DevTools console: supabase.auth.getSession()
```

### 7.3 Enable branch protection (recommended)
In GitHub → **Settings → Branches → Add rule for `main`**:
- ✅ Require status checks to pass: `lint-js`, `lint-python`, `audit-tests`
- ✅ Require pull request reviews before merging

---

## Step 8 — Run Load Test Locally (Optional)

```bash
# From repo root
k6 run \
  --env SUPABASE_URL=https://<ref>.supabase.co \
  --env SUPABASE_ANON_KEY=<anon-key> \
  --env TEST_USER_JWT=<test-user-jwt> \
  load-tests/scan_load.js
```

Expected output: 20 VUs running for 60s, p95 < 8s, error rate < 5%.

---

## Quick Reference: Environment Variables

| Variable | Used by | Description |
|---|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | web | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | web | Supabase anon key |
| `EXPO_PUBLIC_SUPABASE_URL` | mobile | Supabase project URL |
| `EXPO_PUBLIC_SUPABASE_ANON_KEY` | mobile | Supabase anon key |
| `SUPABASE_URL` | cli, k6 | Supabase project URL |
| `SUPABASE_ANON_KEY` | cli, k6 | Supabase anon key |
| `GOOGLE_VISION_API_KEY` | edge function | Google Vision OCR API key |
| `GOOGLE_CLIENT_ID` | Supabase config | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Supabase config | Google OAuth client secret |
| `SONAR_TOKEN` | GitHub Actions | SonarCloud analysis token |
| `TEST_USER_JWT` | k6 | JWT for dedicated load test account |
