# Circumplex Interpersonnel (IPC) — Ancrage des Tendances Comportementales

**Date :** 12 avril 2026
**Statut :** Résolution du Lièvre L7
**Objectif :** Ancrer formellement les "tendances comportementales inconscientes en nombre limité" identifiées dans le brainstorming

---

## 1. Le Problème (L7)

Dans le CDC Comportemental, Yann identifie que les tendances comportementales inconscientes sont "en nombre limité" : domination, soumission, séduction. Cette intuition n'était pas sourcée. Elle l'est maintenant.

---

## 2. L'Interpersonal Circumplex (IPC)

### Historique
Développé par Timothy Leary en 1957, raffiné par Wiggins (1979) et Kiesler (1983). Le modèle le plus validé empiriquement en psychologie interpersonnelle.

### Principe
Tout comportement interpersonnel se décrit par **2 axes orthogonaux** :

```
                    DOMINANCE
                       ↑
                       |
    Hostile-     PA    |    NO    Warm-
    Dominant  ─────────┼─────────  Dominant
     (BC)      DE      |      LM   (NO)
                       |
   HOSTILITÉ ──────────┼────────── CHALEUR
                       |
     (DE)      FG      |      JK
    Hostile-  ─────────┼─────────  Warm-
    Submissive  HI     |          Submissive
                       |
                       ↓
                   SOUMISSION
```

**Axe vertical : AGENCY (Agentivité)** — Dominance → Soumission
**Axe horizontal : COMMUNION (Affiliation)** — Chaleur → Hostilité

### Les 8 Octants (Wiggins 1979)

| Code | Label | Comportement type |
|---|---|---|
| PA | Ambitieux-Dominant | Leadership, assertivité, prise de contrôle |
| BC | Arrogant-Calculateur | Manipulation, séduction stratégique, narcissisme |
| DE | Froid-Querelleur | Hostilité ouverte, agressivité, rejet |
| FG | Distant-Introverti | Retrait, évitement, isolement |
| HI | Paresseux-Soumis | Passivité, dépendance, soumission totale |
| JK | Modeste-Ingénu | Complaisance, docilité, abnégation |
| LM | Chaleureux-Agréable | Coopération, empathie, soutien |
| NO | Grégaire-Extraverti | Sociabilité, enthousiasme, recherche d'attention |

---

## 3. Mapping vers l'Intuition de Yann

| Tendance Yann | Octant(s) IPC | Axe principal |
|---|---|---|
| Domination | PA, BC | Agency haut |
| Soumission | HI, JK | Agency bas |
| Séduction | BC, NO | Communion positif + Agency variable |

La "séduction" n'est pas un 3ème axe — c'est un **blend** de dominance et chaleur (quadrant PA-NO-BC).

---

## 4. Principe de Complémentarité — Critique pour Delirium

DOMINANCE ←→ SOUMISSION (s'attirent). CHALEUR ←→ CHALEUR (se renforcent). HOSTILITÉ ←→ HOSTILITÉ (se renforcent).

**Implication persona :** Delirium ne doit PAS être complémentaire. Si l'utilisateur est soumis, un Delirium complémentaire serait dominant — renforçant le pattern. Delirium doit être **adjacent** : octant orthogonal (LM ou NO) pour briser le pattern.

---

## 5. Détection des Changements de Pattern

Changement DANS le même quadrant (PA → BC) = variation de degré → mécanisme habituel.
Changement qui TRAVERSE un axe (PA → HI) = changement de nature → précurseur occulté.

---

## 6. Implémentation — IPCTracker

```python
class IPCTracker:
    def __init__(self):
        self.positions = []
        self.baseline = None
        
    def update(self, timestamp, agency, communion):
        self.positions.append((timestamp, agency, communion))
        if len(self.positions) >= 10:
            self.baseline = self._compute_baseline()
    
    def detect_shift(self, threshold=0.3):
        if not self.baseline:
            return None
        current = self.positions[-1]
        delta_a = abs(current[1] - self.baseline[0])
        delta_c = abs(current[2] - self.baseline[1])
        if delta_a > threshold or delta_c > threshold:
            crosses = (current[1] * self.baseline[0] < 0 or 
                      current[2] * self.baseline[1] < 0)
            return {
                'type': 'axis_crossing' if crosses else 'degree_change',
                'implication': 'occluded_precursor' if crosses else 'contextual_variation'
            }
        return None
```

---

## 7. Références

- Leary, T. (1957). Interpersonal Diagnosis of Personality. Ronald Press.
- Wiggins, J.S. (1979). J. Personality and Social Psychology, 37, 395-412.
- Kiesler, D.J. (1983). Contemporary Directions in Psychopathology.
- Pincus, A.L. & Ansell, E.B. (2003). Handbook of Psychology.

## 8. Statut : [RÉSOLU] — 12 avril 2026
