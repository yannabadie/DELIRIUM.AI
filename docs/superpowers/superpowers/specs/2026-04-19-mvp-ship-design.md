# DELIRIUM.AI MVP Ship Design

**Date:** 2026-04-19
**Status:** Approved (autonomous brainstorming)
**Goal:** Ship to first 10 real users within 2 weeks

---

## 1. Scope — What Ships

### MVP v0.1 (must-have)

| Feature | Status | Effort |
|---------|--------|--------|
| PWA chat frontend (single HTML file + WS) | NOT DONE | 1 day |
| Docker Compose full stack | NOT DONE | 1 day |
| Deploy to Scaleway DEV1-S + Caddy HTTPS | NOT DONE | 0.5 day |
| Basic auth (magic link or simple token) | NOT DONE | 0.5 day |
| RGPD export (/export endpoint) | DONE (endpoint exists) | Verify |
| Cold Weaver first scan on 1419 real fragments | NOT DONE | CORAL task |
| Health monitoring | DONE (/health endpoint) | — |

### Cut from MVP

- TTS/STT (adds complexity, zero demand)
- OSINT onboarding (legal risk, Honcho builds profile organically)
- Invitation/viralité system (no users to invite yet)
- 4-level notification escalation (in-app only for now)
- Mobile app (PWA covers this)

---

## 2. Architecture

```
┌─────────────────────────────────────────┐
│  Caddy (reverse proxy, auto-HTTPS)      │
│  └── delirium.app → :8080               │
│  └── honcho.internal → :8000            │
├─────────────────────────────────────────┤
│  delirium-api (FastAPI + uvicorn)       │
│  ├── /chat (POST) — sync response      │
│  ├── /ws — WebSocket streaming          │
│  ├── /status — persona + bubble state   │
│  ├── /export — RGPD JSON dump           │
│  ├── /health — liveness check           │
│  └── / — serves static/index.html (PWA) │
├─────────────────────────────────────────┤
│  honcho-api + honcho-deriver            │
│  └── PostgreSQL + pgvector + Redis      │
├─────────────────────────────────────────┤
│  External: MiniMax M2.7 API             │
└─────────────────────────────────────────┘
```

### Data flow per message

1. User sends message via WebSocket
2. FastAPI receives → guardrails check (deterministic)
3. If guardrail matches → return deterministic response
4. Else → compose S1 prompt (persona + working memory + world vision + bubble + collision)
5. Call MiniMax M2.7 → stream tokens back via WebSocket
6. Store in SQLite episodic memory + push to Honcho (async, fail-safe)
7. Run S2 analysis async (metacognition)
8. Update persona state, decay, bubble score

---

## 3. Frontend — PWA Chat

Single `static/index.html` served by FastAPI.

**Requirements:**
- Chat bubble UI (user = right/yellow, Delirium = left/cyan)
- Text input + send button
- WebSocket connection to /ws
- Token-by-token streaming display
- Persona indicator (H level: retenu ↔ audacieux)
- Auto-reconnect on disconnect
- PWA manifest + service worker (offline shell)
- Mobile-responsive (flexbox, no framework)

**Design constraints:**
- No build step. No npm. No framework.
- ~200-300 lines total (HTML + CSS + JS)
- Served as static file by FastAPI

---

## 4. Docker Compose

```yaml
services:
  delirium:
    build: .
    ports: ["127.0.0.1:8080:8080"]
    env_file: .env
    depends_on: [postgres, redis]

  honcho-api:
    build: ./honcho
    ports: ["127.0.0.1:8000:8000"]
    env_file: ./honcho/.env
    depends_on: [postgres, redis]

  honcho-deriver:
    build: ./honcho
    entrypoint: [python, -m, src.deriver]
    env_file: ./honcho/.env
    depends_on: [postgres, redis]

  postgres:
    image: pgvector/pgvector:pg15
    volumes: [pgdata:/var/lib/postgresql/data]

  redis:
    image: redis:8.2
    volumes: [redis-data:/data]

  caddy:
    image: caddy:2
    ports: ["80:80", "443:443"]
    volumes: [./Caddyfile:/etc/caddy/Caddyfile, caddy-data:/data]
```

---

## 5. Auth — Minimal

For MVP: simple token-based auth.
- User visits site → enters email → receives magic link (or simple passcode)
- Token stored in localStorage, sent as Bearer header on WS upgrade
- No registration form. No password. No OAuth.
- Backend: simple SQLite table `users(id, email, token, created_at)`

---

## 6. Cold Weaver Activation

CORAL task to:
1. Run `ColdWeaverEngine.scan()` on the 1419 imported Claude fragments
2. Verify collisions are found and stored
3. Verify collision injection appears in S1 prompt
4. Test "rien à voir mais..." format in response

This validates the core differentiator end-to-end.

---

## 7. Deployment Steps

1. Buy Scaleway DEV1-S (Paris, €7.50/month)
2. Point domain to instance IP
3. `docker compose up -d` on the server
4. Caddy auto-provisions HTTPS via Let's Encrypt
5. Verify /health responds
6. Send URL to 10 test users

---

## 8. Success Criteria

- [ ] Chat works end-to-end (browser → WS → MiniMax → response)
- [ ] Delirium refuses service requests (recipes, translations, etc.)
- [ ] Delirium challenges sycophancy
- [ ] Crisis detection works
- [ ] Persona goûts are consistent (rugby, turque, céphalopodes)
- [ ] Memory persists across page refresh (same session)
- [ ] RGPD export downloads JSON
- [ ] PWA installable on mobile
- [ ] 10 real users can use it simultaneously

---

## 9. What CORAL Does vs Manual

| Task | Method | Why |
|------|--------|-----|
| Cold Weaver activation + tests | **CORAL** | Systematic iteration with behavioral grader |
| Frontend HTML/CSS/JS | **Manual** | Design decisions, visual iteration |
| Docker Compose + Caddyfile | **Manual** | Environment-specific, imperative |
| Scaleway deployment | **Manual** | Infrastructure |
| Auth implementation | **CORAL** | Pytest-testable code |
| MiniMax fallback testing | **CORAL** | Multi-scenario evaluation |

---

## 10. Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| MiniMax goes down or changes pricing | Test prompts against Mistral/DeepSeek as fallback |
| Honcho adds latency | SQLite episodic memory works standalone (degraded) |
| First users find Delirium annoying | Tune H variable, MI aggressiveness based on feedback |
| CNIL complaint | RGPD export ready, data deletion endpoint, no OSINT |
