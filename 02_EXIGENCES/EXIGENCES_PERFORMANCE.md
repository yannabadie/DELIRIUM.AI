# Exigences Performance — Delirium AI

**Version :** 1.0 | **Date :** 11 avril 2026

---

## 1. Latence

| Opération | Cible | Accepté | Critique |
|---|---|---|---|
| STT local (Whisper) | < 2s pour 30s audio | < 5s | > 10s |
| S1 — premier token | < 1s | < 2s | > 5s |
| S1 — réponse complète (streaming) | < 5s | < 10s | > 15s |
| S2 — analyse métacognitive | Asynchrone (pas de contrainte) | < 30s | N/A |
| OSINT onboarding | < 15s | < 30s | > 60s |
| Cold Weaver — batch | < 5min par run | < 15min | > 30min |
| Recherche dans le graphe local | < 500ms | < 1s | > 3s |

## 2. Stockage Device

| Composant | Budget | Notes |
|---|---|---|
| App + modèle Whisper | ~150 Mo | Whisper small = ~150 Mo |
| Base SQLite | < 50 Mo | Transcripts + métadonnées |
| Vault vectoriel | < 200 Mo | Embeddings + index |
| Graphe | < 50 Mo | Nœuds + arêtes |
| **Total** | **< 500 Mo** | Oubli sélectif si dépassement |

## 3. Bande Passante

- S1/S2 : ~1-5 Ko par requête (prompt) + ~1-5 Ko par réponse (streaming)
- Cold Weaver : ~100 Ko-1 Mo par batch (métadonnées ArXiv/GitHub)
- Sync cloud : delta uniquement, compressé, chiffré

## 4. Batterie

- STT local : impact modéré (~5-10% batterie pour 10 minutes d'enregistrement continu)
- Pas de tâche de fond permanente — Cold Weaver déclenché par CRON, pas par polling
- Mode économie configurable (réduction fréquence Cold Weaver)

## 5. Scalabilité Backend

- MVP : mono-serveur, ~1000 utilisateurs actifs
- Phase 2 : scaling horizontal des workers Cold Weaver
- Cible 12 mois : 50 000 utilisateurs actifs sans dégradation
