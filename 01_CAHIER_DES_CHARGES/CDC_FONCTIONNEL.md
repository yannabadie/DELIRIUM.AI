# Cahier des Charges Fonctionnel — Delirium AI

**Version :** 1.0
**Date :** 11 avril 2026
**Statut :** Draft

---

## 1. Objet du Document

Ce document décrit les fonctionnalités attendues de Delirium AI. Il est destiné à être audité par des agents IA avant mise en production pour vérifier la cohérence, la complétude et la faisabilité.

---

## 2. Périmètre

Delirium AI est une application mobile-first (avec déclinaison desktop) qui agit comme un compagnon intellectuel non-servile. Il capture les pensées de l'utilisateur, les challenge avec humour, et construit progressivement une vision du monde personnalisée en croisant les fragments de l'utilisateur avec le savoir mondial.

---

## 3. Fonctionnalités par Module

### 3.1 Module ONBOARDING — Archétype Inversé

**F-ONB-01 :** Collecte minimale — nom, prénom, date de naissance
**F-ONB-02 :** Recherche OSINT automatique (consentie) — réseaux sociaux publics, publications, traces numériques
**F-ONB-03 :** Construction d'un archétype initial (milieu social estimé, centres d'intérêt détectés, positionnement culturel)
**F-ONB-04 :** Génération du premier message par profilage inversé — ancrages vrais (1-2) + erreurs volontaires (reste)
**F-ONB-05 :** Affichage transparent de l'archétype sur demande (droit d'accès RGPD)
**F-ONB-06 :** Variante onboarding par invitation — l'inviteur fournit une description custom (signée ou anonyme)
**F-ONB-07 :** Pré-archétype construit à partir de la description d'invitation + OSINT

### 3.2 Module CAPTURE — Le Confident Muet

**F-CAP-01 :** Interface mono-bouton (enregistrement vocal)
**F-CAP-02 :** STT local (Whisper) — transcription on-device, audio non stocké
**F-CAP-03 :** Saisie texte alternative
**F-CAP-04 :** Réponse minimale : "Noté." (phases 1-2)
**F-CAP-05 :** Calibrage silencieux du registre utilisateur (vocabulaire, rythme, sujets récurrents, niveau de langage)
**F-CAP-06 :** TTS optionnel pour les réponses de Delirium (voix configurable)
**F-CAP-07 :** Stockage : transcript uniquement → extraction données pertinentes → embedding + graphe. Données brutes purgées après extraction.

### 3.3 Module SPARRING — Système 1 + Système 2

**F-SPR-01 :** Réponse S1 instantanée — humour calibré, jamais de tutorat
**F-SPR-02 :** Détection d'intensité de l'idée (banale → violente) — classification par le LLM
**F-SPR-03 :** Gradient de réponse S1 adapté à l'intensité (cf. VISION_v4 §4.4)
**F-SPR-04 :** Registre linguistique adaptatif — gros mots autorisés si c'est le registre détecté de l'utilisateur
**F-SPR-05 :** S2 métacognitif asynchrone — analyse "pourquoi cette personne dit ça"
**F-SPR-06 :** RÈGLE ABSOLUE : les conclusions du S2 ne sont jamais restituées directement à l'utilisateur
**F-SPR-07 :** Les sorties S2 alimentent le module Tisserand et le module Vision du Monde
**F-SPR-08 :** Delirium peut raconter ses propres histoires / parcours d'utilisateurs imaginaires
**F-SPR-09 :** Delirium peut refuser de répondre / dire que l'idée est mauvaise / dire des gros mots — il n'est pas servile
**F-SPR-10 :** Fonctions utilitaires basiques accessibles ("rappelle-moi l'anniversaire de X", etc.)

### 3.4 Module TISSERAND — Cold Weaver

**F-TIS-01 :** Connexion aux API d'export des conversations IA (ChatGPT, Claude, Gemini, Copilot)
**F-TIS-02 :** Détection d'inspirations avortées dans les historiques externes — 4 critères :
  - Friction sémantique (écart vectoriel question/réponse)
  - Récurrence latente (thème qui revient sous formes différentes cross-plateforme)
  - Abandon après résistance (insistance → reformulation → changement de sujet)
  - Surgissement non rebondi (concept introduit par l'IA, ignoré par l'utilisateur)
**F-TIS-03 :** Pipeline de veille mondiale — flux ArXiv, GitHub trending, presse généraliste
**F-TIS-04 :** Moteur de collision sémantique — croisement fragments utilisateur × flux mondial
**F-TIS-05 :** Notifications asynchrones de type "collision détectée" — format non-didactique
**F-TIS-06 :** Fréquence des notifications configurable (pas de spam)
**F-TIS-07 :** Explication du raisonnement de collision disponible sur demande UNIQUEMENT

### 3.5 Module VISION DU MONDE

**F-VIS-01 :** Construction progressive de l'archétype affiné à partir des interactions
**F-VIS-02 :** Détection de boucles cognitives — "tu m'as dit exactement ça le [date]"
**F-VIS-03 :** Introduction de "bruit utile" pour casser les bulles algorithmiques
**F-VIS-04 :** Adaptation du mode de stimulation selon le profil :
  - Dispersé → connecter des domaines
  - En boucle → révéler le cercle
  - En bulle → ouvrir des angles tangentiels
**F-VIS-05 :** Timeline d'accumulation des informations — vision diachronique
**F-VIS-06 :** Stockage des problèmes supposés, bonheurs supposés, sans jamais les présenter comme diagnostic
**F-VIS-07 :** Seuil d'arrêt thérapeutique — quand le S2 détecte du matériel dépassant la construction intellectuelle

### 3.6 Module VIRALITÉ

**F-VIR-01 :** Génération de lien d'invitation avec description custom de l'invité
**F-VIR-02 :** Mode signé (nom de l'inviteur visible) et mode anonyme
**F-VIR-03 :** Pré-archétype construit à partir de la description d'invitation
**F-VIR-04 :** Premier message de l'invité intègre le profilage inversé basé sur le pré-archétype

### 3.7 Module DONNÉES & CONFIDENTIALITÉ

**F-DAT-01 :** Architecture local-first par défaut
**F-DAT-02 :** Sync cloud FR optionnel (consentement explicite, hébergement souverain)
**F-DAT-03 :** Données stockées : embeddings, graphe, texte. Jamais d'audio, jamais d'images.
**F-DAT-04 :** Oubli sélectif configurable — nœuds vieillissent, perdent du poids, disparaissent si non réactivés
**F-DAT-05 :** Export complet des données (portabilité RGPD)
**F-DAT-06 :** Suppression complète sur demande (droit à l'oubli)
**F-DAT-07 :** Visualisation de l'archétype et des données stockées sur demande

---

## 4. Exigences Non-Fonctionnelles

Voir documents dédiés :
- `02_EXIGENCES/EXIGENCES_LEGALES.md`
- `02_EXIGENCES/EXIGENCES_ETHIQUES.md`
- `02_EXIGENCES/EXIGENCES_SECURITE.md`
- `02_EXIGENCES/EXIGENCES_PERFORMANCE.md`

---

## 5. Hors Périmètre (MVP)

- Analyse d'images / photos
- Intégration calendrier (au-delà de rappels basiques)
- Mode multi-utilisateur / collaboratif
- Marketplace de "visions du monde"
- Monétisation par publicité (interdite par design)
