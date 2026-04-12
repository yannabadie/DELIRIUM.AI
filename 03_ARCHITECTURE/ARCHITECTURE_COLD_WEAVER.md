# Architecture Cold Weaver — Delirium AI

**Version :** 2.0 | **Date :** 12 avril 2026

---

## 1. Pipeline

```
SOURCES (ArXiv, GitHub, RSS, Historiques IA, Conversations)
  → PROCESSING (Embed, Distances, Détection collisions)
  → OUTPUT (Collisions, Notifications, Graphe, Notes autonomes)
```

## 2. Sources de Veille

- **ArXiv** — quotidien, tous domaines, embedding sur abstract
- **GitHub** — hebdomadaire, trending + releases, embedding description+README
- **Presse** — quotidien, RSS configurables, embedding titre+excerpt
- **Historiques IA** — import manuel, re-scan périodique

---

## 3. Détection d'Inspirations Avortées (4 critères)

### 3.1 Friction Sémantique
Distance cosinus Q/R élevée → zone de malentendu créatif.

### 3.2 Récurrence Latente
Clustering HDBSCAN cross-plateforme → thème obsessionnel non nommé.

### 3.3 Abandon Après Résistance
Insistance → reformulation × 2 → changement de sujet → idée tuée par friction.

### 3.4 Surgissement Non Rebondi
Concept IA ignoré mais matché dans une conversation future → graine latente.

---

## 4. Moteur de Collision

Cross-domaine : proximité sémantique élevée + domaines différents = collision. Top-K nearest, seuil configurable, déduplication.

### Formatage des Notifications
```
Ton intrigant, pas didactique. "Eh, regarde ça."
Jamais "j'ai analysé". Maximum 2 phrases. Question ou invitation.
```

---

## 5. Métriques

| Métrique | Cible |
|---|---|
| Collisions/semaine | 1-3 (qualité > quantité) |
| Taux de clic | > 40% |
| Taux de rebond vers conversation | > 20% |
| Faux positifs signalés | < 30% |
| Time-to-first-collision | < 30 jours |

---

## 6. Collision Score — Formule SerenQA

Ancré dans SerenQA (Wang et al. 2025, arXiv:2511.12472) :

```python
def collision_score(user_fragment, external_content, user_db):
    R = cosine_similarity(user_fragment.embedding, external_content.embedding)
    N = 1 - max(cosine_similarity(f.embedding, external_content.embedding) 
                for f in user_db.all_fragments())
    S = 1 - abs(R - 0.5) * 2  # sweet spot : max à R=0.5

    alpha_R, alpha_N, alpha_S = 0.3, 0.3, 0.4  # [NC: à calibrer]
    return alpha_R * R + alpha_N * N + alpha_S * S
```

**Sweet spot :** Liu et al. (2026) — les combinaisons plus distantes produisent des idées plus originales. Mais trop distant = non pertinent. Fonction S = maximum quand R ≈ 0.5.

**Seuil notification :** collision_score > 0.5 [NC: à calibrer]

---

## 7. Vie Autonome de Delirium

Le Cold Weaver alimente aussi la **vie autonome** dans le Non-BlocNote :

```
Collisions détectées → 2 usages :

1. NOTIFICATION UTILISATEUR (si score > seuil)
   Format : "rien à voir mais..." — intrigant, pas didactique

2. NOTES AUTONOMES DE DELIRIUM (toujours)
   Collisions reformulées en "questions de Delirium" dans le carnet
   Ex: collision parking + reforestation → "Les parkings sont des forêts mortes ?"
```

### Injection Bruit Utile (Utilisateur en Bulle)

Quand H_bulle élevé + Cold Weaver sans collision naturelle :
- Contenu ADJACENT aux clusters (pas orthogonal)
- Max 1/session, arrêt après 3 ignores
- Objectif : élargir les clusters, pas forcer la diversification

---

## 8. Sycophancy Score — Import Historiques IA

```python
def sycophancy_score(fragment, ai_responses):
    # Mesure validation molle par les IA externes
    for response in ai_responses:
        agreement = nli_entailment_score(fragment, response)
        sourced = has_sources(response)
        challenged = has_counterargument(response)
        syc = 0.4 * agreement + 0.3 * (1 - sourced) + 0.3 * (1 - challenged)
    # Alimente le risque de transition H→B (biais enfoui)
```

Ancrage : Sharma et al. (2023) — sycophantie dans les LLM.
