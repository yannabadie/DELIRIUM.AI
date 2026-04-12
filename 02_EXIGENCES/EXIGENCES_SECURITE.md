# Exigences Sécurité — Delirium AI

**Version :** 1.0 | **Date :** 11 avril 2026

---

## 1. Chiffrement

| Couche | Mécanisme | Standard |
|---|---|---|
| Base SQLite locale | SQLCipher | AES-256-CBC |
| Vault vectoriel local | Chiffrement fichier | AES-256-GCM |
| Transit API LLM | TLS 1.3 | Certificats pinning |
| Sync cloud | E2E encryption | Signal Protocol ou NaCl |
| Backup | Chiffré côté client avant upload | AES-256 + clé dérivée du mot de passe utilisateur |

## 2. Authentification

- Biométrie device (Face ID / Touch ID / empreinte) pour accès app
- PIN de fallback
- Pas de compte utilisateur centralisé pour le MVP (local-first)
- Si sync cloud : authentification par clé dérivée, pas de mot de passe stocké côté serveur

## 3. OSINT — Sécurité des Données Collectées

- Données OSINT chiffrées au repos comme toute autre donnée
- Pas de stockage de credentials, tokens, ou mots de passe découverts
- Pas de stockage de données sensibles (santé, religion, orientation) même si publiques
- Purge automatique des données OSINT brutes après construction de l'archétype
- Seul l'archétype synthétisé est conservé

## 4. Protection contre les Attaques

- Injection prompt : le S1/S2 utilise des system prompts non-modifiables par l'utilisateur
- L'utilisateur interagit en langage naturel, pas en commandes système
- Rate limiting sur les appels API LLM
- Pas d'exécution de code côté client basée sur les réponses LLM

## 5. Gestion des Clés

- Clé de chiffrement locale dérivée du PIN/biométrie (PBKDF2 ou Argon2)
- Pas de clé maître côté serveur
- Perte du device = perte des données (sauf si sync cloud activé)
- Rotation de clé API LLM gérée côté backend

## 6. Audit

- Logging des accès API (sans contenu des conversations)
- Pas de logging du contenu utilisateur côté serveur
- Audit de sécurité annuel recommandé
- Pen test avant lancement public

---

## 7. Logs d'Exécution (Obligatoires)

- Décisions S1, analyses S2, collisions Cold Weaver, transitions d'état, détections danger, signalements, changements persona
- **Chiffrement :** AES-256, clé dérivée du device
- **Conservation :** 12 mois standard, 36 mois danger N2+, vie du compte pour signalements
- **Suppression :** purgeable sauf logs danger N3 (conservation légale)
- **Portabilité :** exportable JSON chiffré

---

## 8. Données Spéciales

### Vision du Monde
- Donnée dérivée sensible, chiffrée, cloud optionnel E2E
- NON CONSULTABLE sauf maintenance auto
- Suppressible, non modifiable directement

### Features Paralingustiques
- Extraites avant transcription (débit, pauses, volume)
- Stockées comme delta par rapport à la baseline
- Audio brut purgé immédiatement

### Sécurité Proactive
- Check périodique HaveIBeenPwned API (hash uniquement)
- Notification utilisateur si credentials compromis
