# Cahier des Charges Technique — Delirium AI

**Version :** 1.0
**Date :** 11 avril 2026

---

## 1. Stack Technique Cible

### 1.1 Client Mobile (MVP)
- **Framework :** React Native ou Flutter (à arbitrer — Flutter privilégié pour performance STT)
- **STT :** Whisper.cpp embarqué (modèle small ou medium selon device)
- **TTS :** Optionnel, moteur natif OS (iOS Speech / Android TTS)
- **Base locale :** SQLite (historique, métadonnées) + ChromaDB ou LanceDB (embeddings vectoriels)
- **Chiffrement local :** SQLCipher pour SQLite, chiffrement AES-256 pour le vault vectoriel

### 1.2 Client Desktop
- Application Electron ou Tauri (Tauri privilégié — plus léger, Rust-based)
- Mêmes composants que mobile + accès fichiers locaux

### 1.3 Backend
- **API Gateway :** FastAPI (Python) ou Axum (Rust) — selon compétences équipe
- **LLM :** Anthropic Claude API (S1 + S2) via tool-use pour le sourcing temps réel
- **Veille (Cold Weaver) :** Worker asynchrone — CRON ou event-driven
  - ArXiv API (bulk metadata + semantic scholar enrichment)
  - GitHub API (trending repos, new releases)
  - Flux RSS presse configurable
- **OSINT :** Module dédié, API légales uniquement (cf. EXIGENCES_LEGALES.md)
- **Cloud sync (optionnel) :** Serveur FR (Scaleway / OVH), API sync chiffrée E2E

### 1.4 Modèle de Données
Voir `03_ARCHITECTURE/ARCHITECTURE_DONNEES.md` pour le schéma détaillé.

---

## 2. Contraintes Techniques

### 2.1 Latence
- S1 (réponse immédiate) : < 3 secondes perçues (streaming token par token)
- S2 (métacognition) : asynchrone, pas de contrainte temps réel
- Cold Weaver : batch, exécution quotidienne ou hebdomadaire
- OSINT onboarding : < 30 secondes pour le premier archétype

### 2.2 Stockage Device
- Budget stockage cible : < 500 Mo sur device (embeddings + graphe + texte)
- Oubli sélectif obligatoire au-delà du seuil configurable
- Pas de stockage audio — transcription immédiate puis purge

### 2.3 Connectivité
- Mode offline complet pour la capture et le S1 (avec modèle LLM local de fallback si disponible)
- S2 et Cold Weaver nécessitent une connexion (API LLM + veille)
- Sync cloud nécessite connexion

### 2.4 Compatibilité API Export IA
- ChatGPT : export JSON via settings (manual) ou API conversations (si disponible)
- Claude : export via API conversations (à vérifier disponibilité 2026)
- Gemini : Google Takeout format
- Copilot : format Microsoft à déterminer
- **Risque :** ces APIs peuvent changer ou être restreintes — prévoir un mode import manuel (upload JSON/ZIP)

---

## 3. Dépendances Critiques

| Dépendance | Risque | Mitigation |
|---|---|---|
| Anthropic Claude API | Changement pricing/ToS | Abstraction LLM, fallback OpenAI/local |
| Whisper.cpp | Performance on-device | Modèle small par défaut, medium optionnel |
| ChromaDB/LanceDB | Stabilité, taille | Benchmark les deux, choisir au MVP |
| APIs export IA | Disponibilité, format | Import manuel en fallback |
| OSINT APIs | Légalité par juridiction | Module désactivable, transparent |

---

## 4. Environnements

| Env | Usage | Infra |
|---|---|---|
| DEV | Développement local | Machine dev + émulateurs |
| STAGING | Tests intégration | Cloud FR (Scaleway) |
| PROD | Production | Cloud FR + CDN pour assets statiques |

---

## 5. CI/CD

- Git (GitHub ou GitLab)
- Tests automatisés (cf. `06_TESTS/STRATEGIE_TESTS.md`)
- Build mobile : Fastlane (iOS) + Gradle (Android)
- Déploiement backend : Docker + orchestration légère (Docker Compose ou Nomad)
