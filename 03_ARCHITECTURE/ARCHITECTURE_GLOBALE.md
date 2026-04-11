# Architecture Globale — Delirium AI

**Version :** 1.0 | **Date :** 11 avril 2026

---

## 1. Vue d'Ensemble

```
┌─────────────────────────────────────────────────────────┐
│                    CLIENT (Mobile/Desktop)                │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐ │
│  │ UI/UX    │  │ Whisper  │  │ SQLite   │  │ Vector  │ │
│  │ Mono-    │  │ STT      │  │ + SQLCi- │  │ DB      │ │
│  │ bouton   │  │ Local    │  │ pher     │  │ Local   │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬────┘ │
│       │              │              │              │      │
│       └──────────────┴──────┬───────┴──────────────┘      │
│                             │                             │
│                    ┌────────┴────────┐                    │
│                    │  Orchestrateur  │                    │
│                    │  Local          │                    │
│                    └────────┬────────┘                    │
└─────────────────────────────┼────────────────────────────┘
                              │ TLS 1.3
                              ▼
┌─────────────────────────────────────────────────────────┐
│                    BACKEND (Cloud FR)                     │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │ API Gateway  │  │ Worker S2    │  │ Cold Weaver   │  │
│  │ (FastAPI)    │  │ (Async)      │  │ (CRON Worker) │  │
│  └──────┬───────┘  └──────┬───────┘  └───────┬───────┘  │
│         │                 │                   │          │
│         ▼                 ▼                   ▼          │
│  ┌──────────────────────────────────────────────────┐   │
│  │              LLM Router                           │   │
│  │  (Anthropic Claude API — tool-use, citations)     │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │ OSINT        │  │ Veille       │  │ Sync Cloud    │  │
│  │ Module       │  │ ArXiv/GitHub │  │ (E2E chiffré) │  │
│  └──────────────┘  └──────────────┘  └───────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## 2. Flux de Données Principaux

### 2.1 Flux Capture → S1

```
User parle → Whisper STT (local) → Transcript texte
  → Envoi au backend API Gateway
  → LLM Router (Claude, system prompt S1 + archétype)
  → Réponse S1 streamée → Affichée à l'utilisateur
  → Transcript + réponse stockés localement (SQLite)
  → Extraction embeddings → stockés dans VectorDB locale
```

### 2.2 Flux S2 (Asynchrone)

```
Après réponse S1 :
  → Worker S2 reçoit le transcript + contexte archétype
  → LLM Router (Claude, system prompt S2 métacognitif)
  → Analyse : pourquoi cette personne dit ça ?
  → Résultat S2 stocké dans le graphe local (pas affiché)
  → Nourrit le module Vision du Monde
  → Nourrit le Cold Weaver (priorités de veille ajustées)
```

### 2.3 Flux Cold Weaver (Batch)

```
CRON périodique (quotidien ou hebdomadaire) :
  1. Récupération flux ArXiv/GitHub/presse
  2. Embeddings des nouveaux contenus
  3. Calcul de distance sémantique vs. fragments utilisateur
  4. Détection de collisions (seuil configurable)
  5. Si collision détectée → notification push formatée
  6. Parallèlement : scan des historiques IA externes
     → Détection d'inspirations avortées (4 critères)
     → Résultats stockés dans le graphe
```

### 2.4 Flux Import Historiques IA

```
User connecte son compte ChatGPT/Claude/Gemini :
  → Export JSON/ZIP importé
  → Parser adapté par plateforme
  → Extraction des paires question/réponse
  → Détection inspirations avortées :
     a) Friction sémantique (distance embedding Q vs R)
     b) Récurrence latente (clustering cross-conversations)
     c) Abandon après résistance (pattern insistance → abandon)
     d) Surgissement non rebondi (concept IA ignoré)
  → Fragments qualifiés stockés dans VectorDB + graphe
```

---

## 3. Composants Critiques

| Composant | Technologie | Criticité | Fallback |
|---|---|---|---|
| STT | Whisper.cpp local | Haute | Saisie texte |
| LLM S1 | Claude API (Anthropic) | Haute | Cache local réponses types |
| LLM S2 | Claude API (Anthropic) | Moyenne | File d'attente, retry |
| VectorDB | ChromaDB/LanceDB | Haute | SQLite FTS5 en dégradé |
| Cold Weaver | Worker async | Basse (batch) | Report au prochain cycle |
| OSINT | APIs publiques | Basse (onboarding only) | Archétype basé interactions |
| Sync Cloud | Serveur FR E2E | Basse (optionnel) | Local-only |

---

## 4. Principes Architecturaux

1. **Local-first :** Les données vivent sur le device. Le cloud est un miroir optionnel.
2. **Offline-capable :** Capture et consultation fonctionnent sans connexion.
3. **Async-by-default :** Seul le S1 est synchrone. Tout le reste est batch ou event-driven.
4. **Privacy-by-design :** Embeddings non réversibles, chiffrement au repos, pas de logs de contenu côté serveur.
5. **Modular :** Chaque module (OSINT, Cold Weaver, Sync) est activable/désactivable indépendamment.
