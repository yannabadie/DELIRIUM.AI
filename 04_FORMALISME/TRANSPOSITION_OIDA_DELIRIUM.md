# Transposition OIDA V4.2 → Delirium AI — Mapping Formel Complet

**Version :** 1.0 | **Date :** 11 avril 2026
**Source :** modele_v4_2_formalisme.md + oida/analyzer.py + oida/models.py
**Objectif :** Extraire chaque variable, fonction et comportement du formalisme OIDA V4.2 et définir sa transposition dans le contexte Delirium AI, ou justifier son abandon.

---

## 1. Changement de Cadre Fondamental

| Dimension | OIDA V4.2 | Delirium AI |
|---|---|---|
| Agent | Un individu professionnel | Un humain + N IA conversationnelles |
| Domaine | Un domaine D connu, formalisé par un treillis L_D | N domaines inconnus — l'utilisateur ne sait pas de quoi il parle |
| Expérience | Tâche professionnelle qualifiante | Fragment cognitif (idée, frustration, délire, question) |
| Boucle | O→I→D→A explicite et évaluable | Pas de boucle — des collisions stochastiques |
| Évaluateur | Observateur externe ou self-assessment | La machine porte la charge évaluative |
| Objectif | Mesurer la compétence et prédire la valeur nette | Détecter la cognition émergente et construire une vision du monde |
| Sortie | Q_obs, V_IA, H_sys, V_net | Collision, boucle détectée, persona optimale, vision construite |

---

## 2. Transposition Variable par Variable

### 2.1 Variables Structurelles

#### L_D (Treillis conceptuel du domaine)
**OIDA :** Contexte formel K_D = (O_D, A_D, R_D) → treillis L_D = 𝔅(K_D)
**Delirium :** **NON TRANSPOSABLE DIRECTEMENT.** Le domaine n'est pas connu a priori. 
**Remplacement :** Le graphe conceptuel de l'utilisateur émerge des fragments. Pas de treillis pré-défini — la structure se révèle par accumulation. C'est un graphe de similarité dynamique, pas un contexte formel.
**Implication :** Le Cold Weaver ne peut pas "chercher dans un domaine" — il cherche des collisions dans un espace non structuré. C'est pourquoi on migre vers la topologie des données (cf. TOPOLOGIE_DONNEES.md).

