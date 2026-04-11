# Architecture Cold Weaver — Delirium AI

**Version :** 1.0 | **Date :** 11 avril 2026

---

## 1. Pipeline

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│ SOURCES          │     │ PROCESSING       │     │ OUTPUT          │
│                  │     │                  │     │                 │
│ ArXiv API ───────┼────►│ Embed nouveaux   │     │ Collisions      │
│ GitHub Trending ─┼────►│ contenus         │────►│ détectées       │
│ RSS Presse ──────┼────►│                  │     │                 │
│                  │     │ Calcul distances │     │ Notifications   │
│ Historiques IA ──┼────►│ vs fragments     │────►│ formatées       │
│ (import)         │     │ utilisateur      │     │                 │
│                  │     │                  │     │ Graphe mis      │
│ Conversations ───┼────►│ Détection        │────►│ à jour          │
│ Delirium         │     │ collisions       │     │                 │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

---

## 2. Sources de Veille

### 2.1 ArXiv
- **API :** OAI-PMH (bulk metadata) + REST API (search)
- **Fréquence :** Quotidienne
- **Filtrage :** Pas de filtre disciplinaire — tout domaine est pertinent (cross-domain = le but)
- **Données extraites :** Titre, abstract, auteurs, catégories, date
- **Embedding :** Abstract uniquement (pas le full paper)

### 2.2 GitHub
- **API :** GitHub REST/GraphQL — trending repos, new releases
- **Fréquence :** Hebdomadaire
- **Données extraites :** Nom repo, description, README (premiers 500 mots), stars, language
- **Embedding :** Description + README tronqué

### 2.3 Presse
- **Sources :** Flux RSS configurables (par défaut : généralistes multi-langues)
- **Fréquence :** Quotidienne
- **Données extraites :** Titre, excerpt, URL
- **Embedding :** Titre + excerpt

### 2.4 Historiques IA Externes
- **Sources :** Imports manuels (ChatGPT, Claude, Gemini, Copilot)
- **Fréquence :** À l'import + re-scan périodique si nouvelles données
- **Pipeline spécifique :** Voir section 3

---

## 3. Détection d'Inspirations Avortées (Historiques IA)

### 3.1 Critère 1 — Friction Sémantique

```python
def detect_semantic_friction(question_embedding, answer_embedding, threshold=0.6):
    """
    Si la distance cosinus entre Q et R est élevée,
    l'IA a peut-être compris de travers → zone de malentendu créatif.
    """
    distance = cosine_distance(question_embedding, answer_embedding)
    if distance > threshold:
        return FrictionSignal(
            type='semantic_friction',
            score=distance,
            q_fragment=question,
            r_fragment=answer
        )
```

### 3.2 Critère 2 — Récurrence Latente

```python
def detect_latent_recurrence(user_fragments, min_cluster_size=3, max_distance=0.3):
    """
    Clustering des fragments utilisateur cross-plateforme.
    Si un cluster apparaît avec des fragments de sources différentes
    et des formulations différentes → thème obsessionnel non nommé.
    """
    clusters = hdbscan.HDBSCAN(min_cluster_size=min_cluster_size).fit(embeddings)
    for cluster in clusters:
        sources = set(f.source for f in cluster.fragments)
        if len(sources) >= 2:  # Cross-plateforme
            return RecurrenceSignal(
                type='latent_recurrence',
                theme=extract_theme(cluster),
                fragments=cluster.fragments
            )
```

### 3.3 Critère 3 — Abandon Après Résistance

```python
def detect_resistance_abandonment(conversation):
    """
    Pattern : user insiste sur un point → reformule → reformule encore → change de sujet.
    La séquence d'insistance suivie d'un abandon est un signal d'idée tuée par la friction.
    """
    for window in sliding_window(conversation, size=5):
        if (count_reformulations(window) >= 2 and
            topic_change_detected(window[-1], window[-2])):
            return AbandonSignal(
                type='resistance_abandonment',
                abandoned_topic=extract_topic(window[:-1]),
                conversation_id=conversation.id
            )
```

### 3.4 Critère 4 — Surgissement Non Rebondi

```python
def detect_unbounced_emergence(conversation, user_history_embeddings):
    """
    L'IA introduit un concept que l'utilisateur n'a jamais mentionné.
    L'utilisateur ne rebondit pas. Mais le concept matche avec
    un fragment ultérieur (autre conversation, autre plateforme).
    """
    for ai_response in conversation.ai_responses:
        novel_concepts = extract_novel_concepts(ai_response, user_history_embeddings)
        for concept in novel_concepts:
            future_matches = search_future_conversations(concept, user_history_embeddings)
            if future_matches and not user_acknowledged(concept, conversation):
                return EmergenceSignal(
                    type='unbounced_emergence',
                    concept=concept,
                    introduced_in=conversation.id,
                    matched_in=[m.id for m in future_matches]
                )
```

---

## 4. Moteur de Collision

### 4.1 Algorithme

```python
def find_collisions(user_fragments_db, external_knowledge_db, top_k=10, threshold=0.75):
    """
    Pour chaque nouveau contenu externe, chercher les fragments utilisateur
    les plus proches. Si la proximité dépasse le seuil ET que le domaine
    est différent → collision.
    """
    new_externals = external_knowledge_db.get_recent(since=last_run)
    collisions = []
    
    for external in new_externals:
        nearest = user_fragments_db.query(
            embedding=external.embedding,
            n_results=top_k
        )
        for match in nearest:
            if (match.distance < (1 - threshold) and
                external.domain_tags != match.metadata.themes):  # Cross-domaine
                collisions.append(Collision(
                    user_fragment=match,
                    external=external,
                    score=1 - match.distance
                ))
    
    return rank_and_deduplicate(collisions)
```

### 4.2 Formatage des Notifications

Le LLM génère la notification à partir de la collision brute :

```
[INSTRUCTION]
Tu dois formuler une notification Delirium pour l'utilisateur.
Tu as détecté une collision entre un fragment de l'utilisateur et un contenu externe.

Fragment utilisateur (date: {date}) : "{fragment_summary}"
Contenu externe : "{external_title}" — {external_source}

Règles :
1. Ton intrigant, pas didactique. Comme un pote qui dit "eh, regarde ça".
2. Ne dis JAMAIS "j'ai analysé" ou "j'ai détecté".
3. Maximum 2 phrases.
4. Termine par une question ou une invitation.
```

---

## 5. Métriques Cold Weaver

| Métrique | Description | Cible |
|---|---|---|
| Collisions/semaine | Nombre de collisions détectées | 1-3 (qualité > quantité) |
| Taux de clic notifications | % de notifications ouvertes | > 40% |
| Taux de rebond | % de collisions menant à une conversation | > 20% |
| Faux positifs signalés | Collisions jugées non pertinentes par l'utilisateur | < 30% |
| Time-to-first-collision | Délai entre inscription et première collision | < 30 jours |
