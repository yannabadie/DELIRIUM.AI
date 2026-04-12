# Backlog Cold Weaver v2 — Idées écartées du prototype

**Date :** 12 avril 2026
**Contexte :** Ces idées ont été identifiées lors de la recherche sur la bisociation computationnelle et les fragments hétérogènes, mais jugées hors-scope pour le prototype actuel. Elles sont documentées ici pour implémentation future.

---

## 1. Analyse de code source ligne par ligne

**Quoi :** Analyser le code source de chaque fichier des repos GitHub, pas seulement le README et la structure.
**Pourquoi c'est écarté :** Coûteux en compute (N fichiers × appel LLM), et le PURPOSE d'un projet est mieux capturé par le README + structure que par le code brut.
**Quand le faire :** Phase 2, quand on voudra trouver des collisions entre MODULES spécifiques (ex: "ton module d'auth dans BulleoApp utilise le même pattern que ton pipeline OSINT dans NEXUS").
**Référence :** GraphGen4Code (IBM) — toolkit qui construit des knowledge graphs à partir de 1.3M fichiers Python.

## 2. Double embedding (mpnet + UniXcoder/CodeBERT)

**Quoi :** Embedder chaque fragment dans DEUX espaces — mpnet pour le sens naturel, UniXcoder pour la sémantique du code — et chercher des collisions dans les deux.
**Pourquoi c'est écarté :** Complexifie l'architecture (deux espaces vectoriels, double stockage, logique de fusion des scores). Le résumé LLM → mpnet capture suffisamment le PURPOSE pour le prototype.
**Quand le faire :** Quand les collisions textuelles ne suffisent plus, ou quand on veut détecter des patterns architecturaux similaires entre repos (pas juste des thèmes similaires).
**Référence :** UniXcoder (Microsoft) — code + commentaires + AST, 768D. CodeBERT — bimodal code/NL. GraphCodeBERT — code + data flow. voyage-code-3 (Voyage AI) — SOTA 2025.

## 3. Recherche génétique sur les combinaisons (type CodeScientist)

**Quoi :** Au lieu de scorer des paires une par une, utiliser un algorithme génétique pour ÉVOLUER les meilleures combinaisons de fragments par mutation/croisement. Traiter les fragments comme du "matériel génétique".
**Pourquoi c'est écarté :** Complexité algorithmique significative. Le scoring par paires avec LLM quality gate est suffisant pour prouver le concept de bisociation.
**Quand le faire :** Quand on a assez de données pour que l'espace de combinaisons soit trop grand pour le scan exhaustif (>10K fragments, >100M paires).
**Référence :** CodeScientist (Allen AI, ACL 2025) — genetic search over codeblocks + articles, 19 découvertes dont 6 jugées nouvelles. arXiv:2503.22708.

## 4. Knowledge graph type Discovery Engine / Conceptual Nexus Model

**Quoi :** Construire un tenseur conceptuel multi-dimensionnel (concepts × méthodes × paramètres × relations) à partir de tous les fragments, puis naviguer le graphe pour trouver les GAPS — pas juste les connexions, mais les TROUS dans la connaissance.
**Pourquoi c'est écarté :** Architecture lourde (tenseur multi-mode, agents de navigation, opérations mathématiques abstraites). Le graphe sémantique SQLite + Cold Weaver par paires suffit pour le prototype.
**Quand le faire :** Phase OmniArxiv, quand on passe d'un utilisateur à une plateforme collective. La détection de gaps devient critique quand on croise les graphes de plusieurs utilisateurs.
**Référence :** Discovery Engine / CNM (Baulin, 2025). arXiv:2505.17500. Conceptual Tensor → unrolling en graphe → agents naviguent pour trouver gaps et connexions non-évidentes.

## 5. Persistent Homology / TDA sur les embeddings

