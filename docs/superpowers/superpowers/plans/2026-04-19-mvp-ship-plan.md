# DELIRIUM.AI MVP Ship — Implementation Plan

**Date:** 2026-04-19
**Spec:** docs/superpowers/specs/2026-04-19-mvp-ship-design.md
**Target:** Ship to 10 real users within 2 weeks

---

## Phase 1: Frontend + Deployment (Days 1-3)

### Step 1.1: PWA Chat Frontend
**Method:** Manual (design decisions, visual)
**Files:** `static/index.html`, `static/manifest.json`, `static/sw.js`
- Single HTML file with embedded CSS + JS
- WebSocket connection to /ws
- Chat bubble UI (user right, Delirium left)
- Token streaming display
- H indicator (mood bar)
- Auto-reconnect, mobile-responsive
- PWA manifest + service worker

### Step 1.2: Docker Compose
**Method:** Manual
**Files:** `Dockerfile`, `docker-compose.yml`, `Caddyfile`
- Delirium API (FastAPI + uvicorn)
- Honcho (API + deriver + PostgreSQL + Redis)
- Caddy reverse proxy (auto-HTTPS)
- .env.example with all required vars
- Health check on all services

### Step 1.3: Scaleway Deploy
**Method:** Manual
- DEV1-S instance (Paris, €7.50/month)
- Domain pointing + Caddy HTTPS
- `docker compose up -d`
- Verify /health + /chat + /ws

---

## Phase 2: Cold Weaver Activation (Day 2)

### Step 2.1: Cold Weaver Scan
**Method:** CORAL (5 agents, behavioral grader)
**Grader:** Custom — runs scan on 1419 real fragments, checks:
- C1: scan() produces collision candidates (>0)
- C2: collision_score() in expected range [0.3, 0.7]
- C3: collision stored in DB
- C4: pending collision retrieved for S1 injection
- C5: S1 prompt includes collision context
- C6: "rien à voir mais..." appears in response
- Score = criteria_met / 6

---

## Phase 3: Auth + RGPD (Days 3-4)

### Step 3.1: Simple Auth
**Method:** CORAL (5 agents, behavioral grader)
**Grader:** Custom — checks:
- C1: /auth/login endpoint exists
- C2: token returned on valid login
- C3: /ws rejects unauthenticated
- C4: /chat requires token
- C5: users table exists in SQLite
- Score = criteria_met / 5

### Step 3.2: RGPD Compliance
**Method:** CORAL (5 agents, behavioral grader)
**Grader:** Custom — checks:
- C1: /export returns JSON with all user data
- C2: /delete purges all user data
- C3: first message includes disclaimer (not therapist)
- C4: consent recorded before first conversation
- Score = criteria_met / 4

---

## Phase 4: Polish + Ship (Days 5-7)

### Step 4.1: Onboarding (Simplified)
**Method:** Manual
- No OSINT. Simple structured first conversation.
- Delirium asks 3 questions: name, what brings you here, one interest
- Builds initial persona from answers
- No form — conversational onboarding

### Step 4.2: Live Testing
- Deploy to Scaleway
- Test all 12 behavioral criteria live
- Test Cold Weaver collision delivery
- Test auth + RGPD export/delete
- Fix bugs

### Step 4.3: Ship
- Send URL to 10 real users
- Instrument basic analytics (conversation count per user per day)
- Monitor /health

---

## Execution Order

| Day | Task | Method | Parallel? |
|-----|------|--------|-----------|
| 1 | Frontend PWA | Manual | — |
| 1 | Cold Weaver CORAL task | CORAL | Yes (background) |
| 2 | Docker Compose + Caddyfile | Manual | — |
| 2 | Auth CORAL task | CORAL | Yes (background) |
| 3 | Scaleway deploy | Manual | — |
| 3 | RGPD CORAL task | CORAL | Yes (background) |
| 4 | Merge CORAL results | Manual | — |
| 5 | Onboarding conversation flow | Manual | — |
| 6 | Live testing + bug fixes | Manual | — |
| 7 | Ship to 10 users | — | — |