#### G_N^D (DAG de dépendance des expériences)
**OIDA :** DAG avec arêtes constitutives (nécessaires) et supportives (aidantes). Relation de dominance dom_D(i,j).
**Delirium :** **TRANSPOSABLE.** Le graphe conceptuel de l'utilisateur est un graphe orienté de fragments reliés par :
- `semantic_proximity` (≈ arête supportive)
- `temporal_cooccurrence` (≈ arête supportive)
- `user_linked` (≈ arête constitutive — l'utilisateur a explicitement relié deux idées)
- `collision` (nouveau — le Cold Weaver a créé la connexion)

**Adaptation :** La distinction constitutive/supportive est conservée mais inversée : dans OIDA, c'est l'agent qui crée les liens. Dans Delirium, c'est la machine qui crée la plupart des liens (par détection de similarité), et l'utilisateur qui valide ou invalide par son comportement.

**Implémentation :** La relation de dominance dom_D(i,j) reste pertinente pour la propagation de corrections double-loop. Si un fragment central est invalidé (par le sparring ou le Cold Weaver), les fragments qui en dépendent doivent être réexaminés.

#### T(D) (Tâches du domaine)
**OIDA :** Ensemble fini de tâches τ_1...τ_q avec frontière dentelée.
**Delirium :** **NON APPLICABLE.** L'utilisateur ne fait pas de tâches — il pense. Pas de tâches, pas de frontière dentelée.

---

### 2.2 Variables Fondamentales

#### N (Tissu cicatriciel)
**OIDA :** N^D(T) = Σ 𝟙[id_inconnu ∧ pert_sys ∧ vision ∧ t_i ≤ T]
**Delirium :** **TRANSPOSABLE avec adaptation.** 
- N n'est plus un comptage d'expériences professionnelles mais un **comptage de fragments cognitifs qualifiants**
- Un fragment est "qualifiant" s'il a été détecté comme porteur de signal (pas du bruit)
- Les conditions id_inconnu / pert_sys / vision sont remplacées par les 4 critères de détection d'inspirations avortées (friction, récurrence, abandon, surgissement)

```
N_delirium(T) = |{fragments actifs avec decay_weight > seuil}|
```

#### uN_i (Hypothèse obligatoire)
**OIDA :** uN_i(T) = (s_i(T), v_i(T), a_i(T)) avec s_i ∈ {H, C+, E, B}
**Delirium :** **TRANSPOSABLE DIRECTEMENT.** C'est le cœur de la transposition.

Chaque fragment de l'utilisateur est un uN_i :
- **H** (hypothèse) : idée brute, non examinée — état par défaut de tout ce qui entre dans Delirium
- **C+** (confirmé) : le Cold Weaver a trouvé une collision qui valide l'intuition, ET l'utilisateur a fait le lien lui-même
- **E** (éliminé) : le sparring a montré que c'est factuellement faux, l'utilisateur l'a accepté
- **B** (biais enfoui) : l'idée a été adoptée sans examen (validée par une IA sycophante, ou jamais challengée)

**Adaptation clé :** Dans OIDA, l'agent porte son propre uN. Dans Delirium, **la machine porte le uN pour le compte de l'humain**. L'utilisateur ne sait même pas que ses idées sont classifiées.

**v_i(T) ∈ [-1,1] :** Conservé. La valeur décroît exponentiellement si non réactivé (déclin naturel en état H).

**a_i(T) ∈ {0,1} :** Conservé comme drapeau de revue. Quand le Cold Weaver trouve une collision, a_i est mis à 1.

#### uDN_i (Trace cross-domaine)
**OIDA :** uDN_i = {D_j : D_j ≠ D, D_j mobilisé pendant N_i}
**Delirium :** **TRANSPOSABLE avec adaptation.**
- uDN_i = ensemble des tags thématiques co-activés lors du fragment i
- Détecté automatiquement par embedding clustering, pas par déclaration
- Un fragment qui touche à la fois la mécanique et la musique a un uDN_i riche

```
uDN_i = {cluster_k : fragment_i.embedding ∈ voisinage(centroide_k)}
```

#### N_eff (Stock net signé)
**OIDA :** N_eff^D(T) = N_stock^D(T) - B_load^D(T), peut être négatif
**Delirium :** **TRANSPOSABLE.**

```
N_stock = Σ (1 si s_i = C+) + Σ (v_i si s_i = H)
B_load = Σ damage_i(T) pour s_i = B
N_eff = N_stock - B_load
```

**Interprétation Delirium :** Un utilisateur dont les idées sont majoritairement en état B (validées sans examen par des IA sycophantes) a un N_eff qui tend vers le négatif. Delirium cherche à inverser cette tendance.

#### Debt (Dette d'apprentissage)
**OIDA :** Debt^D(T) = max{0, -N_eff^D(T)}
**Delirium :** **TRANSPOSABLE.** La dette cognitive est le volume d'idées biaisées non corrigées. C'est une métrique interne du système, jamais exposée à l'utilisateur.

---

### 2.3 Variables d'État et Transitions

#### Déclin naturel en état H
**OIDA :** v_i(T) = v_i(t_i) · exp(-δ(T - t_i))
**Delirium :** **TRANSPOSABLE DIRECTEMENT.** C'est exactement le mécanisme d'oubli sélectif :

```
decay_weight(t) = initial_weight * exp(-λ * (t - last_activated_at))
```

δ (OIDA) = λ (Delirium). Même mécanique, même interprétation.

#### Dommage en état B
**OIDA :** damage_i(T) = |v_i| · usage_i(T) · log(1 + (T - t_B,i) / τ_ref)
**Delirium :** **TRANSPOSABLE.** Le dommage augmente si un biais est réutilisé souvent et depuis longtemps.

```
damage_i(T) = |v_i| * (1 + reuse_count_i) * log(1 + (T - t_bias_i) / tau_ref)
```

**Adaptation :** `usage_i(T)` = nombre de fois que l'utilisateur a re-mentionné cette idée, ou que le graphe l'a mobilisée comme connexion.

#### Risque H → B (λ_H→B)
**OIDA :** λ_H→B = α_B · SIA_eff · (1-μ) · (1-G_D) · usage_i(T)
**Delirium :** **TRANSPOSABLE avec ré-interprétation.**

```
λ_H→B_delirium = α_B * sycophancy_score * (1 - grounding) * reuse_norm
```

Où :
- `sycophancy_score` remplace SIA_eff — mesure à quel point les IA externes ont validé mollement l'idée (détecté lors de l'import des historiques)
- `grounding` remplace G_D — mesure si l'utilisateur a des fragments validés (C+) dans le même cluster thématique
- `μ` est supprimé (pas de frontière technologique dans Delirium)
- `reuse_norm` est conservé — plus l'idée est réutilisée sans examen, plus le risque est fort

