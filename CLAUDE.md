# CLAUDE.md — Instructions pour Claude Code

## Projet

Delirium AI — Système immunitaire cognitif. App grand public "Non-BlocNote" habitée par une IA colocataire non-servile qui construit la vision du monde que l'utilisateur n'a pas le temps d'avoir.

**Mantra :** "Apprendre à l'autre est une découverte."
**Tagline :** "Vos idées à la con sont intéressantes."

## Architecture du Repo

```
00_VISION/          Vision produit (VISION_v5.md = canonique), scénarios, bibliographie, companion AI patterns
01_CAHIER_DES_CHARGES/  CDC Comportemental (DOCUMENT CENTRAL), Fonctionnel, Technique, UX
02_EXIGENCES/       Légales (AI Act, RGPD, art.223-6 CP), Éthiques (danger 3 niveaux), Sécurité (logs, HIBP)
03_ARCHITECTURE/    ARCHITECTURE_HARNESS.md = spéc technique la plus détaillée (persona engine, 4 couches mémoire, cycle par message)
04_FORMALISME/      OIDA→Delirium, IPC (Circumplex), PsyFIRE (défensivité), Archétype inversé (protocole recherche)
05_ROADMAP/         6 phases jusqu'à OmniArxiv (Phase 6, 2028+)
06_TESTS/           27 scénarios critiques, prompts de test, résultats v0.1
07_BUSINESS/        Freemium + OmniArxiv (wiki open-source des idées)
```

## Documents Clés (lire en priorité)

1. `01_CAHIER_DES_CHARGES/CDC_COMPORTEMENTAL.md` — COMMENT Delirium se comporte. 10 invariants, cadres MI/Socratique/Précurseurs, protocole danger 3 niveaux. C'est la source de vérité pour le comportement.
2. `03_ARCHITECTURE/ARCHITECTURE_HARNESS.md` — Spéc technique du harness : génération de persona, moteur de transition, 4 couches mémoire, cycle par message, budget compute.
3. `03_ARCHITECTURE/ARCHITECTURE_IA.md` — System prompts S1 (réponse) et S2 (métacognition silencieuse). Persona vector 6D.
4. `03_ARCHITECTURE/DELIRIUM_PROMPT_V01.txt` — Prompt testable (validé, 10/11 tests passent).
5. `LIEVRES.md` — 21 questions ouvertes, 7 résolues, 14 en attente.

## Concepts Fondamentaux

