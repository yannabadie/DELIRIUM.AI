# Topologie des Données — Piste de Recherche

**Version :** 0.1 (Exploratoire) | **Date :** 11 avril 2026
**Statut :** R&D — Non implémenté, piste de formalisation future

---

## 1. Problème

OIDA utilise l'entropie de Shannon pour mesurer C (compétence cross-domaine) dans un domaine D connu. Dans Delirium, le domaine est inconnu, la distribution de base n'existe pas, et les fragments proviennent de sources multiples hétérogènes. Shannon ne s'applique pas.

**Question :** Quel formalisme mathématique permet de détecter des structures émergentes (cohérence, récurrences, trous) dans un espace sémantique non défini a priori ?

---

## 2. Piste : Topological Data Analysis (TDA)

### 2.1 Persistent Homology
- Les embeddings des fragments utilisateur forment un nuage de points dans ℝⁿ
- La persistent homology détecte des structures topologiques (composantes connexes, boucles, cavités) qui persistent à travers plusieurs échelles
- **Application Delirium :** Les structures persistantes dans le nuage de fragments = les thèmes profonds de l'utilisateur. Les structures éphémères = le bruit.

### 2.2 Nombres de Betti
- β₀ = nombre de composantes connexes (clusters thématiques isolés)
- β₁ = nombre de boucles (thèmes que l'utilisateur contourne sans y entrer)
- β₂ = nombre de cavités (zones vides dans l'espace sémantique)
- **Application Delirium :** Les β₁ sont les domaines que l'utilisateur évite activement. Les β₂ sont les "unknown unknowns". Le Cold Weaver devrait cibler ces zones en priorité.

### 2.3 Persistence Diagrams
- Visualisation de la naissance/mort des features topologiques en fonction de l'échelle
- **Application Delirium :** Suivi diachronique — comment la topologie de la pensée de l'utilisateur évolue dans le temps. Apparition de nouvelles composantes = élargissement de la vision. Fusion de composantes = connexion cross-domaine réussie.

---

## 3. Lien avec OIDA

| Concept OIDA | Équivalent TDA |
|---|---|
| N_eff (stock net signé) | Richesse topologique (nombre de features persistantes) |
| uDN (capacité métacognitive) | Taux de changement topologique (les features bougent-elles ?) |
| C (transfert cross-domaine) | Fusion de composantes β₀ dans le persistence diagram |
| Expert atrophié | β₀ élevé, β₁ élevé, peu de fusions = silos cognitifs |
| Boucle cognitive | β₁ persistant autour d'un même centroïde |

---

## 4. Challenges Pratiques

1. **Dimensionalité :** Les embeddings sont en dim 768-1536. TDA est computationnellement coûteux en haute dimension → réduction (UMAP) nécessaire avant analyse.
2. **Volume :** La persistent homology a une complexité O(n³) naïve. Pour des milliers de fragments → approximations (Ripser, Giotto-TDA).
3. **Interprétabilité :** Les persistence diagrams sont difficiles à interpréter pour un non-mathématicien → nécessité de traduction en langage produit.
4. **Validation :** Aucune ground truth n'existe pour valider que les structures détectées correspondent à des "visions du monde". → Étude utilisateur nécessaire.

---

## 5. Prochaines Étapes

1. Prototype sur un corpus synthétique (conversations simulées multi-domaines)
2. Benchmark persistent homology vs. clustering classique (HDBSCAN) sur la détection de thèmes
3. Si résultats positifs → papier de recherche distinct : "Detecting Emergent Cognition in Multi-Agent Human-AI Systems via Topological Data Analysis"
4. Lien avec le papier OIDA existant : OIDA comme cas particulier (topologie triviale d'un agent dans un domaine unique)

---

## 6. Références Préliminaires

- Carlsson, G. (2009). Topology and data. Bulletin of the AMS.
- Otter, N. et al. (2017). A roadmap for the computation of persistent homology. EPJ Data Science.
- Chazal, F. & Michel, B. (2021). An introduction to Topological Data Analysis. Frontiers in AI.
- Giotto-TDA : bibliothèque Python pour TDA (https://giotto-ai.github.io/gtda-docs/)
