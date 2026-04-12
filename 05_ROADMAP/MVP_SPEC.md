# Spécification MVP — Delirium AI

**Version :** 1.0 | **Date :** 11 avril 2026
**Scope :** Ce qui est IN et OUT du MVP mobile (Phase 1)

---

## 1. In Scope MVP

| Feature | Description | Priorité |
|---|---|---|
| Mono-bouton vocal | Appui = record, relâche = stop, transcript | P0 |
| Saisie texte | Alternative au vocal | P0 |
| Whisper STT local | Transcription on-device, audio purgé | P0 |
| Onboarding archétype inversé | Nom/prénom/DOB → OSINT → premier message erroné | P0 |
| Phase Confident Muet | 2 semaines, réponses minimales | P0 |
| Phase Reflet | Détection thèmes récurrents, feedback doux | P0 |
| Phase Sparring S1 | Humour calibré, gradient de réponse | P0 |
| S2 métacognitif | Analyse asynchrone, jamais affichée | P1 |
| SQLite local chiffré | Stockage transcripts + métadonnées | P0 |
| Base vectorielle locale | Embeddings des fragments | P1 |
| Calibrage registre | Détection automatique du ton approprié | P1 |
| Seuil d'arrêt thérapeutique | Détection crise, arrêt humour | P0 |

## 2. Out of Scope MVP

| Feature | Phase prévue |
|---|---|
| Cold Weaver (veille ArXiv/GitHub) | Phase 2 |
| Import historiques IA | Phase 2 |
| Détection inspirations avortées | Phase 2 |
| Notifications collision | Phase 2 |
| Module Vision du Monde | Phase 2 |
| Système d'invitation | Phase 3 |
| Sync cloud | Phase 3 |
| TTS réponses | Phase 3 |
| App desktop | Phase 3 |
| Multilingue | Phase 4 |

## 3. Métriques de Succès MVP

| Métrique | Cible | Mesure |
|---|---|---|
| Rétention J1 | > 70% | Retour dans l'app le lendemain |
| Rétention J7 | > 40% | Retour dans la semaine |
| Rétention J30 | > 20% | Retour dans le mois |
| Sessions/semaine | > 3 | Moyenne par utilisateur actif |
| Durée session moyenne | > 2 min | Temps entre ouverture et fermeture |
| Correction onboarding | > 70% | % d'utilisateurs qui corrigent le profilage inversé |
| Satisfaction registre | > 60% | % d'utilisateurs jugeant le ton approprié (survey) |

## 4. Stack MVP

```
Mobile : Flutter + Whisper.cpp + SQLCipher + ChromaDB-lite
Backend : FastAPI + MiniMax M2.7 API (OpenAI-compatible, MINIMAX_API_KEY)
OSINT : Module Python léger (APIs publiques)
Infra : 1 serveur Scaleway (Paris)
```

## 5. Équipe MVP Minimale

| Rôle | Profil | Temps |
|---|---|---|
| Lead Dev Mobile | Flutter + natif audio | Full-time |
| Lead Dev Backend | Python + LLM + prompt engineering | Full-time |
| UX/Product | Minimaliste, conversational UI | Mi-temps |
| Juridique | RGPD, OSINT, CGU | Consulting ponctuel |
