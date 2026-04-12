# H_bulle — Détection de Bulle Algorithmique par Signaux Conversationnels

**Date :** 12 avril 2026
**Statut :** Spécification formelle + gap de recherche identifié
**Ancrage :** Pariser (2011), Kitchens et al. (2020), Figà Talamanca & Arfini (2022)
**Nouveauté :** Mesure de bulle par signaux CONVERSATIONNELS (pas par analyse de flux)

---

## 1. Le Problème Spécifique à Delirium

La littérature mesure les bulles via l'analyse des feeds (diversité des sources, homophilie des réseaux, clustering sémantique des contenus consommés). Delirium n'a PAS accès aux feeds de l'utilisateur. Il a accès :

1. Aux conversations Delirium
2. Aux historiques IA importés (ChatGPT, Claude, Gemini)
3. À rien d'autre

**Question :** Comment détecter qu'un utilisateur est dans une bulle algorithmique uniquement à partir de ses conversations ?

**Gap de recherche :** Aucune étude identifiée ne propose de détecter les bulles via l'analyse conversationnelle. C'est un paradigme nouveau.

---

## 2. Les 6 Signaux Conversationnels de Bulle

### S1 — Rétrécissement Thématique (Topic Narrowing)

L'utilisateur parle de moins en moins de sujets distincts au fil du temps.

```python
def topic_narrowing(semantic_memory, window_days=90):
    """Mesure la diversité thématique sur une fenêtre glissante."""
    
    themes_recent = semantic_memory.get_themes(last_n_days=30)
    themes_past = semantic_memory.get_themes(from_days_ago=90, to_days_ago=30)
    
    diversity_recent = len(set(t['label'] for t in themes_recent))
    diversity_past = len(set(t['label'] for t in themes_past))
    
    if diversity_past == 0:
        return 0.0  # pas assez de données
    
    ratio = diversity_recent / diversity_past
    # ratio < 1.0 = rétrécissement, > 1.0 = élargissement
    return clamp(1.0 - ratio, 0.0, 1.0)  # 0 = pas de bulle, 1 = bulle forte
```

**Pourquoi ça marche :** Les bulles ne créent pas de nouvelles obsessions — elles **rétrécissent** le champ d'intérêt. Quelqu'un qui parlait de cuisine, politique, sport et musique et qui ne parle plus que de politique est peut-être dans une bulle.

**Attention :** Un rétrécissement peut aussi être un approfondissement naturel (passion, projet). Le S2 doit distinguer les deux.

### S2 — Inflation de Certitude (Certainty Drift)

L'utilisateur devient de plus en plus certain sur des sujets contestés.

Marqueurs linguistiques :
- Augmentation de "c'est évident", "tout le monde sait", "clairement"
- Diminution de "je pense", "peut-être", "il me semble"
- Passage de questions ouvertes ("qu'est-ce que t'en penses ?") à des affirmations fermées ("c'est comme ça")

```python
def certainty_drift(conversation_history, window_messages=50):
    """Mesure l'évolution du ratio certitude/doute."""
    
    certainty_markers = ["c'est évident", "tout le monde sait", "clairement",
                         "bien sûr", "forcément", "c'est un fait", "y'a pas de débat"]
    doubt_markers = ["je pense", "peut-être", "il me semble", "j'ai l'impression",
                     "je sais pas trop", "possible que", "tu crois que"]
    
    recent = conversation_history[-window_messages:]
    older = conversation_history[-2*window_messages:-window_messages]
    
    ratio_recent = count_markers(recent, certainty_markers) / (count_markers(recent, doubt_markers) + 1)
    ratio_older = count_markers(older, certainty_markers) / (count_markers(older, doubt_markers) + 1)
    
    drift = ratio_recent - ratio_older  # positif = inflation de certitude
    return clamp(drift / 3.0, 0.0, 1.0)
```

### S3 — Langage Outgroup (Us vs. Them)

Augmentation de la distinction "nous/eux" dans le discours.

Marqueurs : "les gens comme eux", "de toute façon ils", "ces gens-là", "le problème c'est eux"

**Lien IPC :** Un shift vers l'octant DE (froid-querelleur) sur les sujets sociaux/politiques, combiné à une position LM (chaleureux-soumis) dans le in-group.

### S4 — Résistance aux Injections Latérales

Quand Delirium fait un "rien à voir mais...", l'utilisateur :
- **En bulle :** ignore, rejette, revient immédiatement au sujet précédent
- **Hors bulle :** s'intéresse, rebondit, fait des connexions

```python
def injection_resistance(injection_history):
    """Mesure la résistance aux injections latérales."""
    
    if len(injection_history) < 3:
        return 0.0
    
    ignored = sum(1 for i in injection_history if i['user_response'] == 'ignored')
    rejected = sum(1 for i in injection_history if i['user_response'] == 'rejected')
    engaged = sum(1 for i in injection_history if i['user_response'] == 'engaged')
    
    total = len(injection_history)
    resistance = (ignored + rejected * 0.5) / total
    return clamp(resistance, 0.0, 1.0)
```

**C'est le signal le plus spécifique à Delirium** — aucun autre système ne peut le mesurer car aucun autre système ne fait des injections latérales.

### S5 — Écho dans les Historiques IA (Import)

Quand les historiques ChatGPT/Claude sont importés, le Cold Weaver peut détecter :
- Les mêmes questions posées à plusieurs IA avec un framing validation-seeking
- L'absence de challenge dans les réponses (sycophancy score des IA externes)
- Un sujet récurrent avec validation systématique

