# Prompt Claude Code — Fix Cold Start : Extraction de Thèmes depuis les Imports

## LE PROBLÈME

Le Cold Weaver ne trouve pas de thèmes pour ArXiv (`"No active themes for ArXiv fetch"`) parce que le graphe sémantique n'est alimenté QUE par le S2, qui ne tourne QUE sur les conversations Delirium. Résultat : 1419 messages importés de Claude.ai sont dans la mémoire épisodique mais AUCUN thème n'en est extrait.

C'est un bug de cold start. Les imports doivent alimenter le graphe sémantique.

## CE QU'IL FAUT FAIRE

### 1. Extraction de thèmes au moment de l'import

Dans `main.py`, après `_run_import()`, ajouter un appel pour extraire les thèmes des messages importés :

```python
# Après l'import
self._extract_themes_from_import(messages)
```

### 2. Créer la méthode d'extraction de thèmes

Option A — **Extraction par LLM (précise mais coûteuse)** :
Prendre un échantillon de ~50 messages importés, les envoyer au LLM avec un prompt :
```
Voici 50 messages d'un utilisateur. Extrais les 10-20 thèmes principaux.
Réponds en JSON : {"themes": ["theme1", "theme2", ...]}
```
Stocker chaque thème dans le graphe sémantique avec un poids initial proportionnel à sa fréquence.

Option B — **Extraction par clustering d'embeddings (rapide, pas d'API)** :
1. Prendre tous les embeddings des messages importés
2. K-Means clustering (K=15-20)
3. Pour chaque cluster, prendre le message le plus proche du centroïde comme label
4. Stocker chaque cluster comme thème dans le graphe sémantique

**Recommandation : Option A pour le MVP** (plus simple, plus précis, coût ~1 appel LLM par import).

### 3. Implémenter

Crée `src/import_/theme_extractor.py` :

```python
class ThemeExtractor:
    """Extracts themes from imported messages to bootstrap semantic memory."""
    
    def extract(self, messages: list, llm: LLMClient, semantic: SemanticMemory):
        """Extract themes from imported messages and store in semantic graph.
        
        Takes a sample of messages, sends to LLM, stores themes.
        """
        # Sample ~50 substantive messages
        substantive = [m for m in messages if len(m.user_input) > 50]
        sample = random.sample(substantive, min(50, len(substantive)))
        
        # Build prompt
        sample_text = "\n".join([f"- {m.user_input[:150]}" for m in sample])
        
        prompt = """Voici des messages d'un utilisateur envoyés à différentes IA.
Extrais les 10-20 thèmes principaux qui ressortent de ces messages.
Chaque thème doit être un label court (2-4 mots).
Réponds UNIQUEMENT en JSON : {"themes": ["theme1", "theme2", ...]}"""
        
        response = llm.chat(system=prompt, 
                           messages=[{"role": "user", "content": sample_text}])
        themes = json.loads(response)["themes"]
        
        # Count frequency of each theme across ALL messages
        for theme in themes:
            count = sum(1 for m in messages if theme.lower() in m.user_input.lower())
            weight = min(count / len(messages) * 10, 1.0)  # normalize
            semantic.add_or_reinforce_theme(theme, weight)
```

### 4. Modifier semantic.py si nécessaire

S'assurer que `add_or_reinforce_theme(label, weight)` existe. Si non, créer :

```python
def add_or_reinforce_theme(self, label: str, weight: float):
    """Add a theme or increase its weight if it exists."""
    existing = self.conn.execute(
        "SELECT id, weight FROM themes WHERE label = ?", (label,)
    ).fetchone()
    if existing:
        new_weight = min(existing["weight"] + weight, 1.0)
        self.conn.execute("UPDATE themes SET weight = ?, last_activated = ? WHERE id = ?",
                         (new_weight, datetime.now().isoformat(), existing["id"]))
    else:
        self.conn.execute(
            "INSERT INTO themes (id, label, weight, last_activated, activation_count) VALUES (?, ?, ?, ?, ?)",
            (str(uuid4()), label, weight, datetime.now().isoformat(), 1))
    self.conn.commit()
```

### 5. Intégrer dans le flux d'import

Dans `_run_import()` de main.py, après les imports :

```python
# Extract themes for Cold Weaver bootstrapping
from src.import_.theme_extractor import ThemeExtractor
extractor = ThemeExtractor()
extractor.extract(messages, self.llm, self.semantic)
print(f"  Thèmes extraits: {len(themes)}")
```

### 6. Re-scanner

Après le fix, l'utilisateur fait :
```
/collisions --purge
```

Cette fois ArXiv devrait se déclencher avec les thèmes extraits des imports.

## CE QU'ON VEUT VOIR

```
ArXiv fetch: 15 papers for themes ["architecture logicielle", "IA conversationnelle", "gestion de projet", ...]
Collision (0.72, q=0.85): "Comment organiser mon equipe MES" <-> "ArXiv: Self-organizing teams in distributed systems"
```

## CONTRAINTES
- 1 seul appel LLM pour l'extraction (pas 1 par message)
- Les 39 tests doivent passer
- Logs obligatoires