**Quoi :** Utiliser la topologie des données (Topological Data Analysis) pour détecter les structures persistantes, les boucles, et les cavités dans l'espace sémantique des fragments. Les β₁ (boucles) = thèmes contournés. Les β₂ (cavités) = unknown unknowns.
**Pourquoi c'est écarté :** Complexité computationnelle O(n³), nécessite réduction dimensionnelle (UMAP), interprétabilité difficile, pas de ground truth pour valider.
**Quand le faire :** Papier de recherche distinct. Étude N=200 pour valider que les structures topologiques correspondent à des "visions du monde" réelles.
**Référence :** Déjà documenté dans 04_FORMALISME/TOPOLOGIE_DONNEES.md. Giotto-TDA (Python). Carlsson (2009), Chazal & Michel (2021).

## 6. Analyse de data flow inter-repos

**Quoi :** Détecter quand deux repos différents traitent le MÊME type de données ou résolvent le MÊME sous-problème avec des approches différentes, en analysant les types d'input/output de chaque module.
**Pourquoi c'est écarté :** Nécessite une analyse statique de code profonde (AST parsing, type inference) qui dépasse le scope du prototype.
**Quand le faire :** Quand on a un pipeline GraphGen4Code fonctionnel et qu'on veut des collisions au niveau PATTERN ARCHITECTURAL, pas juste thématique.

## 7. Enrichissement par exécution de code

**Quoi :** Pour les repos avec tests, exécuter les tests pour comprendre ce que le code FAIT réellement (pas juste ce que le README dit). Les tests sont la documentation la plus honnête.
**Pourquoi c'est écarté :** Risque de sécurité (exécution de code arbitraire), complexité d'environnement (dépendances, versions), temps d'exécution.
**Quand le faire :** Dans un environnement sandboxé, quand on veut valider que deux modules sont réellement compatibles (pas juste thématiquement proches).

## 8. Scoring novelty × utility (framework Combinatorial Creativity)

**Quoi :** Au lieu du score Surprise × Relevance actuel, utiliser le framework de créativité combinatoire qui évalue chaque collision sur deux axes : novelty (à quel point c'est nouveau) ET utility (à quel point c'est utilisable/actionnable). Le tradeoff novelty-utility est formalisé.
**Pourquoi c'est écarté :** Nécessite un évaluateur LLM plus sophistiqué (pas juste quality 0-1 mais deux dimensions). Le quality gate actuel capture implicitement ce tradeoff.
**Quand le faire :** Quand on veut prioriser les collisions qui mènent à des PROJETS ACTIONNABLES, pas juste des connexions intéressantes.
**Référence :** Combinatorial Creativity (arXiv:2509.21043, 2025). Tradeoff novelty-utility caractéristique des algorithmes de créativité.

## 9. Import Obsidian/Notion/notes personnelles

**Quoi :** Importer les notes de PKM (Personal Knowledge Management) de l'utilisateur — Obsidian vault, Notion export, Apple Notes, etc. — comme fragments supplémentaires pour le Cold Weaver.
**Pourquoi c'est écarté :** Chaque format est différent (Markdown avec liens wiki, JSON Notion, SQLite Apple Notes). Trop de parsers à écrire pour le prototype.
**Quand le faire :** Phase 3 (Viralité + Polish), quand le produit est stable et qu'on veut maximiser les sources de fragments.

## 10. Clustering dynamique des fragments pour détection de thèmes émergents

**Quoi :** Au lieu d'extraire les thèmes par LLM (ThemeExtractor actuel), utiliser HDBSCAN sur les embeddings pour détecter des clusters qui ÉMERGENT naturellement, y compris des thèmes que l'utilisateur n'a jamais nommés.
**Pourquoi c'est écarté :** HDBSCAN nécessite scikit-learn + calibration du min_cluster_size. Le ThemeExtractor LLM est plus simple et produit des labels lisibles.
**Quand le faire :** Quand on a >5000 fragments et que les thèmes LLM ne capturent plus la diversité réelle.
**Référence :** HDBSCAN (Campello et al. 2013). Déjà mentionné dans FORMALISME_DELIRIUM_v0.1.md §1.3.

---

*Ces idées ne sont pas abandonnées. Elles sont en attente du moment où le prototype aura prouvé que la bisociation computationnelle sur fragments personnels fonctionne.*
