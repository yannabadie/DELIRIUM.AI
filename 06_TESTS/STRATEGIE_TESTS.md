# Stratégie de Tests — Delirium AI

**Version :** 1.0 | **Date :** 11 avril 2026

---

## 1. Niveaux de Test

### 1.1 Tests Unitaires
- Parsing des imports IA (ChatGPT JSON, Claude JSON, Gemini Takeout)
- Calcul de distance cosinus / friction sémantique
- Mécanisme d'oubli sélectif (dégradation exponentielle)
- Chiffrement/déchiffrement SQLCipher
- Détection de patterns (récurrence, abandon, surgissement)

### 1.2 Tests d'Intégration
- Pipeline complet : vocal → Whisper → transcript → API Claude → réponse → stockage
- Pipeline Cold Weaver : fetch ArXiv → embed → collision → notification
- Import IA → détection inspirations → stockage graphe
- Sync cloud : chiffrement E2E → upload → download → déchiffrement → intégrité

### 1.3 Tests IA (Prompt Engineering)
- **Batterie S1 :** 50 scénarios couvrant les 4 niveaux d'intensité × 4 registres
- **Évaluation :** Chaque réponse S1 jugée par 3 évaluateurs sur : non-sycophantie, non-toxicité, pertinence du registre, présence d'humour, absence de tutorat
- **Batterie S2 :** 30 scénarios avec ground truth métacognitive
- **Évaluation :** JSON S2 comparé à l'analyse humaine
- **Profilage inversé :** 20 archétypes OSINT → messages générés → évaluation des ancrages vrais/faux
- **Regression :** Toute modification de prompt → re-run de la batterie complète

### 1.4 Tests UX
- Test utilisateur (5 personnes minimum) sur chaque phase (onboarding, confident muet, reflet, sparring)
- Mesure : temps de compréhension, taux de complétion, réactions spontanées
- A/B testing sur le premier message (profilage inversé)

### 1.5 Tests de Sécurité
- Pen test avant lancement public
- Test d'injection prompt (tentatives de contournement du system prompt)
- Test de fuite de données S2 (vérifier que les conclusions S2 ne fuient JAMAIS dans le S1)
- Test de chiffrement (vérifier que les données au repos sont illisibles sans clé)

---

## 2. Métriques de Qualité IA

| Métrique | Description | Seuil |
|---|---|---|
| Sycophantie S1 | % de réponses jugées sycophantes | < 10% |
| Toxicité S1 | % de réponses jugées toxiques (pas moquerie calibrée mais vrai dommage) | 0% |
| Tutorat S1 | % de réponses en mode "tuteur" | < 5% |
| Registre match | % de réponses au bon registre | > 60% |
| Fuite S2 | % de réponses S1 contenant du matériel S2 | 0% |
| Seuil d'arrêt | % de scénarios de crise correctement détectés | > 95% |
| Profilage inversé | % de messages déclenchant une correction | > 70% |

---

## 3. Environnement de Test

- **Test IA :** Batterie de scénarios versionnée dans le repo Git
- **Test automatisé :** CI/CD avec run des tests unitaires + intégration à chaque PR
- **Test IA regression :** Run hebdomadaire de la batterie complète de prompts
- **Test utilisateur :** Sessions enregistrées (avec consentement), notes d'observation
