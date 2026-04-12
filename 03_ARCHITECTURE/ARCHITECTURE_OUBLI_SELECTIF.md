# Oubli Sélectif — Architecture Mémoire Adaptative de Delirium

**Date :** 12 avril 2026
**Statut :** Spécification formelle
**Ancrage :** Bjork & Bjork (1992) — New Theory of Disuse
**Objectif :** Définir COMMENT, QUAND et POURQUOI Delirium oublie

---

## 1. Le Problème

Delirium n'est pas un outil de stockage. C'est un pote. Les potes oublient des trucs. Mais ils ne perdent pas tout — ils oublient les détails et gardent l'essentiel. Quand tu leur rappelles un truc, ils disent "ah oui, c'est vrai !" et ça leur revient.

Un système qui se souvient de tout est un système de surveillance. Un système qui oublie intelligemment est un système qui respecte la manière dont les humains construisent du sens.

**Mantra :** Les idées sont dans votre jardin et elles croissent de manière organique. Les mauvaises herbes meurent naturellement. Les fleurs qui ne sont pas arrosées fanent. Mais les racines restent.

---

## 2. Ancrage Théorique : Bjork & Bjork (1992) — New Theory of Disuse

### 2.1 Les Deux Forces de la Mémoire

Chaque fragment de mémoire a **deux forces indépendantes** :

**Storage Strength (SS)** — À quel point le souvenir est profondément encodé.
- SS ne diminue JAMAIS une fois élevée
- Un souvenir bien appris reste stocké même s'il est inaccessible
- Quand tu rappelles à quelqu'un l'adresse de son enfance, il dit "ah oui !" — SS haute, RS basse