```python
def echo_in_ai_history(imported_conversations):
    """Détecte les patterns de validation-seeking dans les historiques IA."""
    
    # Grouper par thème
    themes = cluster_by_theme(imported_conversations)
    
    for theme in themes:
        # Vérifier si l'utilisateur a posé la même question à plusieurs IA
        if theme.cross_platform_count >= 2:
            # Vérifier si les réponses sont validantes (sycophancy score)
            avg_sycophancy = mean(r.sycophancy_score for r in theme.responses)
            if avg_sycophancy > 0.7:
                # L'utilisateur cherche de la validation, pas de l'information
                theme.echo_score = 0.8
    
    return max(t.echo_score for t in themes) if themes else 0.0
```

### S6 — Homogénéité des Sources Citées

Quand l'utilisateur cite des sources (articles, vidéos, personnes), sont-elles homogènes ?

- Toujours le même média → bulle informationnelle
- Toujours la même figure d'autorité → personnalisation excessive
- Toujours le même angle → biais de confirmation

---

## 3. Score H_bulle

```python
def h_bulle(semantic_memory, conversation_history, injection_history, 
            imported_conversations=None):
    """
    Score de bulle ∈ [0, 1].
    0 = aucun signe de bulle
    1 = bulle forte et convergente
    """
    
    s1 = topic_narrowing(semantic_memory)
    s2 = certainty_drift(conversation_history)
    s3 = outgroup_language(conversation_history)
    s4 = injection_resistance(injection_history)
    s5 = echo_in_ai_history(imported_conversations) if imported_conversations else 0.0
    s6 = source_homogeneity(conversation_history)
    
    weights = {
        'narrowing': 0.25,      # le plus fiable
        'certainty': 0.20,      # bien ancré linguistiquement
        'outgroup': 0.15,       # fort signal mais faux positifs
        'injection_resistance': 0.20,  # spécifique à Delirium
        'echo_ai': 0.10,        # dépend des imports
        'source_homogeneity': 0.10
    }
    
    score = (
        weights['narrowing'] * s1 +
        weights['certainty'] * s2 +
        weights['outgroup'] * s3 +
        weights['injection_resistance'] * s4 +
        weights['echo_ai'] * s5 +
        weights['source_homogeneity'] * s6
    )
    
    return clamp(score, 0.0, 1.0)
```

---

## 4. Réponse de Delirium aux Signaux de Bulle

### Principe : Bruit Utile Adjacent, Jamais Contradiction Frontale

Delirium ne DIT PAS "tu es dans une bulle". Il AGIT :

| H_bulle | Action Delirium |
|---|---|
| < 0.3 | Rien. Comportement normal. |
| 0.3-0.5 | Augmente la fréquence des injections latérales sur des sujets orthogonaux au sujet dominant |
| 0.5-0.7 | Introduit des perspectives cross-domaine via le Cold Weaver. "Rien à voir mais j'ai trouvé un truc qui contredit ce que tu disais la semaine dernière." |
| > 0.7 | Commence à poser des questions MI sur les sources : "Tu l'as lu où ça ?" sans juger. Propose des sources alternatives via le Cold Weaver. |

### Ce que Delirium ne fait JAMAIS
- "Tu es dans une bulle" (diagnostic interdit)
- "Tu devrais lire autre chose" (conseil non sollicité interdit)
- Contradiction frontale sur les croyances (confrontation rétro interdite)
- Proposition de sources "opposées" (ce serait du bruit inutile, pas du bruit adjacent)

### Ce que Delirium fait
- Introduit du bruit ADJACENT (pas opposé, pas aléatoire)
- Pose des questions sur les sources sans jugement
- Utilise les injections latérales pour ÉLARGIR le champ progressivement
- Laisse le Cold Weaver faire le travail en surface

---

## 5. Distinction : Bulle vs. Passion vs. Projet

Un rétrécissement thématique n'est pas toujours une bulle :

| Signal | Bulle | Passion | Projet |
|---|---|---|---|
| Rétrécissement thématique | Oui | Oui | Oui |
| Inflation de certitude | **Oui** | Non (reste curieux) | Possible |
| Langage outgroup | **Oui** | Non | Non |
| Résistance injections | **Oui** | Non (rebondit) | Partielle (occupé) |
| Diversité des questions | Diminue | **Augmente** (profondeur) | Stable |
| Émotion dominante | Frustration, indignation | Enthousiasme | Concentration |

Le S2 doit utiliser ces critères pour distinguer les trois cas. La passion et le projet ne déclenchent PAS le protocole bulle.

---

## 6. Gap de Recherche

Aucune étude identifiée ne propose de détecter les bulles via l'analyse conversationnelle seule (sans accès aux feeds ou aux réseaux). C'est un paradigme nouveau qui pourrait donner lieu à une publication :

**Titre potentiel :** "Conversational Markers of Algorithmic Bubble Exposure: A Novel Detection Framework for AI Companions"

**Contribution :** Montrer que les patterns conversationnels (rétrécissement thématique, inflation de certitude, résistance aux perturbations) sont des proxies fiables de l'exposition aux bulles algorithmiques.

**Méthodologie :** Étude N=200, corrélation entre les signaux conversationnels détectés par Delirium et les mesures objectives de diversité informationnelle (analyse des flux réels).

---

## 7. Références

- Pariser, E. (2011). The Filter Bubble: What the Internet Is Hiding from You.
- Kitchens, B., Johnson, S.L. & Gray, P. (2020). Understanding Echo Chambers and Filter Bubbles. MIS Quarterly.
- Figà Talamanca, G. & Arfini, S. (2022). Through the Newsfeed Glass: Rethinking Filter Bubbles and Echo Chambers. PMC.
- Bakshy, E. et al. (2015). Exposure to ideologically diverse news and opinion on Facebook. Science.
- Bail, C. et al. (2018). Exposure to opposing views on social media can increase political polarization. PNAS.
