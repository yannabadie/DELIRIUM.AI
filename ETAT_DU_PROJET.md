# État du Projet — Delirium AI — 12 avril 2026

## Vue d'Ensemble

**Prototype :** CLI fonctionnel (Python, MiniMax M2.7, SQLite)
**Documentation :** ~20 documents d'architecture/formalisme, ~30 références académiques
**Tests :** 10/11 comportementaux passent, 20/20 unitaires
**Code :** 2242 lignes Python (src/ + tests/)

---

## Arborescence Complète

```
DELIRIUM.AI/
├── CLAUDE.md                          ★ Instructions Claude Code
├── LIEVRES.md                         ★ 21 questions ouvertes (8 résolues)
├── README.md
├── .env.example                       Configuration MiniMax M2.7
├── requirements.txt
│
├── 00_VISION/
│   ├── VISION_v5.md                   ★★ Document canonique
│   ├── COMPANION_AI_PATTERNS.md       8 patterns jeu → Delirium
│   ├── RESEARCH_BIBLIOGRAPHY.md       ~30 références (12 sections)
│   └── SCENARIOS_WHATIF.md
│
├── 01_CAHIER_DES_CHARGES/
│   ├── CDC_COMPORTEMENTAL.md          ★★★ SOURCE DE VÉRITÉ comportement
│   ├── CDC_FONCTIONNEL.md
│   ├── CDC_TECHNIQUE.md
│   ├── CDC_UX.md
│   └── DECISIONS_SESSION2_PM.md       3 décisions design (OmniArxiv, pub, instances)
│
├── 02_EXIGENCES/
│   ├── EXIGENCES_LEGALES.md           AI Act, RGPD, art.223-6
│   ├── EXIGENCES_ETHIQUES.md          Protocole danger 3 niveaux
│   └── EXIGENCES_SECURITE.md
│
├── 03_ARCHITECTURE/
│   ├── ARCHITECTURE_HARNESS.md        ★★ Pipeline complet (persona + mémoire + cycle)
│   ├── ARCHITECTURE_IA.md             Prompts S1/S2, persona vector
│   ├── ARCHITECTURE_COLD_WEAVER.md    Collision score, vie autonome
│   ├── ARCHITECTURE_OUBLI_SELECTIF.md ★★ Bjork SS/RS, 3 modes
│   ├── ARCHITECTURE_RETRAIT.md        4 états, escalade communication
│   ├── ARCHITECTURE_RUNNING_GAGS.md   Naissance/évolution/mort
│   ├── ARCHITECTURE_DONNEES.md        Schéma SQL + tables
│   ├── PROTOTYPE_SYSTEM_PROMPT.md     Prompt + 12 tests
│   └── DELIRIUM_PROMPT_V01.txt        ★ Prompt prêt à copier
│
├── 04_FORMALISME/
│   ├── FORMALISME_DELIRIUM_v0.1.md    Formalisme mathématique OIDA
│   ├── CIRCUMPLEX_INTERPERSONNEL.md   IPC (Leary/Wiggins) + IPCTracker
│   ├── DETECTION_DEFENSIVITE.md       PsyFIRE + 6 marqueurs
│   ├── DETECTION_BULLE.md             ★★ 6 signaux conversationnels (gap recherche)
│   ├── DETECTION_SYCOPHANTIE.md       ★★ ELEPHANT + face positive/négative
│   ├── SCORE_FANFARONADE.md           6 marqueurs (Gales 2015)
│   ├── ARCHETYPE_INVERSE_PROTOCOLE.md Protocole recherche N=100-200
│   └── AUDIT_FORMEL_OIDA_V42.md
│
├── 05_ROADMAP/
│   ├── ROADMAP.md                     6 phases → OmniArxiv (KPI autonomie intégrés)
│   └── MVP_SPEC.md
│
├── 06_TESTS/
│   ├── PROMPTS_TEST_V01.txt           12 prompts de test
│   ├── RESULTATS_TEST_V01.md          10/11 pass sur Claude Opus 4.6
│   └── SCENARIOS_CRITIQUES.md         27 scénarios
│
├── 07_BUSINESS/
│   ├── BUSINESS_MODEL.md              Freemium + OmniArxiv
│   └── KPI_AUTONOMIE.md              ★ Remplacement des KPI d'engagement
│
└── src/                               ★★ PROTOTYPE FONCTIONNEL
    ├── main.py                        CLI (conversation + /import + /collisions + /status)
    ├── llm_client.py                  MiniMax M2.7 (streaming, <think> suppression)
    ├── config.py                      .env loading
    ├── embeddings.py                  HashEmbedder 384D + SentenceTransformer opt.
    ├── memory/
    │   ├── episodic.py                SQLite + embeddings + collisions table
    │   ├── semantic.py                Graphe de connaissances
    │   └── working.py                 Composition prompt S1 + injection collision
    ├── persona/
    │   ├── engine.py                  PersonaEngine (transitions 6D)
    │   └── state.py                   PersonaState dataclass
    ├── s2/
    │   └── analyzer.py                S2 async (JSON structuré)
    ├── import_/
    │   ├── base.py                    Interface ImportedMessage
    │   ├── chatgpt.py                 Parse conversations.json
    │   └── sycophancy.py              Détection bilingue (heuristique + LLM)
    ├── cold_weaver/
    │   ├── engine.py                  Moteur de collision
    │   ├── scoring.py                 Relevance × Novelty × Surprise
    │   └── sources.py                 ArXiv API
    └── prompts/
        ├── s1_system.txt              System prompt validé
        └── s2_system.txt              System prompt S2
```

---

## Ce qui est PRÊT à tester

1. **Conversation avec Delirium** → `python -m src.main` (nécessite MINIMAX_API_KEY)
2. **Import ChatGPT** → `/import chatgpt ./conversations.json`
3. **Scan collisions** → `/collisions`
4. **État du système** → `/status`

## Ce qui MANQUE pour le test ultime

1. Une clé API MiniMax réelle dans `.env`
2. Un export ChatGPT réel (Settings → Data Controls → Export)
3. Lancer : import → collisions → conversation → voir si "rien à voir mais..." émerge

## Gaps Conceptuels Restants

| Gap | Priorité | Impact |
|---|---|---|
| Format JSON exact de la Vision du Monde | Haute | Nécessaire pour le S2 |
| Protocole OSINT (quelles APIs) | Basse (retiré du MVP) | Phase 2+ |
| Recherche non-occidentale (L20) | Moyenne | Phase 5 |
| Tests adversariaux | Haute | Sécurité |
| Convergence de H (math) | Basse | Académique |
| Import Claude/Gemini formats | Moyenne | Phase 2 |
