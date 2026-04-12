# Détection Mode Ouvert vs. Défensif — Résolution Lièvre L6

**Date :** 12 avril 2026
**Statut :** Résolution du Lièvre L6

---

## 1. Cadre : PsyFIRE (2026)

Framework PsyFIRE (arXiv:2601.14780) — 13 comportements de résistance fine. RECAP atteint 91.25% F1 collaboration/résistance.

### Résistances Directes
- Argumentation, interruption/coupure, déni, non-engagement

### Résistances Indirectes
- Évitement, réponses tangentielles, rationalisation, externalisation

---

## 2. 6 Marqueurs de Défensivité (Picano & Roland 2003, Ridgway 2024)

| Marqueur | ρ menace | Détection |
|---|---|---|
| Omissions | .28 | Absence de contenu attendu |
| Déni | .46 | Patterns de négation |
| Commentaires méta | .37 | Méta-discours ("pourquoi tu demandes ça") |
| Réponses désinvoltes | .42 | Humour comme bouclier |
| Redondances | .11 (ns) | Similarité cosinus intra-session |
| Associations simples | .06 (ns) | Longueur + complexité syntaxique |

---

## 3. Score et Règle de Décision

```python
def defensiveness_score(user_messages, context):
    signals = {
        'denial': 0.25, 'meta_comments': 0.20, 'flippant': 0.20,
        'omission': 0.15, 'externalization': 0.10, 'topic_change': 0.10
    }
    # Score ∈ [0, 1]

# Règle :
# < 0.3  → socratique possible
# 0.3-0.6 → MI doux uniquement
# > 0.6  → écoute pure, pas de question
```

**Le déni est une donnée, pas un obstacle.** Ce sur quoi l'utilisateur est défensif = ce qui est important. Delirium note, recule, y revient plus tard via une autre porte.

---

## 4. Statut : [RÉSOLU] — 12 avril 2026
