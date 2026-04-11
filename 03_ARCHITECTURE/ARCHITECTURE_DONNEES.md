# Architecture Données — Delirium AI

**Version :** 1.0 | **Date :** 11 avril 2026

---

## 1. Modèle de Données Local

### 1.1 SQLite (Relationnel — Historique et Métadonnées)

```sql
-- Profil utilisateur et archétype
CREATE TABLE user_profile (
    id TEXT PRIMARY KEY DEFAULT 'self',
    name TEXT NOT NULL,
    birthdate DATE,
    archetype_json TEXT,           -- Archétype courant (JSON)
    archetype_version INTEGER,     -- Numéro de version (incrémenté à chaque affinement)
    osint_consented BOOLEAN DEFAULT FALSE,
    osint_raw_json TEXT,           -- Données OSINT brutes (purgées après traitement)
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Conversations
CREATE TABLE conversations (
    id TEXT PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    user_input TEXT NOT NULL,       -- Transcript de l'utilisateur
    s1_response TEXT,              -- Réponse S1
    s2_analysis TEXT,              -- Analyse S2 (jamais affichée)
    intensity_level TEXT CHECK(intensity_level IN ('banal','original','provocant','violent')),
    source TEXT DEFAULT 'delirium', -- 'delirium', 'chatgpt', 'claude', 'gemini', 'copilot'
    embedding_id TEXT,             -- Référence vers le vault vectoriel
    graph_node_ids TEXT,           -- Références vers les nœuds du graphe (JSON array)
    is_inspiration_aborted BOOLEAN DEFAULT FALSE,
    abort_criteria TEXT,           -- Critère de détection si applicable
    created_at TIMESTAMP
);

-- Collisions Cold Weaver
CREATE TABLE collisions (
    id TEXT PRIMARY KEY,
    fragment_ids TEXT NOT NULL,     -- JSON array des conversation IDs liés
    external_source_url TEXT,      -- URL du papier/repo/article
    external_source_title TEXT,
    external_source_summary TEXT,  -- Résumé court (pas de reproduction)
    collision_score REAL,          -- Score de proximité sémantique
    notification_text TEXT,        -- Texte de notification formaté
    status TEXT CHECK(status IN ('pending','notified','viewed','dismissed')),
    created_at TIMESTAMP,
    notified_at TIMESTAMP,
    viewed_at TIMESTAMP
);

-- Invitations
CREATE TABLE invitations (
    id TEXT PRIMARY KEY,
    inviter_description TEXT,      -- Description custom de l'invité
    is_anonymous BOOLEAN DEFAULT FALSE,
    inviter_name TEXT,             -- Null si anonyme
    invite_link TEXT,
    status TEXT CHECK(status IN ('pending','accepted','expired')),
    created_at TIMESTAMP
);

-- Timeline Vision du Monde
CREATE TABLE vision_timeline (
    id TEXT PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    event_type TEXT CHECK(event_type IN ('theme_detected','loop_detected','bubble_detected','collision','archetype_update')),
    description TEXT,
    confidence REAL,               -- 0.0 à 1.0
    related_conversation_ids TEXT,  -- JSON array
    created_at TIMESTAMP
);
```

### 1.2 Base Vectorielle (ChromaDB ou LanceDB)

```
Collection : user_fragments
  - id : TEXT (= conversations.embedding_id)
  - embedding : FLOAT[768] ou FLOAT[1536] (selon modèle)
  - metadata : {
      source: 'delirium' | 'chatgpt' | 'claude' | 'gemini' | 'copilot',
      timestamp: ISO8601,
      intensity: 'banal' | 'original' | 'provocant' | 'violent',
      weight: FLOAT (décroît avec le temps si non réactivé),
      themes: [string]
    }

Collection : external_knowledge
  - id : TEXT
  - embedding : FLOAT[768/1536]
  - metadata : {
      source_type: 'arxiv' | 'github' | 'press',
      url: TEXT,
      title: TEXT,
      date: ISO8601,
      domain_tags: [string]
    }
```

### 1.3 Graphe (Lightweight — JSON ou SQLite-backed)

```
Nœuds :
  - type : 'theme' | 'idea' | 'frustration' | 'joy' | 'loop' | 'external_concept'
  - label : TEXT
  - weight : FLOAT (décroît si non réactivé — oubli sélectif)
  - first_seen : TIMESTAMP
  - last_activated : TIMESTAMP
  - activation_count : INTEGER

Arêtes :
  - type : 'related_to' | 'contradicts' | 'evolved_from' | 'collision_with'
  - weight : FLOAT
  - created_at : TIMESTAMP
```

---

## 2. Oubli Sélectif

### 2.1 Mécanisme

```python
# Pseudo-code de dégradation
def decay_weight(node, current_time):
    days_since_activation = (current_time - node.last_activated).days
    half_life = 90  # jours, configurable
    node.weight *= 0.5 ** (days_since_activation / half_life)
    if node.weight < THRESHOLD_FORGET:  # ex: 0.01
        delete_node(node)
```

### 2.2 Règles
- Les nœuds non réactivés perdent du poids exponentiellement (demi-vie configurable, défaut 90 jours)
- Sous le seuil d'oubli : le nœud et ses arêtes sont supprimés
- Les conversations source restent dans SQLite (historique) mais les embeddings sont purgés
- L'utilisateur peut "protéger" un nœud de l'oubli (pin)
- L'utilisateur peut forcer l'oubli d'un nœud spécifique

---

## 3. Import Historiques IA Externes

### 3.1 Formats Supportés

| Plateforme | Format | Parser |
|---|---|---|
| ChatGPT | JSON (export settings) | Paires message user/assistant |
| Claude | JSON (export API) | Paires human/assistant |
| Gemini | Google Takeout | Format spécifique Google |
| Copilot | À déterminer | TBD |
| Manuel | ZIP/JSON générique | Heuristique Q/R |

### 3.2 Pipeline d'Import
1. Upload fichier (local uniquement, pas d'envoi cloud)
2. Parsing selon format
3. Extraction paires Q/R
4. Embeddings
5. Détection inspirations avortées (4 critères)
6. Stockage fragments qualifiés
7. Purge du fichier importé

---

## 4. Portabilité (Export)

Format d'export standard :
```json
{
  "version": "1.0",
  "exported_at": "ISO8601",
  "profile": { ... },
  "conversations": [ ... ],
  "graph": { "nodes": [...], "edges": [...] },
  "collisions": [ ... ],
  "vision_timeline": [ ... ]
}
```
Pas d'export des embeddings (non réversibles, reconstituables).
