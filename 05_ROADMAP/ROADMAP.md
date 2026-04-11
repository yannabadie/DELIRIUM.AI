# Roadmap — Delirium AI

**Version :** 1.0 | **Date :** 11 avril 2026

---

## Phase 0 — Fondation (T2 2026 : Avril-Juin)

### Livrables
- [ ] Arborescence projet + documentation complète (ce dossier)
- [ ] Prototype CLI du S1 (sparring partner avec persona calibré)
- [ ] System prompts S1 + S2 validés sur corpus de test
- [ ] Pipeline OSINT basique (APIs publiques)
- [ ] Prototype profilage inversé (10 scénarios testés)
- [ ] Base SQLite + schéma de données v1

### Critères Go/No-Go Phase 1
- Le S1 produit des réponses jugées "non-sycophantes ET non-toxiques" par 3 testeurs indépendants
- Le profilage inversé déclenche une correction spontanée dans > 70% des tests
- L'architecture de données supporte l'oubli sélectif

---

## Phase 1 — MVP Mobile (T3 2026 : Juillet-Septembre)

### Livrables
- [ ] App mobile (Flutter) — mono-bouton, capture vocale, sparring texte
- [ ] Whisper STT intégré (local, on-device)
- [ ] Onboarding archétype inversé fonctionnel
- [ ] Phase Confident Muet → Reflet → Sparring (progression automatique)
- [ ] Base vectorielle locale (ChromaDB/LanceDB)
- [ ] Chiffrement local (SQLCipher)
- [ ] 50 bêta-testeurs (friends & family)

### Critères Go/No-Go Phase 2
- Rétention J7 > 40%
- Rétention J30 > 20%
- NPS > 30 parmi les bêta-testeurs
- Aucun incident de sécurité ou de confidentialité
- Le registre de ton détecté correspond au registre réel dans > 60% des cas

---

## Phase 2 — Cold Weaver + Import IA (T4 2026 : Octobre-Décembre)

### Livrables
- [ ] Pipeline Cold Weaver v1 (ArXiv + GitHub)
- [ ] Import historiques ChatGPT (format JSON)
- [ ] Détection d'inspirations avortées (4 critères)
- [ ] Notifications de collision
- [ ] Première version du module Vision du Monde (détection de boucles)
- [ ] Oubli sélectif opérationnel
- [ ] 500 bêta-testeurs (bêta publique limitée)

### Critères Go/No-Go Phase 3
- Time-to-first-collision < 30 jours
- Taux de clic notifications > 40%
- Faux positifs collisions < 30%
- Au moins 1 "moment eurêka" rapporté par > 10% des testeurs

---

## Phase 3 — Viralité + Polish (T1 2027 : Janvier-Mars)

### Livrables
- [ ] Système d'invitation (signée/anonyme) avec description custom
- [ ] Import Claude + Gemini
- [ ] Sync cloud FR optionnel (E2E chiffré)
- [ ] App desktop (Tauri)
- [ ] TTS optionnel
- [ ] AIPD (Analyse d'Impact Protection des Données) réalisée
- [ ] Audit de sécurité externe

### Critères Go/No-Go Lancement
- Coefficient viral (K) > 0.5 (chaque utilisateur invite en moyenne 0.5 personne)
- Conformité RGPD validée par DPO ou conseil juridique
- Pen test passé sans vulnérabilité critique

---

## Phase 4 — Lancement Public (T2 2027)

### Livrables
- [ ] Lancement App Store + Play Store
- [ ] Modèle freemium opérationnel
- [ ] Support multilingue (FR + EN minimum)
- [ ] Infrastructure scalable (5000 utilisateurs actifs)
- [ ] Monitoring + alerting opérationnel

---

## Phase 5 — Recherche et Internationalisation (T3-T4 2027)

### Livrables
- [ ] Recherche socio/psycho non-occidentale intégrée
- [ ] Variantes culturelles du persona
- [ ] Papier de recherche : dérivation OIDA → Delirium
- [ ] Exploration TDA (persistent homology) sur données réelles
- [ ] Partenariats académiques potentiels
