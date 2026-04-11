# Audit Formel du Formalisme OIDA V4.2 — Application Delirium AI

**Version :** 1.0 | **Date :** 11 avril 2026
**Objectif :** Évaluer rigoureusement chaque composant du formalisme OIDA V4.2, identifier les failles, mapper vers les cadres formels existants, et produire un glossaire commun auditable.
**Norme de référence :** Bonnes pratiques en spécification formelle (IEEE Formal Methods, B-Method, Z-Notation, AGM Belief Revision Theory)

---

## PARTIE A — AUDIT DU FORMALISME V4.2

### Critères d'Audit

Pour chaque composant, on évalue :

| Critère | Symbole | Signification |
|---|---|---|
| **Définition opérationnelle** | DEF | Le composant est-il défini de façon mesurable par un algorithme ? |
| **Implémentation** | IMP | Le composant est-il implémenté dans analyzer.py ? |
| **Calibration** | CAL | Les paramètres sont-ils calibrés ou au moins bornés empiriquement ? |
| **Testabilité** | TST | Existe-t-il un test qui valide le comportement du composant ? |
| **Ancrage théorique** | ANC | Le composant est-il ancré dans un cadre formel existant reconnu ? |

Notation : ✅ satisfait, ⚠️ partiel, ❌ non satisfait

---

### Matrice d'Audit

