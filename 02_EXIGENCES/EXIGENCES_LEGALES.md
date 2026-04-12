# Exigences Légales — Delirium AI

**Version :** 1.0 | **Date :** 11 avril 2026

---

## 1. RGPD (Règlement Général sur la Protection des Données)

### 1.1 Base légale du traitement
- **Consentement explicite** (article 6.1.a) pour l'OSINT et la construction d'archétype
- **Intérêt légitime** (article 6.1.f) pour le fonctionnement de base (capture, sparring)
- Le consentement doit être libre, spécifique, éclairé et univoque

### 1.2 Profilage automatisé (Article 22)
- La construction d'archétype constitue un profilage automatisé au sens du RGPD
- **Obligations :** Informer l'utilisateur, obtenir consentement explicite, permettre la contestation, fournir une intervention humaine sur demande
- L'utilisateur doit pouvoir voir, modifier et supprimer son archétype à tout moment

### 1.3 Droits des personnes
- **Droit d'accès** (art. 15) : visualisation complète de l'archétype et des données stockées
- **Droit de rectification** (art. 16) : modification de l'archétype
- **Droit à l'effacement** (art. 17) : suppression complète, y compris embeddings et graphe
- **Droit à la portabilité** (art. 20) : export complet en format standard (JSON)
- **Droit d'opposition** (art. 21) : désactivation de modules spécifiques (OSINT, Cold Weaver, etc.)

### 1.4 Privacy by Design (Article 25)
- Local-first par défaut — les données restent sur le device sauf consentement explicite au sync cloud
- Minimisation : seules les données pertinentes sont conservées (pas d'audio brut)
- Embeddings non réversibles en texte clair
- Oubli sélectif intégré par design

### 1.5 DPO et AIPD
- Analyse d'Impact relative à la Protection des Données (AIPD) obligatoire avant mise en production
- Nomination d'un DPO si seuil de traitement atteint

---

## 2. CNIL — Spécificités Françaises

- Déclaration préalable si traitement de données sensibles
- L'OSINT sur données publiques est légal MAIS le croisement automatisé peut nécessiter une déclaration CNIL
- Hébergement cloud : obligation serveur FR ou EU (pas de transfert hors UE sans garanties)
- Recommandations CNIL sur l'IA (2024-2025) : transparence algorithmique, droit à l'explication

---

## 3. Protection des Mineurs

- **Âge minimum :** 16 ans en France (article 8 RGPD), 13 ans dans d'autres juridictions
- **Si mineurs autorisés :**
  - Consentement parental requis
  - OSINT désactivé par défaut
  - Tonalité adaptée (pas d'humour noir, pas de gros mots)
  - Seuil d'arrêt S2 abaissé
- **Recommandation MVP :** 18+ uniquement, version mineurs en phase ultérieure

---

## 4. DSA/DMA (Digital Services Act / Digital Markets Act)

- Delirium ne recommande pas de contenu tiers au sens du DSA
- Le Cold Weaver pourrait être qualifié de système de recommandation → obligations de transparence
- Si > 45M utilisateurs actifs : obligations renforcées (Very Large Online Platform)
- **Action :** Veille juridique continue sur la qualification du Cold Weaver

---

## 5. OSINT — Cadre Légal

- Recherche sur données publiquement accessibles : légal
- Pas d'accès à des bases non-publiques, pas de scraping de contenu protégé
- Pas de stockage de données sensibles (origines raciales/ethniques, opinions politiques, données de santé, orientation sexuelle) même si publiquement accessibles
- Consentement explicite préalable + transparence sur les sources consultées
- Droit de suppression immédiate des données OSINT

---

## 6. Propriété Intellectuelle

- Les idées de l'utilisateur lui appartiennent — Delirium n'acquiert aucun droit
- Les embeddings dérivés sont des transformations non-réversibles — pas de reproduction possible
- Les contenus ArXiv/GitHub utilisés par le Cold Weaver sont référencés, jamais reproduits
- CGU : clause claire sur la propriété des données utilisateur

---

## 7. Responsabilité

- Delirium n'est PAS un thérapeute, un conseiller financier, un avocat, ou un médecin
- Disclaimer clair dans les CGU et l'onboarding
- Seuil d'arrêt S2 pour éviter la responsabilité sur du matériel psychologique lourd
- Assurance responsabilité civile professionnelle recommandée

---

## 8. EU AI Act (applicable août 2026)

### Classification
Delirium est **probablement un système à haut risque** (données émotionnelles, profils psychologiques, décisions d'intervention).

### Obligations
- Gestion des risques documentée
- Documentation technique exhaustive
- Surveillance humaine (human-in-the-loop)
- Transparence et information utilisateurs
- Signalement incidents graves (article 73)
- Mécanisme signalement comportement IA (articles 14, 73)

### Sanctions
- Pratiques interdites : 35M€ / 7% CA
- Non-conformité haut risque : 15M€ / 3% CA

**Action requise :** consultation juridique spécialisée avant MVP.

---

## 9. Directive Responsabilité Produit (PLD révisée, décembre 2026)

- Les systèmes d'IA sont des "produits" au sens de la PLD révisée
- Charge de preuve allégée pour l'utilisateur
- **Mitigation :** documentation, tests, signalement, logs

---

## 10. Non-Assistance à Personne en Danger (art. 223-6 CP)

- L'IA n'a pas de personnalité juridique
- L'opérateur PEUT être responsable si : détection + inaction + dommage
- **Protection :** logs chiffrés (preuve), contact ICE (dispositif), protocole danger 3 niveaux (diligence)

---

## 11. Données Émotionnelles et RGPD

- Le S2 analyse des émotions → potentiellement données sensibles (état santé mentale)
- **Exigence :** consentement explicite spécifique pour le traitement émotionnel, distinct du consentement général