#### Single-loop / Double-loop
**OIDA :** Single-loop = correction locale. Double-loop = correction d'un nœud dominant + propagation via dom_D(i,j).
**Delirium :** **TRANSPOSABLE.**

- **Single-loop :** Le sparring montre qu'une idée spécifique est fausse → E. Pas de propagation.
- **Double-loop :** Le Cold Weaver ou le sparring invalide un concept central du graphe → tous les fragments dominés sont réouverts (s ← H, a ← 1), les fragments influencés sont marqués pour revue.

**Implémentation :** Identique à `double_loop_repair()` dans analyzer.py — graphe constitutif, synthetic root, dominance immédiate, propagation.

---

### 2.4 Variables Cross-Domaine

#### C_stock (Variété liée accumulée)
**OIDA :** Entropie de Shannon normalisée sur la distribution des domaines co-mobilisés, pondérée par w_i.
**Delirium :** **TRANSPOSABLE.**

```
C_stock = H_norm(distribution des clusters thématiques dans le graphe, pondérée par decay_weight)
```

Interprétation : un utilisateur dont les fragments sont répartis uniformément entre de nombreux clusters a un C_stock élevé = diversité cognitive élevée.

#### C_flow (Plasticité récente)
**OIDA :** Même chose mais avec pondération de récence exp(-η(T-t_i)).
**Delirium :** **TRANSPOSABLE.**

```
C_flow = H_norm(distribution des clusters récents, pondérée par decay_weight * exp(-η(T - t_i)))
```

Interprétation : un utilisateur qui explore activement de nouveaux domaines a un C_flow élevé.

**Usage Delirium :** C_flow est un input du module Vision du Monde :
- C_flow élevé → l'utilisateur est en mode exploration → le sparring peut être plus audacieux
- C_flow faible → l'utilisateur est en silo → le Cold Weaver doit introduire du bruit utile

#### Spillovers (ρ_ij)
**OIDA :** ρ_ij = ρ_0 · sim(D_j, D) · 𝟙[D_j ∈ uDN_i]
**Delirium :** **TRANSPOSABLE.** Quand un fragment est validé (C+), les fragments dans des clusters sémantiquement proches reçoivent un boost de decay_weight. Quand un fragment est biaisé (B), les fragments proches subissent un dommage proportionnel.

---

### 2.5 Variables de Sortie

#### Q_obs (Qualité observable)
**OIDA :** Q_obs = SIA_eff + (1-SIA_eff) · G_D
**Delirium :** **NON APPLICABLE DIRECTEMENT.** Il n'y a pas de "qualité observable" d'une pensée brute. 
**Remplacement possible :** `coherence_score` — mesure de la cohérence interne d'un fragment par rapport au graphe existant. Mais attention : les fragments les plus incohérents sont peut-être les plus intéressants (sérendipité).

#### V_IA (Valeur durable)
**OIDA :** V_IA = G_D · [1 + μ · SIA_eff] · g(C_stock, T)
**Delirium :** **TRANSPOSABLE comme "valeur de vision".** 

```
V_vision(fragment_i) = grounding_i * connectivity_i * g(C_stock, T)
```

Où :
- `grounding_i` = ancrage de l'idée dans des fragments validés (nombre de voisins C+ dans le graphe)
- `connectivity_i` = nombre de collisions Cold Weaver impliquant ce fragment
- `g(C_stock, T)` = accélérateur cross-domaine, conservé d'OIDA

