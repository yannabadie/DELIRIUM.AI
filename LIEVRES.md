# Lièvres Levés — Questions Ouvertes et Points de Vigilance

**Date :** 11-12 avril 2026
**Statut :** En cours de résolution

---

## FORMALISME

### L1 — 20 paramètres non calibrés
Le formalisme Delirium v0.1 a 20 paramètres non calibrés (δ, τ_ref, α_B, θ_s, θ_f, etc.). Sans calibration, le modèle peut expliquer n'importe quoi a posteriori. **Action requise :** analyse de sensibilité sur les seuils + données réelles pour calibrer.

### L2 — L'état B (biais enfoui) n'a pas d'équivalent AGM
C'est la contribution la plus originale du modèle. Mais elle n'est pas prouvée formellement. La piste Paraconsistent Belief Revision (LFI) existe mais n'a pas été explorée. **Risque :** si un revieweur académique challenge, il faut pouvoir répondre.

### L3 — Le sycophancy_score est défini mais pas validé
La définition opérationnelle (NLI + détection sources + contre-arguments) est raisonnable. Mais aucun corpus de test n'existe pour valider que ça détecte vraiment la sycophantie. **Action requise :** construire un petit dataset annoté.

### L4 — Le collision_score (Sweet Spot) est ancré dans SerenQA mais pas testé
La formule RNS est raisonnable. Les poids (0.3/0.3/0.4) sont arbitraires. **Action requise :** tester avec des paires fragment/source réelles.

---

## COMPORTEMENT

### L5 — Le ton "franchement direct" est un risque produit — [RÉSOLU 12/04/2026]
**Résolution :** Le ton doit être amical et franc, les mots familiers, et s'adapter aux circonstances et au profil utilisateur. Pas de mode "poli" séparé — c'est le même Delirium qui calibre via la variable H et le registre détecté. Le ton est une conséquence de la relation, pas un paramètre fixe.

### L6 — La détection du "mode ouvert vs. défensif" — [RÉSOLU 12/04/2026]
**Résolu :** PsyFIRE framework (2026) + marqueurs de défensivité verbale (Ridgway 2024). Score de défensivité via 6 marqueurs textuels (déni, méta-commentaires, réponses désinvoltes, omissions, externalisation, changement de sujet). Voir `04_FORMALISME/DETECTION_DEFENSIVITE.md`.

### L7 — Les "tendances comportementales inconscientes en nombre limité" — [RÉSOLU 12/04/2026]
**Résolu :** L'Interpersonal Circumplex (IPC, Leary 1957, Wiggins 1979) fournit exactement ce cadre — 2 axes (agency/communion), 8 octants, 60+ ans de validation. La séduction = blend PA-NO-BC dans le circumplex. Le principe de complémentarité explique la reproduction des patterns. Voir `04_FORMALISME/CIRCUMPLEX_INTERPERSONNEL.md`.

### L8 — L'archétype inversé par invitation — [RÉSOLU 12/04/2026]
**Résolution :** C'est à celui qui envoie l'invitation de décider si la description est visible (signée) ou anonyme. L'invité consent à l'app, pas à la description tierce. Le consentement à l'app couvre l'utilisation de données d'onboarding.

---

## JURIDIQUE

### L9 — Classification "haut risque" AI Act — incertitude
Le CDC dit "probablement haut risque". Mais c'est une interprétation. La classification définitive dépend de l'autorité nationale. **Action requise :** consultation juridique spécialisée AI Act avant MVP.

### L10 — Le contact ICE sans consentement au moment T
Le protocole danger N3 prévoit de notifier le contact ICE sans consentement de l'utilisateur au moment de la crise. Le consentement a été donné à l'inscription. **Zone grise RGPD.**

### L11 — Données émotionnelles = données sensibles RGPD ?
Le S2 analyse des émotions et construit des profils psychologiques. **Question :** le consentement onboarding suffit-il, ou faut-il un consentement spécifique ?

---

## TECHNIQUE

### L12 — Le budget compute "1 appel LLM/jour" pour la vie autonome
**Alternative :** templates + variables, avec appel LLM uniquement pour le contenu Cold Weaver.

### L13 — Le Cold Weaver à l'échelle
**Action requise :** benchmark de scalabilité avant MVP.

### L14 — Whisper embarqué vs. cloud
**Alternative :** STT cloud avec transit chiffré + purge immédiate. Mais ça contredit le "local-first".

---

## PRODUIT

### L15 — Le Non-BlocNote habité est brillant mais complexe à implémenter
**Risque :** MVP retardé par la complexité UI.

### L16 — La vision OmniArxiv est un deuxième produit
**Recommandation :** ne pas en parler dans le MVP. Le mentionner dans la vision mais pas dans le CDC.

### L17 — Le modèle économique "se rendre inutile" — [RÉSOLU 12/04/2026]
**Résolution :** Le paradoxe était mal posé. L'utilisateur autonome ne PART PAS — il ÉVOLUE vers OmniArxiv. Le jardin personnel devient un jardin collectif. L'utilisateur passe de consommateur à générateur de connaissance. Le produit change de forme (app personnelle → plateforme collective), pas de valeur. Le churn par succès est un FEATURE, pas un bug — il alimente la prochaine couche du produit.

### L18 — La "pub absurdiste" comme parodie pose un risque juridique
**Recommandation :** utiliser systématiquement des marques fictives ("DéliTendre") sauf si avis juridique confirme la liberté de parodie.

---

## RECHERCHE MANQUANTE

### L19 — Archétype inversé comme mécanisme de profilage — [PARTIELLEMENT RÉSOLU 12/04/2026]
Gap de recherche confirmé. Ancré dans la littérature sur les mesures implicites (IAT, AMP, SMP) et le biais de désirabilité sociale. Protocole expérimental proposé (N=100-200, 3 groupes). Voir `04_FORMALISME/ARCHETYPE_INVERSE_PROTOCOLE.md`.

### L20 — Psycho/socio non-occidentale absente
**Action :** recherche ciblée.

### L21 — Companion AI — extraction formelle des patterns de jeu vidéo — [RÉSOLU 12/04/2026]
**Résolu :** 8 patterns extraits de BG3/Mass Effect/Witcher 3 (accumulateur d'approbation, valeurs propres, seuils à événements, retrait, évolution morale, présence contextuelle, mémoire narrative, quêtes personnelles). 2 inversions clés : complémentarité → adjacence, fiabilité parfaite → imperfection intentionnelle. Voir `00_VISION/COMPANION_AI_PATTERNS.md`.

---

## RÉSUMÉ

| # | Statut | Date |
|---|---|---|
| L1-L4 | Ouvert | — |
| L5 | **RÉSOLU** | 12/04/2026 |
| L6 | **RÉSOLU** | 12/04/2026 |
| L7 | **RÉSOLU** | 12/04/2026 |
| L8 | **RÉSOLU** | 12/04/2026 |
| L9-L11 | Ouvert (juridique) | — |
| L12-L14 | Ouvert (technique) | — |
| L15-L16 | Ouvert (produit) | — |
| L17 | **RÉSOLU** | 12/04/2026 |
| L18 | Ouvert (juridique) | — |
| L19 | **Partiel** | 12/04/2026 |
| L20 | Ouvert (recherche) | — |
| L21 | **RÉSOLU** | 12/04/2026 |

**8 résolus / 21 total + 3 décisions de design + 5 formalisations majeures (fanfaronade, oubli, bulle, sycophantie, retrait, running gags, vision du monde schema, tests adversariaux)**
