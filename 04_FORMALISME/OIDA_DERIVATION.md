# Dérivation OIDA → Delirium

**Version :** 1.0 | **Date :** 11 avril 2026
**Référence :** Abadie, Y. (2026). OIDA Framework — arXiv preprint, soumis NeurIPS 2026 SafeGenAI

---

## 1. Rappel OIDA Classique

### 1.1 Boucle O→I→D→A
- **O (Observation)** : perception du domaine D
- **I (Interprétation)** : construction de sens à partir de O
- **D (Décision)** : choix d'action basé sur I
- **A (Action)** : exécution et feedback

### 1.2 Variable uDN
```
uDN_i ∈ [-1, 1]
```
Coefficient par expérience mesurant la capacité métacognitive exercée. Machine à 4 états :
- **H (Hypothèse)** : état initial, non testé
- **C⁺ (Connaissance validée)** : hypothèse confirmée par le réel
- **E (Erreur reconnue)** : hypothèse infirmée et admise
- **B (Biais enfoui)** : hypothèse adoptée sans examen, potentiellement fausse

### 1.3 N effectif
```
N_eff = Σᵢ 𝟙[id_i ∧ pert_i ∧ vis_i] · (1 + uDN_i)
```
N_eff peut être négatif — un agent peut avoir une expérience nette destructrice.

---

## 2. Pourquoi OIDA Ne S'Applique Pas Directement

OIDA modélise **un agent, un domaine connu, une boucle identifiable**. Delirium opère dans un espace fondamentalement différent :

| Dimension | OIDA | Delirium |
|---|---|---|
| Agent | Un (humain ou IA) | Humain + N IA + Delirium |
| Domaine | Connu (D) | Inconnu, multiple, variable |
| Boucle | O→I→D→A identifiable | Pas de boucle — fragments chaotiques |
| Mesure de C | Shannon sur D connu | Impossible (pas de distribution de base) |
| uDN | Porté par l'agent | Porté par la machine pour l'humain |
| Entropie | Applicable (distribution connue) | Non applicable directement sur données numériques extraites |

---

## 3. Dérivation : De OIDA à Delirium

### 3.1 Inversion du Porteur de uDN

Dans OIDA, uDN mesure la capacité métacognitive **de l'agent**. Dans Delirium, l'utilisateur produit des hypothèses brutes (état H) **sans réflexivité** — c'est le contrat produit ("vos idées à la con sont intéressantes").

La machine prend la charge réflexive :
```
uDN_delirium(i) = f(machine_metacognition(fragment_i))
```

La machine classe, attend, connecte, laisse mûrir. L'objectif :
- **Empêcher H→B** (biais enfoui = idée jamais examinée qui s'ancre)
- **Maximiser H→C⁺** (validation par le réel, via les collisions du Cold Weaver)

### 3.2 La Transition H→C⁺ dans Delirium

Dans OIDA, H→C⁺ se produit par test explicite dans le domaine D.

Dans Delirium, H→C⁺ se produit quand :
1. Le Cold Weaver détecte une collision entre un fragment H et une publication réelle
2. Delirium pose le contenu au bon moment
3. **L'utilisateur fait le lien lui-même**

C'est une transition assistée mais non-dirigée. Le locus de contrôle reste chez l'humain.

### 3.3 L'Oubli Sélectif comme Dégradation de uDN

Dans OIDA, un uDN non réactivé se dégrade naturellement. Dans Delirium :
```
weight(node, t) = weight₀ · 0.5^(t / half_life)
if weight < threshold: delete(node)  // H disparaît — ni C⁺, ni E, ni B
```

C'est une cinquième transition : **H→∅ (oubli)**. L'hypothèse n'a jamais été ni validée ni infirmée — elle s'efface. C'est le destin naturel de la majorité des fragments.

---

## 4. Extension Théorique : Cognition Émergente Multi-Agents

### 4.1 OIDA comme Cas Particulier

OIDA (un agent, un domaine, une boucle) est un cas particulier d'un cadre plus large : **la détection de cognition émergente dans des systèmes multi-agents humain-IA**.

Delirium opère dans le cas sauvage :
- N agents (humain + ChatGPT + Claude + Gemini + Delirium)
- N domaines (tous inconnus a priori)
- Pas de boucle O→I→D→A identifiable
- Des fragments chaotiques, des malentendus, des collisions

### 4.2 Ce Qui Est Mesurable Sans Connaître le Domaine

1. **Friction sémantique** — écart vectoriel entre Q et R dans une conversation IA. Zone de malentendu potentiellement créatif.
2. **Récurrence latente** — clustering cross-plateforme. L'utilisateur tourne autour d'un thème sans le nommer.
3. **Abandon après résistance** — pattern détectable : insistance → reformulation → abandon.
4. **Surgissement non rebondi** — concept IA ignoré, pertinent rétrospectivement.

### 4.3 Migration Mathématique

OIDA utilise Shannon pour mesurer C (entropie sur la distribution de compétence dans D connu).

Delirium ne peut pas utiliser Shannon (pas de distribution de base). L'outil mathématique approprié est la **topologie des données** :
- **Persistent homology** : détection de structures persistantes dans des nuages de points (embeddings)
- **Graphes de similarité** : détection de clusters instables qui apparaissent/disparaissent
- **Analyse de Betti** : comptage des "trous" dans l'espace sémantique de l'utilisateur — les domaines qu'il contourne sans les explorer

Ceci constitue un **papier de recherche distinct** — cf. `04_FORMALISME/TOPOLOGIE_DONNEES.md`.

---

## 5. Implications pour le Produit

| Concept OIDA | Implémentation Delirium |
|---|---|
| uDN porté par l'agent | uDN porté par la machine (S2) |
| Machine à états {H,C⁺,E,B} | Ajout de H→∅ (oubli sélectif) |
| N_eff signé | Score de richesse du graphe personnel |
| Boucle O→I→D→A | Détection de fragments + collisions asynchrones |
| C (transfert cross-domaine) | Cold Weaver cross-domain par design |
| Expert atrophié (Q élevé, V négatif) | Détection de boucles cognitives |