#### H_sys (Nuisance systémique)
**OIDA :** H_sys = ψ(τ) · (1-μ) · SIA_eff · B̃ · Q_obs
**Delirium :** **TRANSPOSABLE comme "risque de bulle cognitive".**

```
H_bulle(user, T) = (1 - C_flow) * B̃(T) * isolation_score
```

Où :
- `C_flow faible` = l'utilisateur n'explore plus
- `B̃` = charge de biais normalisée
- `isolation_score` = mesure de l'isolement du graphe conceptuel (faible connectivité, clusters séparés)

C'est la métrique qui déclenche l'introduction de "bruit utile" par le Cold Weaver.

#### V_net (Valeur nette)
**OIDA :** V_net = V_IA - H_sys
**Delirium :** 

```
V_net_vision = V_vision - H_bulle
```

Métrique interne du système. Si V_net_vision < 0 pour un utilisateur, le Cold Weaver augmente la fréquence des collisions et le sparring augmente le challenge.

---

### 2.6 Variables Spécifiques à Delirium (NOUVELLES)

#### H (Humour) — Variable de persona
**Pas dans OIDA.** Nouveau pour Delirium.

```
H(T) ∈ [-1, 1]
```

H pilote le ton, le ratio écoute/intervention, la créativité des réponses. C'est le pendant communicationnel de uDN dans le domaine de l'interaction.

#### Persona(T) — Vecteur de personnage
**Pas dans OIDA.** Nouveau pour Delirium.

```
Persona(T) = {H, listen_ratio, creativity, confrontation, empathy, fatigue}
Persona(T+1) = f(Persona(T), user_state(T), conversation_intensity(T), time_context, s2_analysis(T))
```

#### Friction sémantique — Remplace l'entropie de Shannon sur C
**Pas dans OIDA.** Nouveau pour Delirium.

```
friction(msg_user, msg_ai) = 1 - cosine_similarity(embed(msg_user), embed(msg_ai))
```

Utilisé pour la détection d'inspirations avortées. Remplace le besoin de connaître le domaine.

#### Collision score — Sortie du Cold Weaver
**Pas dans OIDA.** Nouveau pour Delirium.

```
collision_score = f(semantic_distance, fragment_weight, source_recency, novelty_for_user)
```

Le "sweet spot" : similarité moyenne-haute (assez proche pour être pertinent, assez loin pour être surprenant).

#### Sycophancy score — Remplace SIA_eff
**Adaptation de OIDA.** SIA_eff mesure l'effet réel de l'IA sur l'individu. Dans Delirium, on mesure l'inverse : à quel point les IA ont validé mollement une idée sans la challenger.

```
sycophancy_score(fragment_i) = f(
    absence_de_contre_arguments_dans_la_reponse_IA,
    validation_molle_detectee,
    absence_de_sources
)
```

---

## 3. Comportements Transposables

### 3.1 Expert Atrophié → "Penseur Bullé"
**OIDA :** Q_obs élevé, Debt > 0, H_sys élevé, V_net < 0. Destructeur de valeur malgré une production crédible.
**Delirium :** Le "penseur bullé" — quelqu'un qui croit avoir des idées originales mais qui recycle des biais validés par des IA sycophantes. Son graphe conceptuel est dense mais isolé (pas de connexions cross-domaine). Son C_flow est faible. Son B_load est élevé.

### 3.2 Profil Adjacent → "Explorateur Naturel"
**OIDA :** C_stock et C_flow élevés, M_IA ≥ M_min, surperforme sur terrain nouveau.
**Delirium :** L'utilisateur dont les fragments sont répartis uniformément entre de nombreux clusters. Le Cold Weaver a le plus de matière pour trouver des collisions. C'est l'utilisateur pour qui Delirium fonctionne le mieux naturellement.

### 3.3 Novice → "Tout le Monde au Départ"
**OIDA :** Faible ancrage, forte dépendance à Q_obs, valeur durable faible.
**Delirium :** C'est l'utilisateur qui vient d'installer l'app. Phase Confident Muet → Reflet → Sparring progressif. N_eff est faible mais pas négatif (pas encore de biais accumulés dans Delirium).

