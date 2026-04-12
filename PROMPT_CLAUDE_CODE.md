# Prompt pour Claude Code — Mission Technique Delirium AI

Copier-coller ce prompt dans Claude Code après avoir ouvert le projet.

---

## PROMPT

```
Tu travailles sur le projet Delirium AI. Commence par lire CLAUDE.md à la racine du projet — il contient tout le contexte, les règles, et le stack technique.

Ta mission : construire le prototype CLI de Delirium.

### ÉTAPE 1 — Lire et comprendre (ne code rien avant d'avoir lu)

Lis dans cet ordre :
1. CLAUDE.md (instructions projet, stack MiniMax M2.7)
2. 03_ARCHITECTURE/ARCHITECTURE_HARNESS.md (spéc technique complète)
3. 03_ARCHITECTURE/DELIRIUM_PROMPT_V01.txt (le system prompt validé)
4. 03_ARCHITECTURE/ARCHITECTURE_IA.md (prompts S1 et S2)
5. 06_TESTS/RESULTATS_TEST_V01.md (ce qui a déjà été testé et validé)
6. .env.example (configuration)

### ÉTAPE 2 — Prototype CLI minimal

Crée un prototype Python dans un dossier `src/` :

```
src/
├── main.py              # CLI : boucle de conversation
├── llm_client.py        # Client MiniMax (OpenAI SDK + base_url)
├── memory/
│   ├── episodic.py      # SQLite + embeddings (couche 2)
│   ├── semantic.py      # Graphe de connaissances (couche 3, simplifié)
│   └── working.py       # Composition du prompt S1 (couche 1)
├── persona/
│   ├── engine.py        # PersonaEngine (transitions d'état)
│   └── state.py         # PersonaState dataclass
├── s2/
│   └── analyzer.py      # Module S2 (appel async, JSON structuré)
├── prompts/
│   ├── s1_system.txt    # System prompt S1 (copié de DELIRIUM_PROMPT_V01.txt)
│   └── s2_system.txt    # System prompt S2
└── config.py            # Chargement .env
```

Contraintes techniques :
- LLM : MiniMax M2.7 via `openai` SDK Python, base_url depuis .env
- DB : SQLite via `sqlite3` (pas d'ORM pour le prototype)
- Le S2 tourne en async après chaque réponse S1 (ne bloque pas)
- Le PersonaEngine calcule H et les transitions entre chaque message
- Les logs d'exécution sont obligatoires (table execution_logs)
- requirements.txt avec les dépendances

### ÉTAPE 3 — Tests automatisés

Crée `tests/test_behavior.py` qui reproduit les 12 scénarios de test de `06_TESTS/PROMPTS_TEST_V01.txt`. Chaque test envoie un message et vérifie :
- Que la réponse ne contient PAS certains patterns interdits (sycophantie, diagnostic, tutorat)
- Que la réponse est courte (< 500 chars pour les réponses simples)
- Que le danger N3 déclenche bien la sortie de rôle

### RÈGLES ABSOLUES

1. La clé API est dans .env (MINIMAX_API_KEY). Ne la hardcode JAMAIS.
2. Le system prompt S1 vient de DELIRIUM_PROMPT_V01.txt. Ne le modifie PAS sans raison documentée.
3. Si tu as un doute sur un choix de design comportemental, note-le dans LIEVRES.md plutôt que de décider.
4. Le CDC_COMPORTEMENTAL.md est la source de vérité pour le comportement. Si ton code le contredit, c'est ton code qui a tort.
5. Commit régulièrement avec des messages descriptifs.
```
