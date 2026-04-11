# Formalisme Delirium v0.1 — Spécification Formelle

**Version :** 0.1 (Draft)
**Date :** 11 avril 2026
**Auteur :** Y. Abadie
**Base :** OIDA V4.2 (Abadie, 2026) — composants audités et corrigés
**Ancrage :** AGM Belief Revision, Ebbinghaus-Murre, Shannon, SerenQA, BDI
**Principe :** Rien n'est écrit ici qui ne soit soit (a) implémentable, soit (b) explicitement marqué comme ouvert

---

## 0. Conventions

- $f_i$ : fragment cognitif (unité de base)
- $T$ : temps discret (tick = interaction ou batch)
- $\sigma(z) = 1/(1+e^{-z})$ : fonction logistique
- $\cos(a,b)$ : similarité cosinus entre vecteurs
- $\text{embed}(x)$ : plongement vectoriel d'un texte $x$ (modèle fixé, ex: text-embedding-3-small)
- Tous les paramètres non calibrés sont marqués `[NC]`

---

## 1. Structures de Données

### 1.1 Fragment Cognitif $f_i$

Unité atomique du système. Tout ce qui entre dans Delirium est un fragment.

$$
f_i = (id_i, \text{content}_i, \text{source}_i, \text{emb}_i, t_i)
$$