---

## 4. Fonctions de l'Analyzer Transposables

### 4.1 grounding() → ancrage_fragment()
```python
def ancrage_fragment(fragment, graph):
    """Proportion de voisins validés (C+) dans le graphe."""
    neighbors = graph.neighbors(fragment.id)
    validated = sum(1 for n in neighbors if n.state == 'C+')
    total = len(list(graph.neighbors(fragment.id)))
    return validated / total if total > 0 else 0.0
```

### 4.2 lambda_bias() → risque_bias()
```python
def risque_bias(fragment, sycophancy_score, grounding, reuse_count, config):
    return (
        config.alpha_b
        * sycophancy_score
        * (1.0 - grounding)
        * (0.5 + 0.5 * reuse_norm(reuse_count))
    )
```

### 4.3 double_loop_repair() → propagation_correction()
```python
def propagation_correction(root_fragment_id, graph_constitutive, graph_all):
    """Identique à OIDA. Propagation via dominance."""
    # Réutilisation directe de l'algorithme OIDA :
    # 1. Synthetic root
    # 2. Dominance immédiate (NetworkX)
    # 3. Descendants dominés → reopen (s ← H, a ← 1)
    # 4. Descendants influencés → audit (a ← 1)
```

### 4.4 _n_stock() / _b_load() → conservés
```python
def n_stock(patterns):
    return sum(1.0 for p in patterns.values() if p.state == 'C+') + \
           sum(p.value for p in patterns.values() if p.state == 'H')

def b_load(patterns):
    return sum(p.damage for p in patterns.values())
```

---

## 5. Ce qui n'est PAS Transposable (et Pourquoi)

| Variable OIDA | Raison de l'abandon |
|---|---|
| μ(τ,T) — frontière technologique | Pas de tâches dans Delirium. L'utilisateur pense, il ne travaille pas. |
| M_IA — maîtrise des outils IA | Non pertinent. Delirium n'évalue pas la compétence IA de l'utilisateur. |
| SIA_brut — capacité brute des IA | Remplacé par sycophancy_score (inversion de la mesure). |
| Q_obs — qualité observable | Pas de "qualité" d'une pensée brute. Remplacé par coherence_score (optionnel). |
| x — expérience accumulée (intégrale) | Pas de notion d'exposition au domaine. Remplacé par la timeline d'accumulation. |
| V_relative — valeur relative au marché | Pas de marché dans Delirium. Pas de comparaison entre utilisateurs. |

---

## 6. Paramètres Non Calibrés (Hérités d'OIDA)

| Paramètre | OIDA | Delirium | Statut |
|---|---|---|---|
| δ / λ | Déclin des hypothèses | Taux de decay_weight | À calibrer empiriquement |
| τ_ref | Inertie temporelle du dommage | Conservé | À calibrer |
| α_B | Intensité de bascule vers B | Conservé | À calibrer |
| ρ_0 | Transfert inter-domaines | Conservé | À calibrer |
| η | Pondération de récence (C_flow) | Conservé | À calibrer |
| confirm_threshold | Seuil de confirmation C+ | Adapté (collision_score > seuil) | À calibrer |
| bias_threshold | Seuil de bascule B | Adapté (sycophancy + non-grounding) | À calibrer |

---

## 7. Synthèse : Ce qui Manque pour Formaliser

1. **Définition formelle de H (Humour)** — sa dynamique, ses dépendances, son influence sur la persona
2. **Définition formelle du collision_score** — fonction mathématique exacte du "sweet spot" sémantique
3. **Définition formelle du sycophancy_score** — comment détecter la validation molle dans un historique IA
4. **Relation entre H_bulle et le déclenchement du Cold Weaver** — seuil, fréquence, intensité
5. **Calibration des paramètres** — nécessite un corpus de test réel (conversations + imports IA)
6. **Validation topologique** — persistent homology sur graphe conceptuel (R&D, pas MVP)

---

*Ce document sert de pont entre le papier OIDA V4.2 publié et l'implémentation Delirium AI. Il doit être mis à jour au fur et à mesure de la formalisation.*
