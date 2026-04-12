# Prompt Claude Code — Phase 2 : Cold Weaver + Import IA

Tu travailles sur le projet Delirium AI. Relis CLAUDE.md si nécessaire.

Le prototype CLI (src/) est fonctionnel : conversation loop, LLM client MiniMax, PersonaEngine, S2 async, mémoire épisodique SQLite. Bien joué.

## TA MISSION MAINTENANT

Le moment magique de Delirium est la **collision** — quand le système connecte deux idées que l'utilisateur n'aurait pas rapprochées seul. C'est ÇA qu'il faut prouver. Pas le carnet, pas la persona, pas l'OSINT. La collision.

### ÉTAPE 1 — Import des historiques ChatGPT

Crée `src/import/` :

```
src/import/
├── chatgpt.py         # Parse le fichier conversations.json exporté de ChatGPT
├── base.py            # Interface commune pour tous les imports
└── sycophancy.py      # Détecteur de sycophantie dans les réponses IA importées
```

**chatgpt.py :**
- ChatGPT exporte en JSON (Settings → Data Controls → Export Data)
- Le fichier contient `conversations.json` avec structure :
  `[{title, create_time, mapping: {node_id: {message: {content: {parts: [...]}, role}}}}]`
- Extraire : chaque conversation → liste de (user_message, assistant_response)
- Stocker dans la mémoire épisodique avec source="chatgpt"
- Embedder les messages utilisateur (pas les réponses IA)

**sycophancy.py :**
- Pour chaque réponse IA importée, calculer un score de sycophantie [0,1]
- Marqueurs : "Great question!", "That's a really interesting idea", "Absolutely!", 
  "You're right", validation sans nuance, absence de contre-argument
- Utiliser un appel LLM (MiniMax-M2.7-highspeed) avec prompt :
  ```
  Score la sycophantie de cette réponse IA de 0 (challenge honnête) à 1 (validation molle).
  Répondre UNIQUEMENT avec un nombre décimal.
  ```
- Stocker le score dans les métadonnées du fragment

### ÉTAPE 2 — Cold Weaver (Moteur de Collision)

Crée `src/cold_weaver/` :

```
src/cold_weaver/
├── engine.py          # Moteur de collision principal
├── scoring.py         # Collision score (SerenQA-inspired)
└── sources.py         # Sources de veille (ArXiv API pour commencer)
```

**engine.py :**
- Prend TOUS les embeddings de la mémoire épisodique (conversations Delirium + imports)
- Cherche des paires de fragments qui sont :
  - Sémantiquement moyennement distants (cosine 0.3-0.7) — pas trop proches (trivial), pas trop loin (random)
  - De sources différentes (user_delirium + user_chatgpt, ou deux conversations Delirium espacées)
  - Jamais combinées auparavant (flag `collision_checked` dans la DB)
- Pour chaque paire candidate, calculer le collision score

**scoring.py :**
- Collision score = Relevance × Novelty × Surprise (inspiré SerenQA)
- Relevance : les deux fragments partagent un thème commun (cosine des thèmes > 0.5)
- Novelty : la combinaison n'a jamais été vue dans les conversations (pas de fragment existant à cosine > 0.8 de la combinaison)
- Surprise : la distance sémantique entre les deux est dans le sweet spot [0.3, 0.7]
- Score final ∈ [0, 1]. Seuil de restitution : > 0.6

**sources.py :**
- Pour le MVP : ArXiv API uniquement
- Requête : les 5 thèmes actifs les plus forts du graphe sémantique
- 1 appel/jour max
- Stocker les résultats comme fragments source="arxiv"

### ÉTAPE 3 — Restitution des Collisions

Dans `src/memory/working.py`, ajouter la capacité d'injecter une collision dans le prompt S1 :

```python
def compose_s1_prompt(self, ..., pending_collision=None):
    # ... existing code ...
    if pending_collision:
        sections.append(f"""
═══ COLLISION COLD WEAVER (injection latérale — max 1/session) ═══
Tu as trouvé une connexion entre deux idées de l'utilisateur :
- Idée A : {pending_collision['fragment_a_summary']}
- Idée B : {pending_collision['fragment_b_summary']}
- Connexion possible : {pending_collision['connection']}

Intègre ça dans la conversation de manière naturelle.
"Rien à voir mais..." est ton format. Pas de cours, pas de tutorat.
""")
```

### ÉTAPE 4 — CLI amélioré

Dans `main.py` :
- Ajouter une commande `/import chatgpt <path>` pour importer un export ChatGPT
- Ajouter une commande `/collisions` pour forcer un scan Cold Weaver
- Ajouter une commande `/status` pour voir l'état de la persona et de la mémoire

### CONTRAINTES

1. Les embeddings : utiliser un modèle d'embedding. Options :
   - MiniMax embedding API (si disponible)
   - Sentence-transformers local (all-MiniLM-L6-v2)
   - Fallback : hash TF-IDF simple pour le prototype
2. Le Cold Weaver scan tourne en CRON ou manuellement, PAS à chaque message
3. Max 1 collision restituée par session (invariant 6)
4. Logs obligatoires pour chaque collision détectée + restituée ou non
5. requirements.txt : ajouter sentence-transformers si embedding local

### CE QU'ON VEUT TESTER

Le test ultime : importer un export ChatGPT réel, laisser le Cold Weaver tourner, et voir si une collision émerge qui fait "oh, j'avais pas pensé à ça". Si oui, le MVP est validé.