| Composant | DEF | IMP | CAL | TST | ANC | Verdict |
|---|---|---|---|---|---|---|
| **L_D** (treillis conceptuel) | ✅ | ❌ | N/A | ❌ | ✅ (FCA, Ganter & Wille 1999) | **DÉCORATIF** — défini formellement mais jamais utilisé |
| **G_N^D** (DAG dépendances) | ✅ | ✅ | N/A | ✅ | ✅ (théorie des graphes) | **SOLIDE** |
| **dom_D(i,j)** (dominance) | ✅ | ✅ | N/A | ✅ | ✅ (immediate_dominators, NetworkX) | **SOLIDE** |
| **N^D(T)** (comptage brut) | ⚠️ | ✅ | N/A | ✅ | ❌ | **FRAGILE** — conditions sémantiques non-opérationnelles |
| **uN_i** (machine 4 états) | ⚠️ | ✅ | ⚠️ | ✅ | ❌ → **devrait être AGM** | **À ANCRER** — voir §B.1 |
| **uDN_i** (trace cross-domaine) | ✅ | ❌ | N/A | ❌ | ⚠️ | **NON IMPLÉMENTÉ** |
| **N_stock** | ✅ | ✅ | N/A | ✅ | ❌ | **OK mais dépend de uN_i** |
| **B_load** | ✅ | ✅ | ⚠️ | ✅ | ❌ | **OK mais τ_ref non calibré** |
| **N_eff** | ✅ | ✅ | ⚠️ | ✅ | ❌ | **OK — composition de N_stock et B_load** |
| **Debt** | ✅ | ✅ | N/A | ✅ | ❌ | **OK — max(0, -N_eff)** |
| **Déclin exp. (δ)** | ✅ | ❌ | ❌ | ❌ | ✅ (mémoire exponentielle, Ebbinghaus) | **NON IMPLÉMENTÉ** mais ancré |
| **damage_i(T)** | ✅ | ✅ | ⚠️ | ✅ | ❌ | **OK mais τ_ref arbitraire** |
| **λ_H→B** | ✅ | ✅ | ⚠️ | ✅ | ❌ | **OK mais α_B, seuils arbitraires** |
| **Double-loop repair** | ✅ | ✅ | N/A | ✅ | ✅ (dominance, théorie des graphes) | **SOLIDE** |
| **C_stock / C_flow** | ✅ | ❌ | ❌ | ❌ | ✅ (Shannon, Frenken et al. 2007) | **NON IMPLÉMENTÉ** |
| **Spillovers ρ_ij** | ✅ | ❌ | ❌ | ❌ | ⚠️ | **NON IMPLÉMENTÉ** |
| **sim(D_j, D)** | ❌ | ❌ | ❌ | ❌ | ❌ | **NON DÉFINI** — proxy sans spécification |
| **M_IA** | ⚠️ | ❌ | ❌ | ❌ | ❌ | **NON IMPLÉMENTÉ, vague** |
| **SIA_eff** | ⚠️ | ❌ | ❌ | ❌ | ❌ | **NON IMPLÉMENTÉ** |
| **μ(τ,T)** | ✅ | ✅ | ❌ | ✅ | ⚠️ (Dell'Acqua et al.) | **OK mais input manuel** |
| **G_D** (ancrage) | ✅ | ✅ | ⚠️ | ✅ | ❌ | **OK — simplification dans le code** |
| **Q_obs** | ✅ | ✅ | ⚠️ | ✅ | ❌ | **OK — moyenne pondérée simple** |
| **V_IA** | ✅ | ✅ | ⚠️ | ✅ | ❌ | **OK — simplifié dans le code** |
| **H_sys** | ✅ | ✅ | ⚠️ | ✅ | ❌ | **OK** |
| **V_net** | ✅ | ✅ | N/A | ✅ | ❌ | **OK — V_IA - H_sys** |

---

### Synthèse de l'Audit

**SOLIDE (utilisable tel quel) :** 5 composants — G_N^D, dom_D, double-loop, N_eff, Debt

**OK AVEC RÉSERVES (utilisable si on accepte les paramètres non calibrés) :** 9 composants — N_stock, B_load, damage, λ_H→B, G_D, Q_obs, V_IA, H_sys, V_net

**À ANCRER (bon concept, mauvaise fondation) :** 1 composant — **uN_i** (voir §B.1)

**NON IMPLÉMENTÉ (papier seulement) :** 5 composants — L_D, uDN_i, C_stock/C_flow, spillovers, déclin exponentiel

**NON DÉFINI (trou béant) :** 3 composants — sim(D_j,D), M_IA, SIA_eff

**DÉCORATIF (notation sans substance) :** 1 composant — L_D (treillis)

---

## PARTIE B — FAILLES BÉANTES ET REMÉDIATION

### B.1 La Machine à 4 États et AGM

#### Le Problème
La machine {H, C⁺, E, B} est un opérateur de révision de croyances ad-hoc. La littérature formelle sur la révision de croyances existe depuis 1985 (AGM : Alchourrón, Gärdenfors, Makinson). Les postulats AGM définissent les propriétés qu'un opérateur de révision *rationnel* doit satisfaire. OIDA V4.2 ne vérifie ni ne cite ces postulats.

#### Ce que AGM apporte
Le cadre AGM définit trois opérations :
- **Expansion** (ajout sans vérification de cohérence) — analogue à H dans OIDA
- **Révision** (ajout avec maintien de cohérence) — analogue à H→C⁺ ou H→E
- **Contraction** (retrait d'une croyance) — analogue à la correction double-loop

Les postulats AGM garantissent le **changement minimal** : on ne modifie que ce qui est nécessaire pour intégrer la nouvelle information. Le double-loop d'OIDA fait quelque chose de similaire (propagation par dominance) mais sans prouver qu'il satisfait les postulats.

#### Remédiation
1. Vérifier si les transitions d'état {H→C⁺, H→E, H→B, B→E, B→C⁺} satisfont les postulats AGM (K*1 à K*6)
2. Si non, documenter quels postulats sont violés et pourquoi (c'est peut-être volontaire — le dommage en B n'a pas d'équivalent AGM direct)
3. Au minimum, citer AGM et positionner le modèle par rapport à ce cadre

#### Pour Delirium
La révision de croyances AGM est applicable si on formalise :
- L'ensemble de croyances K = graphe conceptuel de l'utilisateur
- L'input φ = nouveau fragment (conversation ou collision Cold Weaver)
- L'opérateur * = la machine à états adaptée

La théorie AGM itérée (Darwiche & Pearl 1997) traite des révisions répétées — exactement le cas Delirium (flux continu de fragments).

---

### B.2 Les Conditions de Comptage de N

#### Le Problème
N^D(T) = Σ 𝟙[id_inconnu ∧ pert_sys ∧ vision]. Les trois conditions sont sémantiques :
- "identification de la structure réelle du problème" — comment un algorithme décide-t-il ?
- "viabilité systémique" — par rapport à quel référentiel ?
- "discernement prospectif" — mesurable comment ?

Dans le code, le problème est contourné : les events sont déclarés qualifiants par construction dans les JSON d'input. C'est une tautologie.

#### Remédiation
Deux options :
1. **Abandonner le comptage conditionnel** et compter tous les fragments (N = nombre total). La qualité est portée par uN_i, pas par N.
2. **Opérationnaliser les conditions** via des métriques calculables : id_inconnu → novelty score (distance au centroïde du cluster le plus proche), pert_sys → impact score (nombre de connexions dans le graphe), vision → pas opérationalisable, abandonner.

Pour Delirium : option 1 est la plus honnête. Tout fragment entre dans le système. C'est uN_i qui fait le tri.

---

### B.3 sim(D_j, D) — Le Proxy Fantôme

#### Le Problème
sim() apparaît dans : spillovers (ρ_ij), D.N_adjacent, G_D (ancrage), C_stock/C_flow. Mais sim() n'est jamais défini. "Embeddings, descripteurs ou taxonomies" n'est pas une définition.

#### Remédiation
Choisir UNE définition et s'y tenir :

```
sim(D_j, D) = cosine_similarity(centroide(cluster_j), centroide(cluster_D))
```

Où les clusters sont issus d'un clustering (HDBSCAN, k-means) sur l'espace d'embedding des fragments. C'est calculable, reproductible, et ancré dans une métrique standard.

Pour Delirium : c'est la seule option viable puisque les "domaines" ne sont pas pré-définis.

---

### B.4 Les Seuils Arbitraires

#### Le Problème
- `confirm_threshold = 0.80`
- `bias_threshold = 0.45`
- `g < 0.60 and q >= 0.70` pour H→B

Aucun de ces seuils n'est justifié empiriquement. Changer un seuil de 0.05 modifie fondamentalement les résultats.

#### Remédiation
1. **Analyse de sensibilité obligatoire** : montrer que les résultats qualitatifs (divergence des profils, expert atrophié) sont robustes à des variations de ±20% des seuils
2. **Documentation explicite** : chaque seuil doit être accompagné de sa justification (empirique, heuristique, ou arbitraire) et de sa plage de validité estimée
3. Pour Delirium : les seuils doivent être traités comme des **hyperparamètres** à calibrer sur des données réelles, pas des constantes

---

### B.5 Tests Tautologiques

#### Le Problème
Les 3 scénarios JSON sont fabriqués pour produire les résultats attendus. Les tests vérifient que le code fait ce qu'il est censé faire, pas que le modèle capture correctement la réalité.

#### Remédiation
1. **Tests adversariaux** : construire des scénarios conçus pour faire échouer le modèle (edge cases, contradictions)
2. **Tests de propriétés** (property-based testing) : vérifier des invariants formels :
   - N_eff est monotone décroissant si seuls des B s'accumulent
   - double-loop repair préserve la structure du DAG
   - La dominance est transitive
3. **Validation croisée** : comparer les prédictions du modèle avec des observations réelles (même qualitatives)

---

## PARTIE C — GLOSSAIRE FORMEL COMMUN (OIDA + Delirium)

### Format

Chaque entrée suit le format :

```
TERME
  Symbole      : notation mathématique
  Type         : type formel (ℝ, ℕ, ensemble, graphe, machine à états, etc.)
  Bornes       : domaine de valeur
  Définition   : formule ou algorithme de calcul
  Dépendances  : variables dont il dépend
  Implémenté   : oui/non (référence code)
  Calibré      : oui/non/proxy
  Cadre formel : référence au cadre théorique existant
  Statut       : STABLE / FRAGILE / SPÉCULATIF / ABANDONNÉ
  Usage OIDA   : rôle dans OIDA V4.2
  Usage Delirium : rôle dans Delirium AI (ou N/A)
```

---

### G.01 — Fragment Cognitif (Delirium) / Expérience Qualifiante (OIDA)

```
FRAGMENT (Delirium) / EXPERIENCE N_i (OIDA)
  Symbole      : N_i (OIDA), f_i (Delirium)
  Type         : enregistrement structuré
  Bornes       : N/A
  Définition   :
    OIDA  : N_i = événement satisfaisant [id_inconnu ∧ pert_sys ∧ vision]
    Delirium : f_i = tout transcript capturé ou fragment importé (pas de filtre)
  Dépendances  : aucune (entrée brute)
  Implémenté   : oui (Event dans models.py / table message + aborted_inspiration)
  Calibré      : N/A
  Cadre formel : N/A
  Statut       : STABLE (Delirium), FRAGILE (OIDA — conditions non-opérationnelles)
  Usage OIDA   : unité de base du comptage N^D(T)
  Usage Delirium : unité de base du graphe conceptuel
  NOTE         : Dans Delirium, tous les fragments entrent. Le tri est fait par uN_i.
```

### G.02 — Hypothèse / État Épistémique

```
HYPOTHESE uN_i
  Symbole      : uN_i(T) = (s_i(T), v_i(T), a_i(T))
  Type         : triplet (machine à états × ℝ × {0,1})
  Bornes       : s ∈ {H, C+, E, B}, v ∈ [-1,1], a ∈ {0,1}
  Définition   :
    s = état de l'hypothèse
    v = valeur courante (déclin exponentiel si H, dommage si B)
    a = drapeau d'audit (marqué pour revue)
  Dépendances  : N_i, temps T
  Implémenté   : oui (PatternLedger dans analyzer.py — simplifié : state + value + reuse_count)
  Calibré      : ⚠️ (seuils de transition arbitraires)
  Cadre formel : ❌ DEVRAIT ÊTRE ANCRÉ DANS AGM (voir §B.1)
    Expansion AGM ≈ création en état H
    Révision AGM ≈ transition H→C+ ou H→E
    Contraction AGM ≈ double-loop repair
    État B = extension non-standard (pas d'équivalent AGM direct — 
             contribution potentielle du modèle)
  Statut       : À ANCRER
  Usage OIDA   : cœur du modèle — mesure de la qualité épistémique
  Usage Delirium : cœur du système — chaque fragment est un uN_i porté par la machine
```

### G.03 — États de la Machine

```
ÉTAT H (Hypothèse active)
  Définition   : croyance non confirmée, en déclin naturel
  Transition → C+ : si grounding ≥ confirm_threshold ET q ≥ 0.60 (OIDA)
                    si collision_score > seuil ET user rebondit (Delirium)
  Transition → E  : si invalidation explicite (OIDA) ou sparring réussi (Delirium)
  Transition → B  : si λ_H→B ≥ bias_threshold ET faible grounding ET q élevé
  Déclin          : v(T) = v(t_0) · exp(-δ(T-t_0))
  Cadre formel    : Expansion AGM = ajout en H ; déclin ≈ oubli (non standard AGM)

ÉTAT C+ (Confirmé)
  Définition   : croyance validée par confrontation au réel
  Transition   : stable (pas de sortie sauf double-loop)
  Contribution : +1 à N_stock
  Cadre formel : Résultat d'une révision AGM réussie

ÉTAT E (Éliminé)
  Définition   : croyance reconnue comme fausse
  Transition   : stable
  Contribution : 0
  Cadre formel : Contraction AGM

ÉTAT B (Biais enfoui)
  Définition   : croyance adoptée sans validation, traitée comme savoir
  Transition → E ou C+ : possible via double-loop (conditions strictes)
  Contribution : damage_i(T) négatif sur B_load
  Cadre formel : ❌ PAS D'ÉQUIVALENT AGM DIRECT
    C'est la contribution la plus originale d'OIDA : la notion qu'une
    croyance peut sembler validée (q élevé) tout en étant structurellement
    fausse. AGM ne modélise pas ce cas.
    Piste : Paraconsistent Belief Revision (LFI) — logiques qui tolèrent
    la contradiction sans trivialisation (cf. arXiv:2412.06117)
```

### G.04 — Stock Net Signé

```
N_EFF (Stock net signé)
  Symbole      : N_eff^D(T)
  Type         : ℝ (peut être négatif)
  Bornes       : ]-∞, +∞[
  Définition   : N_eff = N_stock - B_load
    N_stock = Σ(1 si s_i=C+) + Σ(v_i si s_i=H)
    B_load = Σ damage_i(T) pour s_i=B
  Dépendances  : uN_i pour tout i
  Implémenté   : oui
  Calibré      : ⚠️ (dépend de τ_ref pour damage)
  Cadre formel : ❌ pas d'ancrage direct
    Piste : Spohn's Ranking Theory — ordonnancement numérique des croyances
    avec degrés de plausibilité, compatible avec révision itérée
  Statut       : STABLE (calcul), FRAGILE (calibration)
```

### G.05 — Graphe de Dépendance et Dominance

```
G_N^D (Graphe de dépendance des expériences)
  Symbole      : G_N^D(T) = (V_D(T), E_c(T), E_s(T))
  Type         : graphe orienté acyclique (DAG)
  Définition   :
    V = ensemble des fragments/expériences
    E_c = arêtes constitutives (nécessaires)
    E_s = arêtes supportives (aidantes)
  Implémenté   : oui (NetworkX DiGraph)
  Cadre formel : ✅ théorie des graphes standard
  Statut       : SOLIDE

dom_D(i,j) (Dominance)
  Définition   : i domine j si tout chemin constitutif vers j passe par i
  Implémenté   : oui (nx.algorithms.dominance.immediate_dominators)
  Cadre formel : ✅ dominance dans les DAG (Lengauer-Tarjan)
  Statut       : SOLIDE

DOUBLE-LOOP REPAIR
  Définition   :
    Input : nœud racine i à corriger
    Output : descendants dominés → reopen (s←H, a←1)
             descendants influencés → audit (a←1)
  Implémenté   : oui (double_loop_repair dans analyzer.py)
  Cadre formel : ✅ propagation par dominance + contraction AGM
  Statut       : SOLIDE
```

### G.06 — Déclin et Dommage

```
DÉCLIN EXPONENTIEL
  Symbole      : v_i(T) = v_i(t_0) · exp(-δ(T-t_0))
  Type         : ℝ → ℝ
  Paramètre    : δ > 0 (NON CALIBRÉ)
  Cadre formel : ✅ courbe d'oubli d'Ebbinghaus (1885) — exponentielle décroissante
    Référence : Ebbinghaus, H. (1885). Über das Gedächtnis.
    Murre & Dros (2015) confirment la forme exponentielle.
  Statut       : STABLE (forme), FRAGILE (calibration de δ)

DOMMAGE EN ÉTAT B
  Symbole      : damage_i(T) = |v_i| · usage_i · log(1 + (T-t_B)/τ_ref)
  Type         : ℝ≥0
  Paramètre    : τ_ref > 0 (NON CALIBRÉ)
  Cadre formel : ❌ pas d'ancrage direct
    La forme log(1+t/τ) est raisonnable (croissance sous-linéaire)
    mais le choix du log n'est pas justifié vs. une racine carrée ou linéaire
  Statut       : FRAGILE
```

### G.07 — Diversité Cross-Domaine

```
C_STOCK (Variété liée accumulée)
  Symbole      : C_stock(T) = H_norm(p^stock)
  Type         : [0,1]
  Définition   : entropie de Shannon normalisée sur la distribution des domaines co-mobilisés
  Implémenté   : ❌
  Cadre formel : ✅ Shannon (1948), Frenken et al. (2007) — related variety
  Statut       : NON IMPLÉMENTÉ mais ancré

C_FLOW (Plasticité récente)
  Symbole      : C_flow(T) = H_norm(p^flow) avec pondération de récence
  Type         : [0,1]
  Implémenté   : ❌
  Cadre formel : ✅ Shannon + amortissement exponentiel
  Statut       : NON IMPLÉMENTÉ mais ancré
```

### G.08 — Variable H (Humour) — DELIRIUM UNIQUEMENT

```
H (Humour / qualité communicationnelle)
  Symbole      : H(T)
  Type         : ℝ
  Bornes       : [-1, 1]
  Définition   : variable dynamique pilotant le ton de la persona
    H > 0 : exploration audacieuse, provocation, humour noir
    H = 0 : neutre, écoute
    H < 0 : retenue, empathie, pas de blagues
  Dépendances  : user_emotional_state, conversation_intensity, time_context, s2_analysis
  Implémenté   : ❌ (à implémenter)
  Calibré      : ❌ (à calibrer sur données réelles)
  Cadre formel : ❌ PAS D'ANCRAGE DIRECT
    Piste 1 : Martin et al. (2003) — Humor Styles Questionnaire (HSQ),
              4 styles {affiliatif, auto-valorisant, agressif, auto-dépréciatif}
              → H pourrait être un composite de ces 4 dimensions
    Piste 2 : Opinion Dynamics (Flache et al. 2017) — modèles ABM d'attitudes
              avec fonctions d'assimilation/répulsion → la persona Delirium
              interagit avec l'utilisateur comme un agent dans un modèle d'opinion
    Piste 3 : SLAP framework (O'Brien) — Surprise, Light-heartedness,
              Absurdity, Perspective → H comme fonction de ces 4 composantes
  Statut       : SPÉCULATIF — nécessite formalisation
  NOTE         : H est le pendant communicationnel de uDN (qualité métacognitive).
                 Les deux sont contextuels, bornés, et portés par la machine.
```

### G.09 — Persona

```
PERSONA(T) (Vecteur de personnage)
  Symbole      : Persona(T) = (H, listen, creativity, confrontation, empathy, fatigue)
  Type         : ℝ⁶
  Bornes       : chaque composante ∈ [0,1] sauf H ∈ [-1,1]
  Définition   : Persona(T+1) = f(Persona(T), user_state(T), context(T), s2(T))
  Implémenté   : ❌
  Calibré      : ❌
  Cadre formel : ❌ PAS D'ANCRAGE DIRECT
    Piste 1 : BDI Architecture (Belief-Desire-Intention) — Rao & Georgeff 1995
              → la persona comme agent BDI avec beliefs (archétype), desires
              (objectif communicationnel), intentions (ton choisi)
    Piste 2 : AgentSpeak(L) — formalisation computationnelle de BDI
              (cf. IEEE Xplore, Bordini et al. 2007)
  Statut       : SPÉCULATIF
```

### G.10 — Collision Sémantique

```
COLLISION_SCORE
  Symbole      : cs(f_user, v_world)
  Type         : ℝ
  Bornes       : [0, 1]
  Définition   : 
    cs = w1·semantic_distance + w2·fragment_weight + w3·source_recency + w4·novelty
    sweet_spot : seuil_min < cosine_sim < seuil_max
    (trop similaire = pas surprenant, trop distant = pas pertinent)
  Implémenté   : ❌
  Calibré      : ❌ (w1-w4 et seuils à calibrer)
  Cadre formel : ⚠️
    Piste 1 : SerenQA (Wang et al. 2025, arXiv:2511.12472) — métrique de
              sérendipité basée sur relevance, novelty, surprise
    Piste 2 : Liu et al. 2026 (arXiv:2603.19087) — distance sémantique KL
              divergence entre concepts comme prédicteur d'originalité
  Statut       : SPÉCULATIF — nécessite ancrage dans SerenQA ou équivalent
```

### G.11 — Sycophancy Score

```
SYCOPHANCY_SCORE
  Symbole      : syc(response_ai, fragment_user)
  Type         : ℝ
  Bornes       : [0, 1]
  Définition   : NON DÉFINI FORMELLEMENT
    Intuition : mesure à quel point une réponse IA valide mollement sans
                challenger, sourcer, ou contredire
  Implémenté   : ❌
  Calibré      : ❌
  Cadre formel : ❌ PAS D'ANCRAGE
    Piste : Sharma et al. (2023) "Towards Understanding Sycophancy in LMs"
            — définition formelle de la sycophantie comme alignement
            excessif avec les préférences exprimées de l'utilisateur
    Piste 2 : classifier binaire (sycophante/non-sycophante) entraîné sur
              des paires (prompt, réponse) annotées
  Statut       : SPÉCULATIF — nécessite définition opérationnelle
```

### G.12 — Friction Sémantique

```
FRICTION SÉMANTIQUE
  Symbole      : fric(msg_user, msg_ai)
  Type         : ℝ
  Bornes       : [0, 1]  (0 = parfaite compréhension, 1 = incompréhension totale)
  Définition   : fric = 1 - cosine_similarity(embed(msg_user), embed(msg_ai))
  Implémenté   : ❌ (trivial à implémenter)
  Calibré      : ⚠️ (seuil de détection à calibrer)
  Cadre formel : ✅ distance cosinus dans un espace d'embedding (métrique standard)
  Statut       : STABLE (calcul), FRAGILE (interprétation)
  NOTE         : NE REMPLACE PAS Shannon. C'est une métrique de distance, pas une
                 entropie. Ne pas prétendre une substitution formelle.
```

---

## PARTIE D — CADRES FORMELS À INTÉGRER

### D.1 AGM Belief Revision (Alchourrón, Gärdenfors, Makinson 1985)
**Quoi :** Théorie standard de la révision de croyances. Postulats de rationalité pour les opérations d'expansion, révision, contraction.
**Pertinence :** Ancrage théorique pour la machine à 4 états.
**Action :** Vérifier si les transitions OIDA satisfont les postulats K*1 à K*6. Documenter les écarts.
**Référence :** Alchourrón, C.E., Gärdenfors, P., Makinson, D. (1985). "On the logic of theory change: Partial meet contraction and revision functions." J. Symbolic Logic 50(2).

### D.2 Spohn's Ranking Theory (1988)
**Quoi :** Ordonnancement numérique des croyances avec degrés de plausibilité. Compatible avec révision itérée.
**Pertinence :** Fournit un cadre pour le N_eff signé — les rangs peuvent être négatifs (discroyance).
**Action :** Explorer si les ranks de Spohn correspondent à v_i dans uN_i.
**Référence :** Spohn, W. (1988). "Ordinal conditional functions: A dynamic theory of epistemic states."

### D.3 Opinion Dynamics ABM (Flache et al. 2017)
**Quoi :** Modèles computationnels de dynamique d'opinions dans des systèmes multi-agents.
**Pertinence :** Delirium est un système à 2 agents (humain + IA) avec une dynamique d'attitudes.
**Action :** Formaliser l'interaction sparring comme une paire (assimilation, répulsion) dans le cadre opinion dynamics.
**Référence :** Flache, A. et al. (2017). "Models of social influence: Towards the next frontiers." JASSS.

### D.4 BDI Architecture (Rao & Georgeff 1995)
**Quoi :** Architecture Belief-Desire-Intention pour les agents autonomes.
**Pertinence :** La persona Delirium est un agent BDI — beliefs (archétype), desires (objectif communicationnel), intentions (ton).
**Action :** Formaliser Persona(T) comme un agent BDI.
**Référence :** Rao, A.S. & Georgeff, M.P. (1995). "BDI Agents: From Theory to Practice." ICMAS.

### D.5 Ebbinghaus Forgetting Curve (1885, confirmé 2015)
**Quoi :** Le déclin mémoriel suit une exponentielle décroissante.
**Pertinence :** Ancrage direct pour le déclin en état H et l'oubli sélectif.
**Action :** Utiliser les constantes de déclin empiriques de Murre & Dros (2015) pour calibrer δ.
**Référence :** Murre, J.M.J. & Dros, J. (2015). "Replication and Analysis of Ebbinghaus' Forgetting Curve." PLOS ONE.

### D.6 SerenQA Framework (Wang et al. 2025)
**Quoi :** Métrique formelle de sérendipité basée sur relevance, novelty, surprise.
**Pertinence :** Ancrage direct pour le collision_score du Cold Weaver.
**Action :** Adopter ou adapter la métrique RNS de SerenQA.
**Référence :** Wang, M. et al. (2025). arXiv:2511.12472.

---

## PARTIE E — RECOMMANDATIONS

### E.1 Pour OIDA V4.3 (le papier)
1. Citer et positionner par rapport à AGM
2. Citer Ebbinghaus/Murre pour le déclin exponentiel
3. Supprimer L_D (treillis) s'il n'est pas utilisé, ou l'implémenter
4. Remplacer sim(D_j,D) par une définition computationnelle unique
5. Ajouter une analyse de sensibilité sur les seuils
6. Ajouter des tests adversariaux

### E.2 Pour Delirium
1. Utiliser UNIQUEMENT les composants SOLIDES d'OIDA : G_N^D, dominance, double-loop, N_eff, Debt
2. Les composants FRAGILES (uN_i, damage, λ_H→B) sont utilisables mais les seuils doivent être documentés comme hyperparamètres
3. Les composants SPÉCULATIFS (H, Persona, collision_score, sycophancy_score) doivent être formalisés avant implémentation — les pistes D.1 à D.6 fournissent les cadres
4. Ne PAS prétendre que la friction sémantique remplace Shannon
5. Construire le glossaire AVANT le code — le vocabulaire commun est la priorité

### E.3 Matrice Finale

| Composant | OIDA V4.2 | Delirium | Statut |
|---|---|---|---|
| G_N^D + dominance + double-loop | ✅ | ✅ | **UTILISER TEL QUEL** |
| N_eff / Debt | ✅ | ✅ | **UTILISER TEL QUEL** |
| uN_i {H,C+,E,B} | ⚠️ | ⚠️ | **UTILISER + ANCRER DANS AGM** |
| Déclin exp. | ⚠️ | ✅ | **UTILISER + CALIBRER (Ebbinghaus)** |
| damage / B_load | ⚠️ | ⚠️ | **UTILISER + DOCUMENTER τ_ref** |
| λ_H→B | ⚠️ | Adapté (sycophancy) | **UTILISER + DÉFINIR sycophancy_score** |
| C_stock / C_flow | ❌ imp. | ✅ concept | **IMPLÉMENTER (Shannon, ancré)** |
| sim(D_j,D) | ❌ déf. | cosine(centroids) | **DÉFINIR UNE FOIS** |
| L_D (treillis) | ❌ util. | N/A | **ABANDONNER** |
| μ, M_IA, SIA_eff | ⚠️ | N/A | **ABANDONNER (Delirium)** |
| H (humour) | N/A | ⚠️ | **FORMALISER (BDI + HSQ + SLAP)** |
| Persona(T) | N/A | ⚠️ | **FORMALISER (BDI)** |
| collision_score | N/A | ⚠️ | **FORMALISER (SerenQA)** |
| friction sémantique | N/A | ✅ calcul | **UTILISER, NE PAS PRÉTENDRE = Shannon** |

---

*Ce document est la fondation du vocabulaire commun. Chaque développement ultérieur doit s'y référer. Toute variable ajoutée doit suivre le format du glossaire (§C).*