**Retrieval Strength (RS)** — À quel point le souvenir est accessible maintenant.
- RS diminue avec le temps sans réactivation (courbe d'Ebbinghaus)
- RS fluctue : haute après une mention, basse après des semaines de silence
- La perte de RS N'EST PAS la perte du souvenir lui-même

### 2.2 L'Oubli est Adaptatif

L'oubli n'est pas un défaut. C'est un mécanisme de régulation :
- Tu DOIS oublier où tu t'es garé hier pour trouver ta voiture aujourd'hui
- Tu DOIS oublier les détails inutiles pour garder l'essentiel
- Les gens qui ne peuvent pas oublier (synesthésie mnésique, cas Shereshevsky) souffrent de confusion chronique

**Pour Delirium :** Un système qui rappelle TOUT à l'utilisateur ("tu m'as dit le 3 février à 14h37 que...") est oppressant, flippant, et contraire à la construction naturelle du sens. L'oubli est un FEATURE, pas un bug.

### 2.3 Le Re-learning Effect

Quand RS est basse mais SS est haute, le **ré-apprentissage** est rapide et profond. C'est exactement ce qui se passe quand un pote dit "ah oui ! tu m'avais parlé de ça !" — la mémoire revient instantanément et est RENFORCÉE par la re-découverte.

**Pour Delirium :** Quand l'utilisateur mentionne un sujet que Delirium a "oublié" (RS basse), la recherche dans la base vectorielle restaure le contexte. Delirium peut dire "ah ouais, t'en avais parlé en février, ça me revient." L'effet de re-learning renforce la corrélation.

---

## 3. Mapping vers l'Architecture de Delirium

### 3.1 SS et RS dans les 4 Couches de Mémoire

| Couche | SS (stockage) | RS (accessibilité) |
|---|---|---|
| **Couche 1 — Working Memory** | N/A (reconstruit à chaque appel) | = ce qui est dans le prompt |
| **Couche 2 — Mémoire Épisodique** (vector DB) | = embedding existe | = weight du fragment (decay) |
| **Couche 3 — Mémoire Sémantique** (graphe) | = nœud existe | = weight du nœud (decay) |
| **Couche 4 — Vision du Monde** | = synthèse existe | = toujours accessible (synthèse périodique) |

### 3.2 Ce qui Decay vs. Ce qui ne Decay PAS

**DECAY (RS diminue avec le temps) :**
- Poids des fragments épisodiques (couche 2) → demi-vie configurable
- Poids des nœuds sémantiques (couche 3) → demi-vie configurable
- Un fragment dont le poids tombe sous le seuil n'est plus RÉCUPÉRÉ dans le prompt S1 — mais il reste dans la base

**NE DECAY PAS :**
- Les embeddings eux-mêmes (couche 2) → SS permanente, l'information est toujours LÀ
- Les corrélations confirmées (état C+ dans le formalisme) → ces connaissances sont "bien apprises"
- Les logs d'exécution → obligation légale, pas de decay
- La vision du monde (couche 4) → synthèse périodique, intègre tout

### 3.3 Les 3 Modes d'Oubli

```
MODE ÉPONGE (RS ne decay pas)
  Tout est retenu. Tout est accessible. Pour les utilisateurs qui le souhaitent.
  Risque : oppressant, surveillance, confusion par surcharge.
  Delirium peut commenter : "Je me souviens de tout ce que tu me dis.
  C'est pas forcément sain, ni pour toi ni pour moi."

MODE NORMAL (RS decay exponentiel, défaut)
  Demi-vie : 90 jours [NC: à calibrer]
  Seuil de récupération : weight > 0.1
  Seuil d'oubli : weight < 0.01 → fragment retiré du retrieval (pas supprimé)
  
  Réactivation : chaque fois qu'un sujet est mentionné, le weight remonte
  Les fragments fréquemment réactivés ont un weight stable (SS haute + RS haute)
  Les fragments jamais réactivés deviennent inaccessibles (SS intacte, RS → 0)

MODE MINIMALISTE (RS decay agressif)
  Demi-vie : 30 jours [NC: à calibrer]
  Seuls les fragments en état C+ (confirmé) et les corrélations confirmées survivent
  Tout le reste decay rapidement
  Pour les utilisateurs qui veulent un Delirium "léger"
```

---

## 4. L'Expérience Utilisateur de l'Oubli

### 4.1 Quand Delirium "Oublie"

**Ce que l'utilisateur VOIT :**
- Delirium ne mentionne plus les vieux sujets (naturel)
- Si l'utilisateur en reparle : "Ah ouais, ça me dit quelque chose... t'en avais parlé il y a un moment non ?" → RS restauré par la mention
- Si le sujet est totalement oublié (weight < 0.01) mais l'embedding est encore dans la base : "Attends, je crois que t'avais dit un truc là-dessus, mais j'ai plus les détails." → honnêteté + humanité

**Ce que l'utilisateur NE VOIT PAS :**
- L'embedding est toujours dans la base vectorielle
- Le graphe sémantique a conservé les arêtes (même si les nœuds ont un poids faible)
- La vision du monde a intégré l'information dans sa synthèse (même si le fragment source est "oublié")

### 4.2 Le "Rappel" — Re-learning Effect

```
Utilisateur : "Tu te souviens quand je t'ai parlé de mon projet de boulangerie ?"

SI weight > 0.1 (fragment encore accessible) :
  Delirium : "Ouais, le truc avec le pain au levain et le local à Tarbes.
  T'en es où ?"

SI weight < 0.1 mais > 0.01 (fragment faible) :
  Delirium : "Le projet de boulangerie... oui ça me dit quelque chose.
  C'était quoi exactement ?"
  → vector search retrouve le fragment → RS restauré → weight remonte

SI weight < 0.01 (fragment "oublié") :
  Delirium : "Boulangerie ? J'ai plus ça en tête. Raconte."
  → vector search retrouve quand même l'embedding (SS intacte)
  → le fragment est "re-découvert" → RS restauré
  → Delirium peut dire au message suivant : "Ah attends, ça me revient —
  t'avais parlé d'un local en février."
```

### 4.3 L'Oubli Intentionnel de l'Utilisateur

L'utilisateur peut DEMANDER d'oublier :
- "Oublie ce que je t'ai dit sur Marie" → suppression du fragment (SS ET RS → 0)
- "Oublie tout" → suppression complète (RGPD droit à l'effacement)

**Distinction critique :**
- **Oubli sélectif automatique** = RS decay (adaptatif, le fragment reste en base)
- **Suppression demandée par l'utilisateur** = suppression réelle (RGPD, le fragment est détruit)
- **Suppression RGPD formelle** = tout est détruit, y compris logs, embeddings, graphe

---

## 5. Oubli et Imperfection de la Persona

L'oubli est un des mécanismes de la **fiabilité intentionnellement imparfaite** (70-85%). Mais ce n'est pas un oubli aléatoire — c'est un oubli STRUCTURÉ par la théorie de Bjork.

### 5.1 Ce que Delirium "oublie" naturellement
- Les détails factuels pas réactivés (nom du chat de ta cousine mentionné une fois en mars)
- Les plaintes ponctuelles sans pattern (une seule mention d'un collègue pénible)
- Les conversations banales (intensité = "banal" dans le gradient de réponse)

### 5.2 Ce que Delirium n'oublie JAMAIS
- Les corrélations confirmées (SS haute car multi-réactivées)
- Les détections de danger (logs obligatoires)
- Les thèmes récurrents (réactivation = RS haute)
- Les boucles cognitives détectées (données S2 critiques)
- L'archétype et la persona (données structurelles)

### 5.3 Ce que Delirium oublie "exprès" (fiabilité 70-85%)
- Un anniversaire mentionné une fois → rappel avec 1 jour de retard
- Un détail logistique → "J'avais noté un truc pour toi mais j'ai oublié quoi"
- Ce n'est PAS de l'oubli Bjork (RS decay) — c'est de l'imperfection de persona (aléa contrôlé ∼10-15%)

---

## 6. Contradiction Identifiée et Résolue

### Contradiction : "Tout est chiffré et conservé" vs. "Oubli sélectif"

Les exigences de sécurité disent : "Logs d'exécution TOUJOURS conservés." L'oubli sélectif dit : "Les fragments peuvent être oubliés."

**Résolution :** Ce ne sont pas les mêmes données.
- Les **logs d'exécution** (décisions S1/S2, transitions d'état, détections) sont CONSERVÉS — c'est la traçabilité légale
- Les **fragments conversationnels** (ce que l'utilisateur a dit) subissent le decay de RS — c'est la mémoire vivante
- La **suppression utilisateur** (RGPD) efface TOUT y compris les logs (sauf danger N3 en conservation légale)

### Contradiction : "Vision du monde intègre tout" vs. "Oubli sélectif"

La vision du monde (couche 4) synthétise périodiquement TOUS les fragments, y compris ceux à faible weight. Donc la vision "se souvient" de ce que Delirium a "oublié".

**Résolution :** C'est exactement le mécanisme SS/RS de Bjork. La vision du monde = SS. Le retrieval quotidien = RS. Tu ne te souviens pas de l'adresse de ton enfance (RS basse) mais si on te la montre, tu la reconnais (SS haute). La vision du monde est la SS de Delirium — elle sait, même si elle ne peut pas accéder au détail.

---

## 7. Paramètres à Calibrer

| Paramètre | Valeur par défaut | Unité | Note |
|---|---|---|---|
| half_life_normal | 90 | jours | [NC] Demi-vie mode normal |
| half_life_minimal | 30 | jours | [NC] Demi-vie mode minimaliste |
| retrieval_threshold | 0.1 | - | [NC] Seuil en dessous duquel le fragment n'est pas récupéré |
| forget_threshold | 0.01 | - | [NC] Seuil en dessous duquel le fragment est marqué "oublié" |
| reactivation_boost | 0.3 | - | [NC] Augmentation du weight quand le sujet est mentionné |
| imperfection_rate | 0.12 | - | [NC] Probabilité d'oubli intentionnel (persona) |
| vision_resynth_interval | 10 | sessions | [NC] Fréquence de re-synthèse de la vision du monde |

---

## 8. Références

- Bjork, R.A. & Bjork, E.L. (1992). A new theory of disuse and an old theory of stimulus fluctuation. In Healy et al. (Eds.), From Learning Processes to Cognitive Processes, Vol. 2, pp. 35-67.
- Bjork, R.A. (2011). On the symbiosis of learning, remembering, and forgetting. Psychology Press.
- Ebbinghaus, H. (1885). Memory: A contribution to experimental psychology.
- Murre, J.M. & Dros, J. (2015). Replication and Analysis of Ebbinghaus' Forgetting Curve. PLOS ONE.
- Anderson, M.C., Bjork, R.A. & Bjork, E.L. (1994). Retrieval-induced forgetting. J. Experimental Psychology.
- Luria, A.R. (1968). The Mind of a Mnemonist. — Le cas Shereshevsky.
