# Prompt Claude Code — Amélioration Qualité des Collisions

## CONTEXTE

Le Cold Weaver produit 238 collisions, mais ~80% sont du bruit (paires intra-domaine triviales). Les causes :

1. **Pas de filtre same-conversation** : deux messages de la MÊME conversation Claude sont pairés. Ils sont liés trivialement (même fil de pensée). Le session_id est `import_claude_{conversation_title}` — deux fragments avec le même session_id ne devraient JAMAIS être une collision.

2. **ArXiv désactivé** : `engine.scan(include_arxiv=False)`. Les collisions cross-domaine les plus intéressantes viennent de sources EXTÉRIEURES. Activer ArXiv par défaut.

3. **Pas de filtre de qualité LLM** : la connexion est générée APRÈS que la collision est stockée. Le LLM devrait aussi JUGER si la connexion est intéressante ou triviale.

## CHANGEMENTS À FAIRE

### 1. Filtre same-conversation dans `_generate_candidates()`

```python
# Dans la boucle same-source, exclure les paires du même session_id
if sorted_frags[i].get("session_id") == sorted_frags[j].get("session_id"):
    continue  # même conversation = connexion triviale
```

S'assurer que `get_all_with_embeddings()` retourne aussi le `session_id`.

### 2. Activer ArXiv par défaut dans `/collisions`

Dans `main.py`, changer :
```python
n = engine.scan(include_arxiv=True)  # était False
```

### 3. Filtre de qualité LLM pour les connexions

Modifier `_generate_connection()` pour aussi évaluer la qualité :

```python
def _generate_connection(self, frag_a, frag_b) -> tuple[str, float]:
    """Returns (connection_text, quality_score).
    
    quality_score < 0.3 = connexion triviale → ne pas stocker
    """
    prompt = """Tu es le Cold Weaver de Delirium. 

    Deux idées d'un utilisateur :
    - Idée A : {a}
    - Idée B : {b}

    1. Ces deux idées ont-elles une connexion NON-TRIVIALE ? (pas juste "les deux parlent de tech")
    2. Si oui, décris la connexion en UNE phrase mystérieuse.
    3. Score la qualité de la connexion de 0 (triviale) à 1 (insight profond).

    Réponds en JSON : {{"connection": "...", "quality": 0.0-1.0, "trivial": true/false}}
    Si trivial=true, connection peut être vide.
    """
```

Ne stocker la collision QUE si `quality >= 0.4`.

### 4. Supprimer les collisions existantes de faible qualité

Purger les 238 collisions existantes avant de re-scanner :
```sql
DELETE FROM collisions;
```

### 5. Ajouter `/collisions --purge` pour reset

Commande pour purger et re-scanner proprement.

### 6. Tester

Après les changements :
```bash
python -m src.main
# /collisions --purge
```

On veut voir :
- Moins de collisions (~10-30 au lieu de 238)
- Mais de MEILLEURE qualité (cross-conversation, cross-domaine)
- Des connexions ArXiv (claude ↔ arxiv)

### CONTRAINTES
- Les 39 tests existants doivent passer
- Logs obligatoires pour chaque collision filtrée (et pourquoi)
