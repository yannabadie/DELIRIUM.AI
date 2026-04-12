# Prompt Claude Code — Fix Cold Weaver Scoring (Urgent)

## LE PROBLÈME

Le Cold Weaver ne produit aucune collision sur 1419 fragments importés de Claude.ai.

Voici les données debug d'un scan réel :

```
pair 501: sim=0.454 S=0.768 N=0.121 R=0.500 score=0.047 | A='Analyse ce site...' B='Je veux une discussion...'
pair 504: sim=0.412 S=0.559 N=0.134 R=0.500 score=0.037 | A='tu as accès a mes info...' B='As-tu un agent mode...'
pair 508: sim=0.424 S=0.622 N=0.130 R=0.500 score=0.040 | A='Bonjour, je souhaite...' B='J'ai tout posté...'
```

**Surprise (S) fonctionne** — les paires dans le sweet spot [0.3, 0.7] scorent bien.

**Relevance (R) = 0.500 toujours** — aucun thème actif dans le graphe sémantique (les imports ne passent pas par le S2, donc pas de thèmes). 0.5 est le fallback "neutre".

**Novelty (N) est le tueur** — même avec threshold à 0.97, N ≈ 0.12-0.20. Avec 1419 embeddings denses, la moyenne de DEUX fragments est toujours cosine > 0.95 avec un fragment existant. Le concept de "novelty par midpoint" ne marche pas pour un corpus dense.

**Score final = S × N × R ≈ 0.768 × 0.12 × 0.5 = 0.046** → bien en dessous du seuil de 0.3.

## CE QU'IL FAUT FAIRE

### 1. Repenser la Novelty

L'idée originale (midpoint du pair proche d'un fragment existant = pas novel) est fondamentalement cassée pour les corpus denses. 

Alternatives :
- **Novelty par thèmes** : la paire est novel si les deux fragments viennent de THÈMES DIFFÉRENTS (pas de nœud commun dans le graphe sémantique)
- **Novelty par conversation** : la paire est novel si les deux fragments viennent de conversations DIFFÉRENTES (conversation_id différent)
- **Novelty par temps** : la paire est novel si les deux fragments sont séparés par > N jours
- **Supprimer la Novelty** et simplifier : Score = Surprise × Relevance. La surprise (sweet spot cosine) EST déjà une mesure de nouveauté implicite — deux fragments dans [0.3, 0.7] ne sont ni identiques ni sans rapport.

Recommandation : **Score = Surprise × Relevance_boosted**, où Relevance est calculée même sans thèmes actifs.

### 2. Repenser la Relevance quand il n'y a pas de thèmes

Actuellement : `if not theme_embeddings: return 0.5`. C'est le cas pour les imports (pas de S2 → pas de thèmes).

Alternatives :
- **Auto-thèmes** : avant le scan, extraire les top-K thèmes du corpus importé par clustering (KMeans sur les embeddings, puis label les clusters)
- **Relevance par contenu** : au lieu de dépendre des thèmes, mesurer si les deux fragments ont du CONTENU substantiel (pas juste "bonjour", "merci", etc.). Filtrer les messages courts (< 20 mots) et les messages purement procéduraux.
- **Relevance = 1.0 par défaut** et compter uniquement sur Surprise pour filtrer

Recommandation : **Filtrer les messages courts + Relevance = 1.0 par défaut** pour les imports.

### 3. Filtrer le bruit

Beaucoup des 1419 messages sont du bruit : "Bonjour", "Merci", "Ok", questions purement techniques sans idée ("erreur de vscode"). 

**Avant le scan, filtrer :**
- Messages < 30 caractères → exclus
- Messages purement procéduraux (regex : "bonjour", "merci", "ok", "d'accord", "voilà") → exclus
- Ne garder que les messages qui contiennent une IDÉE ou une QUESTION substantive

### 4. Implémenter

Modifie `src/cold_weaver/scoring.py` et `src/cold_weaver/engine.py` :

1. Ajouter un filtre de bruit dans `_embed_missing()` ou `get_all_with_embeddings()` (marquer les fragments < 30 chars comme `skip_collision=True`)
2. Simplifier le score : `Score = Surprise × Relevance` (supprimer Novelty)
3. Relevance par défaut = 1.0 quand pas de thèmes, 0.0 pour les messages procéduraux
4. Remonter DELIVERY_THRESHOLD à 0.5 une fois que ça fonctionne
5. Supprimer le debug logging une fois le fix validé

### 5. Tester

Après le fix :
```bash
python -m src.main
# /import claude <path>  (si la DB est vide)
# /collisions
```

On veut voir :
- Des collisions entre des sujets DIFFÉRENTS mais RELIÉS (ex: "architecture ISA-88" ↔ "comment organiser un projet")
- Un score > 0.5 pour les bonnes collisions
- 0 collision entre messages procéduraux

### CONTRAINTE

Les 39 tests existants doivent toujours passer.