- $id_i$ : identifiant unique
- $\text{content}_i$ : texte (transcript)
- $\text{source}_i \in \{\text{conversation}, \text{import\_chatgpt}, \text{import\_claude}, \text{import\_gemini}, \text{import\_copilot}\}$
- $\text{emb}_i = \text{embed}(\text{content}_i) \in \mathbb{R}^d$ (vecteur de dimension $d$, fixée par le modèle d'embedding)
- $t_i$ : timestamp de création

**Pas de filtre à l'entrée.** Tous les fragments entrent. Le tri est fait par l'état épistémique (§2).

### 1.2 Graphe Conceptuel $G(T)$

$$
G(T) = (V(T), E_c(T), E_s(T), E_w(T))
$$

- $V(T)$ : ensemble des fragments actifs (decay\_weight > seuil de purge)
- $E_c(T)$ : arêtes **constitutives** — $f_j$ dépend structurellement de $f_i$
  - Créées quand : l'utilisateur relie explicitement deux idées, ou le S2 détecte une dépendance logique
- $E_s(T)$ : arêtes **supportives** — $f_j$ est thématiquement proche de $f_i$
  - Créées quand : $\cos(\text{emb}_i, \text{emb}_j) > \theta_s$ `[NC: θ_s ≈ 0.7]`
- $E_w(T)$ : arêtes **de collision** — créées par le Cold Weaver
  - Créées quand : une collision est détectée entre un fragment et une source mondiale

**Type :** DAG pour $E_c$ (pas de cycles constitutifs). Graphe général pour $E_s$ et $E_w$.

**Ancrage :** Théorie des graphes standard. Dominance via Lengauer-Tarjan (NetworkX `immediate_dominators`).

### 1.3 Clusters Thématiques $\mathcal{K}(T)$

Les "domaines" de l'utilisateur ne sont pas pré-définis. Ils émergent du clustering.

$$
\mathcal{K}(T) = \text{HDBSCAN}(\{\text{emb}_i : f_i \in V(T)\})
$$

Chaque cluster $K_k$ représente un thème récurrent. La similarité inter-domaines est :

$$
\text{sim}(K_j, K_k) = \cos(\text{centroïde}(K_j), \text{centroïde}(K_k))
$$

**Ancrage :** HDBSCAN (Campello et al. 2013). Similarité cosinus entre centroïdes (métrique standard).

---

## 2. État Épistémique — Machine à États (corrigée)

### 2.1 Définition

Chaque fragment $f_i$ porte un état épistémique :

$$
\epsilon_i(T) = (s_i(T), v_i(T), a_i(T))
$$

- $s_i(T) \in \{H, C^+, E, B\}$ : état
- $v_i(T) \in [-1, 1]$ : valeur courante
- $a_i(T) \in \{0, 1\}$ : drapeau de revue

### 2.2 États

| État | Nom | Signification | Contribution à $N_{stock}$ |
|---|---|---|---|
| $H$ | Hypothèse | Croyance non confirmée, en déclin naturel | $+v_i(T)$ |
| $C^+$ | Confirmé | Croyance validée par confrontation au réel | $+1$ |
| $E$ | Éliminé | Croyance reconnue comme fausse | $0$ |
| $B$ | Biais enfoui | Croyance adoptée sans validation, traitée comme savoir | $-\text{damage}_i(T)$ via $B_{load}$ |

### 2.3 Positionnement AGM

La machine à états est un **opérateur de révision de croyances**.

| Opération AGM | Équivalent Delirium | Postulats satisfaits |
|---|---|---|
| Expansion $K + \phi$ | Création de $f_i$ en état $H$ | K*2 (la nouvelle croyance est dans le résultat) |
| Révision $K * \phi$ | Transition $H \to C^+$ ou $H \to E$ | K*1 (fermeture), K*3 (inclusion), K*5 (consistance) |
| Contraction $K - \phi$ | Double-loop repair | K*6 (récupération partielle via audit) |

**Extension non-standard (contribution originale) :** L'état $B$ n'a pas d'équivalent AGM. AGM suppose que l'agent est rationnel — il ne modélise pas l'adoption irrationnelle d'une croyance fausse. L'état $B$ modélise exactement ce phénomène : une croyance qui semble validée (haute qualité observable) mais qui est structurellement fausse.

**Piste formelle :** Paraconsistent Belief Revision (LFI) — logiques qui tolèrent la contradiction sans trivialisation. L'opérateur de consistance $\circ$ des LFI pourrait formaliser la distinction entre $C^+$ (consistant) et $B$ (inconsistant mais non détecté).

**TODO(formalisation) :** Prouver ou infirmer que les transitions satisfont les postulats AGM étendus. Documenter les violations intentionnelles.

### 2.4 Transitions

```
       ┌──────────────────────────────────────────┐
       │                                          │
       ▼                                          │
   ┌───────┐  confirmation    ┌───────┐           │
   │       │ ───────────────► │       │           │
   │   H   │                  │  C+   │           │
   │       │ ◄─── (rare) ──── │       │  double-loop
   └───┬───┘                  └───────┘           │
       │                                          │
       │ invalidation   ┌───────┐                 │
       ├───────────────► │       │                 │
       │                 │   E   │ ◄──── réouverture
       │                 │       │                 │
       │                 └───────┘                 │
       │                                          │
       │ adoption sans   ┌───────┐                │
       │ validation      │       │ ── correction ─┘
       └───────────────► │   B   │
                         │       │
                         └───────┘
```

#### T1 : Déclin naturel en $H$ (pas de transition, modification de $v_i$)

$$
v_i(T) = v_i(t_i) \cdot e^{-\delta (T - t_i^{last})}
$$

- $\delta > 0$ : constante de déclin `[NC]`
- $t_i^{last}$ : dernière activation (mention par l'utilisateur ou collision Cold Weaver)
- **Ancrage :** Ebbinghaus (1885), confirmé par Murre & Dros (2015, PLOS ONE). La forme exponentielle est empiriquement validée. δ calibrable via les constantes de Murre & Dros `[TODO(calibration)]`.
- **Purge :** Si $v_i(T) < v_{purge}$ `[NC: v_purge ≈ 0.01]`, le fragment est supprimé.
- **Réactivation :** Si l'utilisateur re-mentionne le thème ou si le Cold Weaver détecte une collision, $t_i^{last} \leftarrow T$ et $v_i \leftarrow \max(v_i, v_{react})$ `[NC: v_react ≈ 0.8]`.

#### T2 : Confirmation $H \to C^+$

**Condition :**

$$
s_i \leftarrow C^+ \quad \text{si} \quad \text{collision\_score}(f_i) > \theta_{confirm} \;\land\; \text{user\_engaged}(f_i) = \text{true}
$$

- $\text{collision\_score}$ : défini en §4
- $\text{user\_engaged}$ : l'utilisateur a rebondi sur la collision (pas un dismiss)
- $\theta_{confirm}$ `[NC: ≈ 0.6]`

**Différence avec OIDA V4.2 :** Dans OIDA, C+ requiert `grounding ≥ 0.80 AND q ≥ 0.60`. Ces seuils sont arbitraires et dépendent de variables d'input (completion, tests_pass) qui n'existent pas dans Delirium. Ici, la confirmation est déclenchée par une collision externe validée par l'engagement de l'utilisateur — ce qui est opérationnel et mesurable.

#### T3 : Invalidation $H \to E$

**Condition :**

$$
s_i \leftarrow E \quad \text{si} \quad \text{sparring\_invalidation}(f_i) = \text{true}
$$

- Le S1 (sparring) a factuellement contredit l'idée ET l'utilisateur a accepté la correction (pas de reformulation insistante)

**Détection :** Absence de pattern "abandon après résistance" (cf. §3.3). L'utilisateur change de sujet sans frustration.

#### T4 : Biais $H \to B$

**Condition :**

$$
\lambda_{H \to B,i}(T) = \alpha_B \cdot \text{syc}_i \cdot (1 - \text{anc}_i(T)) \cdot \text{reuse\_norm}(r_i)
$$

$$
s_i \leftarrow B \quad \text{si} \quad \lambda_{H \to B,i} > \theta_B \;\land\; v_i(T) > v_{min}
$$

Où :
- $\alpha_B > 0$ : intensité de bascule `[NC: ≈ 1.15, hérité OIDA]`
- $\text{syc}_i \in [0,1]$ : sycophancy score (§2.5)
- $\text{anc}_i(T) \in [0,1]$ : ancrage du fragment dans le graphe (proportion de voisins en $C^+$)
- $\text{reuse\_norm}(r) = \min(1, \ln(1+r) / \ln 6)$ : normalisation du comptage de réutilisation (héritée OIDA, implémentée)
- $\theta_B$ : seuil de bascule `[NC: ≈ 0.45, hérité OIDA]`
- $v_{min}$ : le fragment doit encore avoir de la valeur pour basculer (pas déjà en déclin terminal) `[NC: ≈ 0.2]`

#### T5 : Correction double-loop $B \to E$ ou $B \to H$

**Condition :** Identique à OIDA V4.2. Algorithme de propagation via dominance :

1. Nœud racine $i$ : $s_i \leftarrow E$ (ou $H$ si correction partielle)
2. Descendants dominés dans $G_c$ : $s_j \leftarrow H$, $a_j \leftarrow 1$
3. Descendants influencés (non dominés) : $a_j \leftarrow 1$ (audit)

**Ancrage :** Théorie des graphes (dominance immédiate). Implémentation existante validée par tests.

### 2.5 Sycophancy Score $\text{syc}_i$

**Définition opérationnelle :** Mesure à quel point les IA externes ont validé le fragment $f_i$ sans le challenger.

$$
\text{syc}_i = \frac{1}{|R_i|} \sum_{r \in R_i} \text{syc\_single}(f_i, r)
$$

Où $R_i$ est l'ensemble des réponses IA au fragment $f_i$ (importées depuis les historiques).

$$
\text{syc\_single}(f, r) = w_a \cdot \text{agreement}(f, r) + w_s \cdot (1 - \text{sourced}(r)) + w_c \cdot (1 - \text{challenged}(r))
$$

- $\text{agreement}(f, r) \in [0,1]$ : degré d'accord détecté (classifieur NLI : entailment score)
- $\text{sourced}(r) \in \{0, 1\}$ : la réponse contient-elle des sources/références ?
- $\text{challenged}(r) \in \{0, 1\}$ : la réponse contient-elle un contre-argument ?
- $w_a, w_s, w_c$ : poids `[NC: w_a=0.4, w_s=0.3, w_c=0.3]`

**Ancrage :** Sharma et al. (2023) "Towards Understanding Sycophancy in Language Models" — définition de la sycophantie comme alignement excessif. Le NLI (Natural Language Inference) est un classifieur standard (entailment/contradiction/neutral).

**Implémentable :** Oui, via un modèle NLI léger (ex: cross-encoder/nli-deberta-v3-small) + détection heuristique de sources et contre-arguments.

**Si pas d'import IA :** $\text{syc}_i = 0$ (pas de risque de biais externe détectable). Le risque H→B vient alors uniquement du manque d'ancrage.

---

## 3. Détection d'Inspirations Avortées

### 3.1 Friction Sémantique

$$
\text{fric}(m_u, m_a) = 1 - \cos(\text{embed}(m_u), \text{embed}(m_a))
$$

- $m_u$ : message utilisateur, $m_a$ : réponse IA
- **Candidat si** $\text{fric} > \theta_f$ `[NC: θ_f ≈ 0.6]`
- **Type :** Distance cosinus. **Ce n'est PAS une entropie.** Ne pas confondre avec Shannon.
- **Ancrage :** Métrique standard dans les espaces d'embedding.

### 3.2 Récurrence Latente

$$
\text{recur}(f_{new}, f_{old}) = \cos(\text{emb}_{new}, \text{emb}_{old})
$$

- **Candidat si** $\text{recur} > \theta_r$ `[NC: θ_r ≈ 0.7]` ET $\text{source}_{new} \neq \text{source}_{old}$
- **Ancrage :** Similarité cosinus cross-plateforme.

### 3.3 Abandon Après Résistance

Détection séquentielle dans une fenêtre glissante de $w$ messages `[NC: w=6]` :

$$
\text{abandon}(\text{window}) = \begin{cases}
1 & \text{si topic\_sim}(\text{window}[1:3]) > 0.8 \;\land\; \text{topic\_sim}(\text{window}[4:6]) < 0.3 \\
0 & \text{sinon}
\end{cases}
$$

- **Ancrage :** Heuristique. Pas d'ancrage formel fort — à valider empiriquement.

### 3.4 Surgissement Non Rebondi

Pour chaque concept $c$ introduit par l'IA mais ignoré par l'utilisateur dans les $n$ messages suivants `[NC: n=5]` :

$$
\text{dormant}(c) = \begin{cases}
\text{activé} & \text{si } \exists f_j \text{ ultérieur} : \cos(\text{embed}(c), \text{emb}_j) > \theta_d \; [\text{NC: } \theta_d \approx 0.6] \\
\text{inactif} & \text{sinon}
\end{cases}
$$

---

## 4. Cold Weaver — Collision Sémantique

### 4.1 Définition du Collision Score

Ancrage : SerenQA (Wang et al. 2025, arXiv:2511.12472) — métrique RNS (Relevance, Novelty, Surprise).

$$
\text{cs}(f_i, v_w) = \alpha_R \cdot R(f_i, v_w) + \alpha_N \cdot N(f_i, v_w) + \alpha_S \cdot S(f_i, v_w)
$$

Où $v_w$ est un vecteur de source mondiale (arXiv, GitHub, presse) :

$$
R(f_i, v_w) = \cos(\text{emb}_i, \text{emb}_w) \quad \text{(relevance)}
$$

$$
N(f_i, v_w) = 1 - \max_{f_j \in V(T)} \cos(\text{emb}_j, \text{emb}_w) \quad \text{(novelty pour l'utilisateur)}
$$

$$
S(f_i, v_w) = \begin{cases}
1 - |R - 0.5| \cdot 2 & \text{(surprise = sweet spot, max à R=0.5)}
\end{cases}
$$

- $\alpha_R, \alpha_N, \alpha_S$ : poids `[NC: α_R=0.3, α_N=0.3, α_S=0.4]`
- **Seuil de notification :** $\text{cs} > \theta_{cs}$ `[NC: θ_cs ≈ 0.5]`

**Justification du sweet spot :** Liu et al. (2026, arXiv:2603.19087) montrent que les combinaisons sémantiquement plus distantes produisent des idées plus originales. Mais trop distant = non pertinent. La fonction $S$ capture ce compromis.

---

## 5. Métriques Agrégées

### 5.1 Stock et Dette

$$
N_{stock}(T) = \sum_{i: s_i = C^+} 1 + \sum_{i: s_i = H} v_i(T)
$$

$$
B_{load}(T) = \sum_{i: s_i = B} \text{damage}_i(T)
$$

$$
\text{damage}_i(T) = |v_i| \cdot (1 + r_i) \cdot \ln\!\left(1 + \frac{T - t_{B,i}}{\tau_{ref}}\right)
$$

$$
N_{eff}(T) = N_{stock}(T) - B_{load}(T) \qquad \text{(peut être négatif)}
$$

$$
\text{Debt}(T) = \max(0, -N_{eff}(T))
$$

- $\tau_{ref}$ : inertie temporelle du dommage `[NC: ≈ 3.0, hérité OIDA]`

### 5.2 Diversité Cognitive

$$
p_k(T) = \frac{\sum_{i: K(i)=k} v_i(T) \cdot \mathbf{1}[s_i \in \{H, C^+\}]}{\sum_{i} v_i(T) \cdot \mathbf{1}[s_i \in \{H, C^+\}]}
$$

$$
C_{stock}(T) = \begin{cases}
-\frac{1}{\ln |\mathcal{K}|} \sum_k p_k \ln p_k & \text{si } |\mathcal{K}| \geq 2 \\
0 & \text{sinon}
\end{cases}
$$

- $K(i)$ : cluster de $f_i$
- **Ancrage :** Shannon (1948). Frenken et al. (2007) — related variety.
- $C_{flow}$ : identique mais avec pondération de récence $e^{-\eta(T-t_i)}$ `[NC: η]`

### 5.3 Risque de Bulle Cognitive

$$
H_{bulle}(T) = (1 - C_{flow}(T)) \cdot \tilde{B}(T) \cdot \text{iso}(T)
$$

- $\tilde{B}(T) = 1 - e^{-B_{load}(T)}$
- $\text{iso}(T) = 1 - \frac{|E_w(T)|}{|V(T)|}$ : ratio d'isolation (proportion de fragments sans collision)
- **Usage :** Si $H_{bulle} > \theta_{bulle}$ `[NC]`, le Cold Weaver augmente la fréquence et la distance des collisions.

---

## 6. Variable H (Humour) — Persona

### 6.1 Définition

$$
H(T) \in [-1, 1]
$$

$H$ pilote le registre communicationnel de la persona Delirium.

### 6.2 Calcul

$$
H(T) = \sigma\!\left( w_e \cdot \text{emo}(T) + w_h \cdot \text{hist}(T) + w_t \cdot \text{time}(T) + w_p \cdot \text{phase}(T) + w_f \cdot \text{fatigue}(T) \right) \cdot 2 - 1
$$

Où :
- $\text{emo}(T) \in [-1,1]$ : état émotionnel détecté (sentiment analysis sur les derniers messages)
- $\text{hist}(T) \in [-1,1]$ : tonalité moyenne de la conversation récente
- $\text{time}(T) \in [-1,1]$ : signal temporel (heure du jour, régularité d'usage)
- $\text{phase}(T) \in \{0, 0.3, 0.7, 1\}$ : phase de la relation (muet, reflet, sparring léger, sparring complet)
- $\text{fatigue}(T) \in [-1, 0]$ : mécanisme de "lassitude" de Delirium (décroit si l'utilisateur est répétitif)
- $w_e, w_h, w_t, w_p, w_f$ : poids `[NC]`

### 6.3 Ancrage

**Partiel.** La structure s'inspire de :
- Martin et al. (2003) — HSQ : 4 styles d'humour {affiliatif, auto-valorisant, agressif, auto-dépréciatif}
- O'Brien — SLAP : Surprise, Light-heartedness, Absurdity, Perspective
- Opinion Dynamics (Flache et al. 2017) — fonctions d'assimilation/répulsion entre agents

**TODO(formalisation) :** Prouver que $H$ converge vers un équilibre stable pour un utilisateur donné, ou documenter les conditions d'oscillation.

### 6.4 Persona comme Vecteur

$$
\text{Persona}(T) = (H(T), \ell(T), \kappa(T), \gamma(T), \epsilon(T), \phi(T)) \in [-1,1]^6
$$

| Composante | Symbole | Signification |
|---|---|---|
| Humour | $H$ | Registre communicationnel |
| Listen ratio | $\ell$ | 0=intervention, 1=écoute pure |
| Creativity | $\kappa$ | Audace des métaphores |
| Confrontation | $\gamma$ | Niveau de challenge |
| Empathy | $\epsilon$ | Écoute émotionnelle |
| Fatigue | $\phi$ | Lassitude de Delirium |

**Ancrage potentiel :** Architecture BDI (Rao & Georgeff 1995). La persona comme agent avec beliefs (archétype), desires (objectif communicationnel), intentions (ton choisi). **TODO(formalisation).**

---

## 7. Paramètres Non Calibrés — Registre Complet

| Symbole | Description | Hérité de | Valeur par défaut | Calibration |
|---|---|---|---|---|
| $\delta$ | Taux de déclin en H | OIDA | — | Ebbinghaus/Murre 2015 |
| $\tau_{ref}$ | Inertie du dommage B | OIDA | 3.0 | Empirique |
| $\alpha_B$ | Intensité bascule H→B | OIDA | 1.15 | Empirique |
| $\theta_s$ | Seuil arête supportive | Nouveau | 0.7 | Empirique |
| $\theta_f$ | Seuil friction sémantique | Nouveau | 0.6 | Empirique |
| $\theta_r$ | Seuil récurrence latente | Nouveau | 0.7 | Empirique |
| $\theta_d$ | Seuil surgissement dormant | Nouveau | 0.6 | Empirique |
| $\theta_B$ | Seuil bascule B | OIDA | 0.45 | Empirique |
| $\theta_{confirm}$ | Seuil confirmation C+ | Adapté | 0.6 | Empirique |
| $\theta_{cs}$ | Seuil notification collision | Nouveau | 0.5 | Empirique |
| $v_{purge}$ | Seuil de purge oubli | Nouveau | 0.01 | Empirique |
| $v_{react}$ | Valeur de réactivation | Nouveau | 0.8 | Empirique |
| $\eta$ | Récence pour C_flow | OIDA | — | Empirique |
| $\alpha_R, \alpha_N, \alpha_S$ | Poids collision score | Nouveau | 0.3/0.3/0.4 | SerenQA |
| $w_a, w_s, w_c$ | Poids sycophancy | Nouveau | 0.4/0.3/0.3 | Empirique |
| $w_e, w_h, w_t, w_p, w_f$ | Poids calcul H | Nouveau | — | Empirique |

**Total : 20 paramètres non calibrés.** C'est beaucoup. Stratégie :
1. Fixer les paramètres ancrés (δ via Ebbinghaus, α_R/N/S via SerenQA)
2. Analyse de sensibilité obligatoire sur les 15 restants
3. Les paramètres de seuil (θ_*) sont des hyperparamètres à tuner sur données réelles

---

## 8. Ce qui n'est PAS dans ce formalisme (et pourquoi)

| Composant OIDA V4.2 | Raison de l'exclusion |
|---|---|
| $L_D$ (treillis conceptuel) | Décoratif dans V4.2 — jamais utilisé. Remplacé par clustering HDBSCAN (§1.3) |
| $\mu(\tau, T)$ (frontière technologique) | Pas de tâches dans Delirium |
| $M_{IA}$ (maîtrise IA) | Non pertinent — Delirium n'évalue pas la compétence IA |
| $SIA_{eff}$ (effet IA) | Remplacé par sycophancy\_score (inversion) |
| $Q_{obs}$ (qualité observable) | Pas de "qualité" d'une pensée brute |
| $V_{IA}$ (valeur durable) | Remplacé par V_vision (concept, pas implémenté dans ce doc) |
| $x$ (expérience accumulée) | Pas d'exposition au domaine dans Delirium |
| $V_{relative}$ (valeur marché) | Pas de marché, pas de comparaison entre utilisateurs |
| Conditions de comptage N (id_inconnu, pert_sys, vision) | Non opérationnelles — tous les fragments entrent |

---

## 9. Propriétés à Vérifier (Tests Formels)

### Invariants

1. **Monotonicité de B_load :** Si aucun double-loop n'est déclenché, $B_{load}(T+1) \geq B_{load}(T)$
2. **Conservation du DAG :** $G_c$ reste acyclique après toute opération
3. **Transitivité de la dominance :** Si $\text{dom}(i,j)$ et $\text{dom}(j,k)$, alors $\text{dom}(i,k)$
4. **Déclin borné :** $\forall i, v_i(T) \geq 0$ si $s_i = H$ et $v_i(t_i) > 0$
5. **Purge effective :** $|V(T)|$ est borné par le budget stockage

### Propriétés Souhaitées (non prouvées)

6. **Convergence de H :** Pour un utilisateur avec un profil stable, $H(T)$ converge-t-il ?
7. **Non-trivialité de C_stock :** Un utilisateur actif et diversifié a-t-il $C_{stock} > 0$ en régime permanent ?
8. **Efficacité du double-loop :** Après correction, $N_{eff}$ augmente-t-il strictement ?

---

## Références

- Alchourrón, C.E., Gärdenfors, P., Makinson, D. (1985). On the logic of theory change. J. Symbolic Logic 50(2).
- Campello, R.J.G.B. et al. (2013). Density-Based Clustering Based on Hierarchical Density Estimates. PAKDD.
- Darwiche, A. & Pearl, J. (1997). On the logic of iterated belief revision. Artificial Intelligence 89.
- Ebbinghaus, H. (1885). Über das Gedächtnis.
- Flache, A. et al. (2017). Models of social influence. JASSS.
- Frenken, K. et al. (2007). Related Variety, Unrelated Variety and Regional Economic Growth. Regional Studies.
- Liu, Q.E. et al. (2026). Serendipity by Design. arXiv:2603.19087.
- Martin, R.A. et al. (2003). Individual differences in uses of humor. J. Research in Personality.
- Murre, J.M.J. & Dros, J. (2015). Replication and Analysis of Ebbinghaus' Forgetting Curve. PLOS ONE.
- Rao, A.S. & Georgeff, M.P. (1995). BDI Agents: From Theory to Practice. ICMAS.
- Shannon, C.E. (1948). A Mathematical Theory of Communication. Bell System Technical Journal.
- Sharma, M. et al. (2023). Towards Understanding Sycophancy in Language Models. arXiv:2310.13548.
- Spohn, W. (1988). Ordinal conditional functions.
- Wang, M. et al. (2025). Assessing LLMs for Serendipity Discovery in Knowledge Graphs. arXiv:2511.12472.
