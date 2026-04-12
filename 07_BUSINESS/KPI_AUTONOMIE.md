# KPI d'Autonomie — Remplacement des KPI d'Engagement

**Date :** 12 avril 2026
**Déclencheur :** Critique GPT-5.4 Pro — "tu reconstruis le même moteur d'engagement avec une philosophie plus noble"

---

## Le Problème

Les KPI du MVP_SPEC mesurent l'ENGAGEMENT :
- Rétention J7 > 40%
- Rétention J30 > 20%
- NPS > 30
- Durée de session

Ce sont les métriques de Meta, pas de Delirium. Si Delirium réussit, l'utilisateur devrait avoir MOINS besoin de l'app au fil du temps, pas plus.

---

## Nouveaux KPI — Mesurer l'Autonomie

### KPI Primaires (le produit marche si...)

| KPI | Mesure | Cible MVP | Pourquoi |
|---|---|---|---|
| **Time-to-first-insight** | Temps entre le 1er message et le 1er "moment eurêka" rapporté ou détecté | < 14 jours | La promesse est "retrouver des idées perdues" |
| **Collision engagement rate** | % des collisions Cold Weaver qui déclenchent une conversation | > 30% | Les collisions sont le cœur du produit |
| **Idée maturée** | Nombre d'idées passées de H (hypothèse) à C+ (confirmée) par utilisateur/mois | > 1 | L'utilisateur construit du sens |
| **Partage spontané** | % d'utilisateurs qui partagent une idée avec un ami (pré-OmniArxiv) | > 10% | Le passage de consommateur à générateur |

### KPI Secondaires (la relation fonctionne si...)

| KPI | Mesure | Cible | Pourquoi |
|---|---|---|---|
| **Correction profilage** | % des premiers messages qui déclenchent une correction spontanée | > 70% | L'onboarding marche |
| **Running gags actifs** | Nombre moyen de gags co-construits par utilisateur | > 1 après 1 mois | La relation est vivante |
| **Challenge acceptance** | % des challenges Delirium acceptés vs ignorés | > 40% | L'utilisateur ne veut pas de la sycophantie |
| **Injection rebond** | % des injections latérales qui déclenchent un échange | > 30% | L'utilisateur est ouvert |

### Anti-KPI (le produit échoue si...)

| Anti-KPI | Seuil d'alerte | Action |
|---|---|---|
| Durée de session moyenne > 45 min | Alerte | L'utilisateur utilise Delirium comme distraction |
| Messages/jour > 20 | Alerte | Dépendance potentielle |
| Corrélation durée ↑ et bien-être ↓ | Alerte | L'app fait du mal |
| 0 partages après 3 mois | Réflexion | L'utilisateur ne produit rien |

### Le KPI Ultime (long terme)

**Taux de graduation vers OmniArxiv** — % des utilisateurs qui passent de consommateur à générateur de connaissance. C'est la seule métrique qui prouve que Delirium a réussi sa mission.

---

## Ce qui change dans le MVP_SPEC

Remplacer :
```
Rétention J7 > 40%
Rétention J30 > 20%
NPS > 30
```

Par :
```
Time-to-first-insight < 14 jours
Collision engagement > 30%
Au moins 1 idée maturée/mois/utilisateur
Au moins 10% de partages spontanés
ANTI-KPI : sessions > 45 min < 10% des utilisateurs
```
