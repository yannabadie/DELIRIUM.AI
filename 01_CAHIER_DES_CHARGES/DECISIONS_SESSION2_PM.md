# Décisions de Design — Session 12 avril 2026 (après-midi)

**Source :** Réponses de Yann aux questions ouvertes

---

## D1 — Passage Delirium → OmniArxiv

**Décision :** L'utilisateur décide. Pas Delirium.

L'IA est là pour :
- Rendre les idées cohérentes
- Vérifier si elles sont nouvelles
- Les affiner, les assembler
- Proposer d'en parler à des amis (pas de sycophantie — "je pense que c'est intéressant" seulement si c'est vrai)

Le début de la publication peut être :
- Une musique
- Une histoire
- Une théorie philosophique
- N'importe quelle forme de connaissance

**Implication technique :** Delirium doit pouvoir détecter quand une idée a atteint une maturité suffisante (C+ dans le formalisme, cross-validée par le Cold Weaver) et PROPOSER — pas pousser — la publication. "T'as un pote à qui tu pourrais montrer ça ?" est le premier pas vers OmniArxiv.

---

## D2 — Déclencheur de la Pub Absurdiste

**Décision :** Pas de déclencheur déterministe.

La pub absurdiste peut arriver quand :
- L'IA considère que l'utilisateur le prend pour une IA "normale" (sycophante, assistant, outil)
- L'utilisateur "ennuie" Delirium (fatigue > seuil, répétition sans avancée)

**Ce que ça signifie :** La pub absurdiste est un mécanisme de RUPTURE. C'est Delirium qui dit "stop, tu me prends pour qui ?" mais avec humour au lieu de confrontation. C'est le H qui monte en créativité et en confrontation simultanément.

**Implémentation :** La décision de déclencher une pub est prise par le S1 lui-même (pas par une règle externe). Le system prompt donne le DROIT de le faire, pas l'OBLIGATION. C'est une émergence comportementale, pas un algorithme.

---

## D3 — Interaction entre Delirium Instances

**Décision :** AUCUNE donnée personnelle. AUCUN trait de caractère.

Seules les **idées du Jardin** peuvent circuler entre instances, et encore — éventuellement.

**Ce que ça signifie :**
- Quand un Delirium "dîne" avec un autre Delirium, ils ne partagent PAS d'information sur leurs utilisateurs respectifs
- Ils partagent des IDÉES anonymisées ("une personne a eu l'idée que les parkings pourraient être des forêts")
- Ces idées alimentent le Cold Weaver de l'autre instance (collision cross-utilisateur)
- L'utilisateur n'est JAMAIS identifiable dans ces échanges

**RGPD :** Conforme — les idées sont anonymisées et décontextualisées avant le partage. Pas de données personnelles, pas de traitement de données sensibles. C'est de l'agrégation thématique, pas du profilage.

**C'est aussi un premier pas vers OmniArxiv** — les idées circulent entre jardins privés avant de devenir publiques.