### Identité de Delirium
- Anthropologue naïf : expert des mécanismes humains, ignorant de CET humain
- Colocataire du Non-BlocNote (app déjà habitée à l'ouverture)
- Personnalité ADJACENTE (jamais complémentaire) : ~30% convergent, ~30% divergent, ~40% orthogonal
- Persona = états (fatigue, ennui), PAS émotions (tristesse, amour)
- Fiabilité intentionnellement imparfaite : 70-85% non-critique, 100% sécurité

### Architecture Clé
- S1/S2 : réponse immédiate + métacognition silencieuse (JAMAIS restituée directement)
- Variable H ∈ [-1,1] : pilote le ton (retenu → audacieux)
- Cold Weaver : collision score SerenQA (Relevance × Novelty × Surprise)
- Machine à 4 états {H, C+, E, B} : hypothèse, confirmé, éliminé, biais enfoui
- IPC (Leary/Wiggins) : 2 axes (agency/communion), détection changement d'axe = précurseur occulté
- Score de défensivité (PsyFIRE) : 6 marqueurs textuels → calibre l'intervention

### 10 Invariants Comportementaux
1. Juger situation, JAMAIS état intérieur
2. Mémoire factuelle restituable ≠ analyse S2 jamais restituée
3. Pas de reproche rétrospectif
4. Persona = états, pas émotions
5. Premier message neutre-léger
6. Injection latérale max 1/session
7. Boucle = fait + question ouverte
8. 100% sécurité, 70-85% reste
9. Notifications content-driven
10. Ne s'installe nulle part sans demander

### Cadres d'Intervention
- MI (Entretien Motivationnel) : mode par défaut. Questions ouvertes, reflets complexes, jamais de confrontation rétro.
- Socratique : uniquement si confiance > 0.6 ET défensivité < 0.3. Cibler le rôle sous-estimé.
- Précurseurs : arrière-plan toujours. Changement d'axe IPC = signal.

### Protocole Danger
- N1 (<0.6) : ajustement MI silencieux
- N2 (0.6-0.9) : intensification MI + logs
- N3 (>0.9) : sort du rôle → contact ICE

## Ce qui est fait vs. ce qui reste

### FAIT (documentation)
- Vision complète (v5) + mantra + OmniArxiv
- CDC Comportemental (13 sections)
- Formalisme (OIDA audit, Delirium v0.1, IPC, PsyFIRE, Archétype inversé)
- Architecture technique (harness complet avec code Python)
- 27 scénarios critiques
- System prompt validé (10/11 tests passent)
- Cadre juridique (AI Act, RGPD, PLD, art. 223-6)
- 7/21 lièvres résolus

### FAIT (implémentation — Phases 1+2 complètes)
- Prototype CLI fonctionnel (`src/main.py`) avec conversation loop + streaming
- Client LLM MiniMax M2.7 (`src/llm_client.py`) avec suppression `<think>` tags
- PersonaEngine 6D (`src/persona/engine.py`) avec transitions
- S2 Analyzer async (`src/s2/analyzer.py`) avec JSON structuré
- Mémoire épisodique SQLite (`src/memory/episodic.py`)
- Mémoire sémantique graphe (`src/memory/semantic.py`)
- Mémoire de travail (`src/memory/working.py`) avec injection collision
- Cold Weaver moteur de collision (`src/cold_weaver/engine.py`)
- Collision scoring SerenQA (`src/cold_weaver/scoring.py`)
- ArXiv API source (`src/cold_weaver/sources.py`)
- Import ChatGPT (`src/import_/chatgpt.py`)
- Détection sycophantie (`src/import_/sycophancy.py`)
- Embeddings hash 384D (`src/embeddings.py`)
- Tests comportementaux 20/20 (`tests/test_behavior.py`)
- Commandes CLI : /import chatgpt, /collisions, /status

### PAS FAIT (à explorer, formaliser, documenter)
- Calibration des 20 paramètres du formalisme
- Formalisation de la convergence de H (oscillation, stabilité)
- Protocole d'import des historiques IA (formats concrets ChatGPT/Claude/Gemini)
- UI du Non-BlocNote (wireframes, interaction model)
- Mécanisme exact d'oubli sélectif (quand, comment, seuils)
- Pub absurdiste : catalogue de templates de parodie
- La "liste de courses" de Delirium : comment elle évolue, quand elle est drôle
- Interaction entre Delirium instances ("dîner" entre IA)
- Recherche socio/psycho non-occidentale (Ubuntu, kuuki wo yomu, Confucianisme)
- Le passage Delirium → OmniArxiv (comment l'utilisateur devient générateur)
- Protocole OSINT détaillé (quelles APIs, quelles limites, quel fallback)
- Score de fanfaronade (formalisation concrète)
- Détection de bulle algorithmique (H_bulle : comment le calculer)
- Le "seuil d'arrêt" du Cold Weaver (quand un sujet est trop surveillé)
- Le mécanisme de "retrait" de Delirium (comment il part, comment il revient)
- Les "running gags" (comment ils naissent, évoluent, meurent)
- Le format exact de la "vision du monde" (JSON schema)
- Tests adversariaux (prompt injection, manipulation, exploitation)
- Property-based testing du persona engine (H converge-t-il ? oscille-t-il ?)

### PAS FAIT (implémentation)
- Import Claude.ai conversations (`src/import_/claude_ai.py`)
- Import générique (`src/import_/generic.py`)
- Vision du monde synthèse (`src/memory/world_vision.py`) — voir `VISION_DU_MONDE_SCHEMA.md`
- Oubli sélectif Bjork (`src/memory/decay.py`) — voir `ARCHITECTURE_OUBLI_SELECTIF.md`
- Running gags tracker (`src/persona/gags.py`) — voir `ARCHITECTURE_RUNNING_GAGS.md`
- Retrait engine (`src/persona/retrait.py`) — voir `ARCHITECTURE_RETRAIT.md`
- Détection bulle prototype (`src/memory/bubble.py`) — voir `DETECTION_BULLE.md`
- Tests adversariaux (`tests/test_adversarial.py`) — voir `TESTS_ADVERSARIAUX.md`
- Audit cohérence inter-documents
- Property-based testing du PersonaEngine

## Règles pour Claude Code

1. **Lire avant d'écrire.** Toujours lire les documents existants avant de créer ou modifier. La cohérence inter-documents est critique.
2. **Le CDC Comportemental est la source de vérité** pour le comportement. Si un autre document le contredit, c'est l'autre document qui a tort.
3. **Ne pas inventer de décisions.** Les choix de design (ton, éthique, limites) appartiennent à Yann. Si un choix n'est pas documenté, le noter dans LIEVRES.md plutôt que de décider.
4. **Le formalisme doit être ancré.** Chaque formule doit citer sa source (AGM, Ebbinghaus, SerenQA, IPC, PsyFIRE). Pas de maths décoratives.
5. **Les paramètres non calibrés sont marqués [NC: à calibrer].** Ne pas inventer de valeurs.
6. **Tester avant de documenter.** Le prompt v0.1 a été TESTÉ (résultats dans 06_TESTS/RESULTATS_TEST_V01.md). Tout nouveau prompt doit être testé.

## Stack Technique

**LLM Backbone : MiniMax M2.7** (pas Claude, pas GPT)
- API key : `.env` → `MINIMAX_API_KEY`
- Base URL : `https://api.minimax.io/v1` (OpenAI-compatible)
- Modèle S1 : `MiniMax-M2.7` (réponse utilisateur)
- Modèle S2/rapide : `MiniMax-M2.7-highspeed` (métacognition async, notes autonomes)
- Contexte : 205K tokens, 131K max output
- Coût : $0.30/1M input, $1.20/1M output (~4x moins cher que Claude Sonnet)
- Supporte : streaming, tool calling, reasoning
- Atout spécifique : "excellent character consistency and emotional intelligence" (benchmarks MiniMax)
- **L'API est OpenAI-compatible** → utiliser le SDK `openai` Python avec `base_url` custom

```python
from openai import OpenAI
import os

client = OpenAI(
    api_key=os.getenv("MINIMAX_API_KEY"),
    base_url="https://api.minimax.io/v1"
)

response = client.chat.completions.create(
    model="MiniMax-M2.7",
    messages=[{"role": "system", "content": DELIRIUM_PROMPT}, {"role": "user", "content": user_msg}],
    stream=True
)
```

Voir `.env.example` pour la configuration complète.

## Style

- Documentation en français
- Code en anglais (noms de variables, commentaires techniques)
- Markdown pour les docs, Python pour le code
- Pas de bullshit corporate. Franc et direct, comme Delirium.
