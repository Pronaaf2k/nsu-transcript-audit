# TODO — NSU Transcript Audit Setup

> Pick up from here tomorrow. Do steps in order.

---

## 🔴 Step 1 — Create Accounts & Get Credentials

- [ ] Create a **Supabase** project at [supabase.com](https://supabase.com)
  - Region: **Singapore** (closest to BD)
  - Save: **Project URL** + **anon public key** (Settings → API)

- [ ] Get a **free Gemini API key** at [aistudio.google.com](https://aistudio.google.com) — **no credit card**
  - Sign in with any Google account → Get API key → Create API key
  - Save: **Gemini API Key**
  - ✅ This replaces Google Vision entirely (1,500 free requests/day)

- [ ] Set up **Google Cloud** at [console.cloud.google.com](https://console.cloud.google.com) — ***only for OAuth, not OCR***
  - [ ] Create **OAuth 2.0 Client ID** (Web Application type)
  - Save: **Client ID**, **Client Secret**

- [ ] Create a **Vercel** account at [vercel.com](https://vercel.com) (free tier is fine)

---

## 🟡 Step 2 — Configure Supabase Dashboard

- [ ] **Authentication → Providers → Google** → paste Client ID + Secret → Save
- [ ] **SQL Editor** → paste `supabase/migrations/001_initial.sql` → Run
- [ ] **Authentication → URL Configuration**
  - Site URL: `https://your-app.vercel.app`
  - Redirect URLs:
    - `https://your-app.vercel.app/auth/callback`
    - `http://localhost:3000/auth/callback`
    - `nsu-audit://`

---

## 🟡 Step 2.5 — Copy Audit Files into the API folder

The FastAPI server needs the real audit logic from CSE226Proj1.
Copy these files from `f:\Github\CSE226Proj1\` into `f:\Github\nsu-transcript-audit\api\audit_src\`:

```
audit_l1.py
audit_l2.py
audit_l3.py
style.py
program.md
```

```bash
# Quick copy command (Windows)
copy f:\Github\CSE226Proj1\audit_l1.py    f:\Github\nsu-transcript-audit\api\audit_src\
copy f:\Github\CSE226Proj1\audit_l2.py    f:\Github\nsu-transcript-audit\api\audit_src\
copy f:\Github\CSE226Proj1\audit_l3.py    f:\Github\nsu-transcript-audit\api\audit_src\
copy f:\Github\CSE226Proj1\style.py       f:\Github\nsu-transcript-audit\api\audit_src\
copy f:\Github\CSE226Proj1\program.md     f:\Github\nsu-transcript-audit\api\audit_src\
```

- [ ] All 5 files copied to `api/audit_src/`

---

## 🟡 Step 3 — Deploy the Edge Function

```bash
npm i -g supabase
supabase login
supabase link --project-ref <your-project-ref>
supabase secrets set GOOGLE_VISION_API_KEY=<your-vision-key>
supabase functions deploy process-transcript
```

> After Render is set up (Step 3.5), come back and also run:
> ```bash
> supabase secrets set AUDIT_API_URL=https://nsu-audit-api.onrender.com
> supabase secrets set AUDIT_API_KEY=<the-key-render-generated>
> ```

---

## 🟡 Step 3.5 — Deploy FastAPI Audit Server on Render

1. Push the repo to GitHub (if not already done)
2. Go to [render.com](https://render.com) → **New → Web Service**
3. Connect your GitHub repo
4. Render will auto-detect `render.yaml` — click **Apply**
5. After deploy, go to your service → **Environment** tab
6. Copy the auto-generated `AUDIT_API_KEY` value
7. Note the service URL (e.g. `https://nsu-audit-api.onrender.com`)
8. Test it:
   ```bash
   curl https://nsu-audit-api.onrender.com/health
   # Should return: {"status": "ok"}
   ```
9. Go back and set the two Supabase secrets (see Step 3 above)

- [ ] Service is live on Render
- [ ] `/health` returns `{"status": "ok"}`
- [ ] `AUDIT_API_URL` and `AUDIT_API_KEY` set in Supabase secrets

---

## 🟡 Step 4 — Run Web App Locally

```bash
cd web
copy .env.local.example .env.local
# Fill in .env.local with your Supabase URL + anon key
npm install
npm run dev
# → Open http://localhost:3000
```

- [ ] Confirm Google sign-in page loads
- [ ] Confirm sign-in works and redirects to `/dashboard`
- [ ] Confirm CSV upload + audit works

---

## 🟡 Step 5 — Deploy to Vercel

- [ ] Push repo to GitHub
- [ ] Vercel → New Project → import repo → Root Directory: `web`
- [ ] Add env vars: `NEXT_PUBLIC_SUPABASE_URL` + `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- [ ] Deploy → copy production URL
- [ ] Add production URL to Supabase redirect URLs

---

## 🔵 Step 6 — CLI (optional, do after web works)

```bash
cd cli
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -r requirements.txt

# Create cli/.env with SUPABASE_URL + SUPABASE_ANON_KEY
python main.py login
python main.py scan ../test_transcript.csv -p CSE
```

- [ ] Login works (browser opens)
- [ ] Scan returns audit result

---

## 🔵 Step 7 — Mobile (optional)

```bash
cd mobile
npm install
# Create mobile/.env with EXPO_PUBLIC_SUPABASE_URL + EXPO_PUBLIC_SUPABASE_ANON_KEY
npx expo start
```

- [ ] App loads on Expo Go
- [ ] Sign-in works
- [ ] Scan tab works

---

## 🔵 Step 8 — GitHub Actions & Load Test

- [ ] Add secrets in GitHub → Settings → Secrets:
  - `SUPABASE_URL`
  - `SUPABASE_ANON_KEY`
  - `SONAR_TOKEN` (from [sonarcloud.io](https://sonarcloud.io))
  - `TEST_USER_JWT` (JWT from a test Supabase account)
- [ ] Enable branch protection on `main`
- [ ] Run load test locally:
  ```bash
  k6 run load-tests/scan_load.js
  ```

---

## 📋 Credentials Cheat Sheet

Fill this in as you go:

| Item | Value |
|---|---|
| Supabase Project URL | |
| Supabase Anon Key | |
| Supabase Project Ref | |
| Google Client ID | |
| Google Client Secret | |
| Google Vision API Key | |
| Vercel Production URL | |
| Render Service URL | |
| Render AUDIT_API_KEY | |

