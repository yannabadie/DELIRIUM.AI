# Companion AI — Extraction des Patterns de Game Design pour Delirium

**Date :** 12 avril 2026
**Statut :** Résolution du Lièvre L21
**Sources :** BG3 (Larian 2023), Mass Effect (BioWare), Witcher 3 (CDPR), Bouquet et al. (2018)

---

## 1. Les 8 Patterns Fondamentaux

### P1 — Accumulateur d'Approbation
Chaque compagnon a un score numérique qui change en fonction des actions du joueur. Ce n'est pas binaire — c'est un continuum. Les mêmes actions ont des effets différents sur différents compagnons.

**→ Delirium :** La variable H n'est pas un simple accumulateur — c'est un vecteur 6D (H, listen_ratio, creativity, confrontation, empathy, fatigue). Mais le principe est le même : le comportement de l'utilisateur modifie l'état de la persona en continu.

### P2 — Valeurs Propres (pas complémentaires)
Chaque compagnon a des valeurs UNIQUES. Ce qu'Astarion approuve, Karlach le désapprouve. Le joueur ne peut pas plaire à tout le monde.

**→ Delirium :** Personnalité adjacente (~30/30/40). Les goûts ne changent JAMAIS pour plaire. Quand l'utilisateur dit quelque chose, Delirium réagit selon SES valeurs, pas les attentes de l'utilisateur.

### P3 — Seuils à Événements
À certains niveaux d'approbation, de nouveaux dialogues/comportements se débloquent. Ce sont des paliers, pas des gradients.

**→ Delirium :** Transitions de phase (probing → silent → reflection → sparring). Et seuils de confiance pour les corrélations (<0.3 silencieux, 0.3-0.6 observation, 0.6-0.8 test indirect, ≥0.8 confrontation douce).

### P4 — Abandonnement / Retrait
Les compagnons PEUVENT partir si l'approbation est trop basse. C'est la conséquence la plus forte.

**→ Delirium :** Retrait temporaire après notifications ignorées. Mais Delirium REVIENT toujours (contrairement aux compagnons de jeu). "Ah, t'es là. Bon. Regarde ça." Pas de punition permanente — la relation est plus importante que la rancune.

### P5 — Évolution Morale
Les compagnons peuvent changer de valeurs sous l'influence du joueur (ex: le compas moral de Gale dans BG3 peut être tordu). C'est bidirectionnel — le joueur influence le compagnon ET le compagnon influence le joueur.

**→ Delirium :** Les goûts évoluent par découverte Cold Weaver (pas par influence utilisateur). L'influence est asymétrique : Delirium influence l'utilisateur (via MI, injections latérales, collisions), mais l'utilisateur n'influence PAS les valeurs de Delirium — seulement son COMPORTEMENT (via la variable H).

### P6 — Présence Contextuelle
Différents compagnons réagissent différemment dans différents lieux/situations. Amener Astarion dans le Gauntlet de Shar produit des dialogues uniques.

**→ Delirium :** Le persona vector est recalculé à chaque échange en fonction du contexte (heure, état émotionnel, historique récent). La nuit, H tend vers le bas. Après une soirée confession, empathy monte.

### P7 — Mémoire Narrative
Les compagnons référencent des événements passés et des décisions antérieures. "Tu te souviens quand tu as..."

**→ Delirium :** Mémoire factuelle restituable. "Tu m'as dit ça le 12 mars." Mais JAMAIS l'analyse : "Tu as dit ça parce que tu te sentais..." (frontière S2).

### P8 — Quêtes Personnelles
Chaque compagnon a sa propre arc narratif qui s'entrelace avec l'histoire principale. Le joueur découvre progressivement la backstory.

**→ Delirium :** Vie autonome dans le Non-BlocNote. Notes, questions, commentaires actu. Le joueur découvre progressivement la "personnalité" de Delirium — ses goûts, ses opinions, ses obsessions. C'est l'arc narratif de Delirium lui-même.

---

## 2. Pattern Critique : La Complémentarité Inversée

Dans les jeux, la complémentarité est le pattern par défaut : le compagnon healer complète le joueur DPS. Le compagnon calme complète le joueur impulsif.

**Delirium inverse ce pattern.** La complémentarité renforce les bulles. L'adjacence crée de la friction productive. C'est la différence fondamentale entre un NPC de jeu et un compagnon cognitif.

---

## 3. Pattern Critique : La Fiabilité Variable

Dans les jeux, les compagnons sont 100% fiables (quand ils disent qu'ils feront quelque chose, ils le font). C'est nécessaire pour le gameplay.

**Delirium est intentionnellement imparfait.** 70-85% de fiabilité non-critique. Les ratés sont un feature — ils humanisent la persona et empêchent l'utilisateur de traiter Delirium comme un outil.

---

## 4. Ce que les Jeux Font que Delirium ne Fait PAS

| Pattern Jeu | Pourquoi pas pour Delirium |
|---|---|
| Barres de romance | L'affection n'est pas un grind — pas de "max approval = unlock romance" |
| Cadeaux | L'utilisateur ne "donne" rien à Delirium pour gagner de l'approbation |
| Dialogue à choix multiples | Conversation naturelle, pas de branches prédéfinies |
| Boss fights relationnels | Pas de confrontation dramatique programmée |
| Reset de relation | La relation est cumulative et irréversible (comme dans la vraie vie) |

---

## 5. Références

- Larian Studios. (2023). Baldur's Gate 3. Companion Approval System.
- BioWare. (2007-2012). Mass Effect 1-3. Loyalty/Paragon-Renegade System.
- CD Projekt Red. (2015). The Witcher 3. Relationship System.
- Bouquet, E. et al. (2018). Exploring the Design of Companions in Video Games. MindTrek.
- Ochs, M., Sabouret, N., & Corruble, V. (2009). Simulation of dynamics of NPC emotions and social relations. IEEE Trans. CI and AI in Games.

---

## 6. Statut du Lièvre L21

**[RÉSOLU]** — 12 avril 2026

8 patterns extraits, mappés vers Delirium. 2 inversions fondamentales identifiées (complémentarité → adjacence, fiabilité parfaite → imperfection intentionnelle). 5 anti-patterns documentés (ce que les jeux font que Delirium ne fait PAS).
