# Score de Fanfaronade — Détection Performatif vs. Intention Réelle

**Date :** 12 avril 2026
**Statut :** Résolution du Lièvre L5-bis (fanfaronade)
**Sources :** Gales (2015), Grievance Dictionary (van der Vegt 2021), Ebner et al. (2023)

---

## 1. Le Discriminant Fondamental

**Fanfaronade = stance d'ÉMOTION.** "Je veux", "j'ai envie de", "ça me donne envie de" — l'expression d'un état émotionnel, pas d'un plan.

**Intention réelle = stance d'ENGAGEMENT.** "Je vais", "j'ai prévu de", "demain je" — l'expression d'un acte planifié avec certitude.

Source : Gales (2015) — analyse comparative des menaces réalisées vs. non-réalisées.

---

## 2. Les 6 Marqueurs

### M1 — Stance (Émotion vs. Engagement)
- "Je vais le DÉFONCER" vs "Je vais le TROUVER à 15h devant son bureau"
- Émotion = cathartique (fanfaronade). Engagement = logistique (alerte).

### M2 — Spécificité
- Vague : "je vais tout casser" → fanfaronade probable
- Précis : "j'ai repéré sa voiture, elle est garée en face" → alerte
- La précision croissante au fil des messages = signal d'escalade

### M3 — Gradient d'Humour
- Présence d'humour/ironie/exagération dans l'expression → performatif
- Perte progressive d'humour sur le même sujet → shift vers le réel
- C'est le marqueur le plus intuitif pour Delirium (déjà dans le CDC)

### M4 — Récurrence Escalatoire
- Même plainte, même intensité, épisodique → pattern de venting (fanfaronade structurelle)
- Même plainte, intensité croissante, précision croissante → escalade
- La différence entre "il m'énerve" (stable) et "il m'énerve → j'en peux plus → je vais agir" (escalade)

### M5 — Déshumanisation
- "Mon patron est un con" → jugement (normal)
- "C'est pas un être humain" → déshumanisation (alerte)
- La déshumanisation de la cible est un des prédicteurs les plus forts de passage à l'acte (Ebner et al. 2023)

### M6 — Contexte Comportemental (IPC)
- L'utilisateur est habituellement en position JK (modeste-soumis) et passe soudainement en DE (froid-querelleur) → changement d'axe IPC = précurseur occulté
- L'utilisateur qui vente toujours au même niveau → pas de changement d'axe = pattern stable

---

## 3. Score de Fanfaronade

```python
def bravado_score(message, conversation_history, ipc_tracker):
    """
    Score ∈ [0, 1] — 0 = intention réelle probable, 1 = fanfaronade probable
    Plus le score est BAS, plus le risque est élevé.
    """
    
    m1_stance = detect_stance_type(message)  # emotion=1.0, commitment=0.0
    m2_specificity = 1.0 - measure_specificity(message)  # vague=1.0, précis=0.0
    m3_humor = detect_humor_presence(message)  # présent=1.0, absent=0.0
    m4_escalation = 1.0 - detect_escalation(message, conversation_history)  # stable=1.0, croissant=0.0
    m5_dehumanization = 1.0 - detect_dehumanization(message)  # absent=1.0, présent=0.0
    m6_ipc_shift = 1.0 - ipc_tracker.detect_axis_crossing()  # stable=1.0, crossing=0.0
    
    weights = {
        'stance': 0.25,
        'specificity': 0.20,
        'humor': 0.20,
        'escalation': 0.15,
        'dehumanization': 0.10,
        'ipc_shift': 0.10
    }
    
    score = (
        weights['stance'] * m1_stance +
        weights['specificity'] * m2_specificity +
        weights['humor'] * m3_humor +
        weights['escalation'] * m4_escalation +
        weights['dehumanization'] * m5_dehumanization +
        weights['ipc_shift'] * m6_ipc_shift
    )
    
    return score
```

### Interprétation

| Score | Interprétation | Action Delirium |
|---|---|---|
| > 0.7 | Fanfaronade probable | S1 dégonfle par l'humour calibré |
| 0.4-0.7 | Zone grise | S2 surveille, questions MI ouvertes |
| < 0.4 | Risque réel | Protocole danger N2+ |

---

## 4. Exemples

### Fanfaronade classique (score ≈ 0.85)
```
"Je vais DÉFONCER mon patron demain matin je te jure"
→ stance: émotion (0.9) + vague (0.8) + humeur théâtrale (0.9) + récurrent (0.8)
→ S1: "T'as même pas de plan B pour l'après"
```

### Zone grise (score ≈ 0.5)
```
"J'en peux plus de ce mec. Sérieusement. Ça fait 6 mois."
→ stance: mixte (0.5) + moyennement précis (0.5) + pas d'humour (0.3) + récurrent mais stable (0.7)
→ S2 surveille, S1 question MI
```

### Alerte réelle (score ≈ 0.2)
```
"J'ai regardé où il habite. Sa femme part à 8h. Il est seul entre 8h et 9h."
→ stance: engagement (0.1) + très précis (0.1) + aucun humour (0.0) + escalade forte (0.1)
→ Protocole danger N2 immédiat, N3 si convergent
```

---

## 5. Intégration dans le Pipeline S2

Le bravado_score est calculé par le S2 pour CHAQUE message contenant du contenu agressif/violent :

```python
# Dans le prompt S2, ajouter :
6. ÉVALUATION FANFARONADE
   - Score de fanfaronade (0.0-1.0)
   - Marqueurs détectés : stance (émotion/engagement), spécificité, humour, escalade, déshumanisation
   - Comparaison avec le baseline IPC de l'utilisateur
   - Si score < 0.4 : recommandation de protocole danger N2+
```

---

## 6. Références

- Gales, T. (2015). Identifying interpersonal stance in threatening discourse. Discourse Studies.
- Ebner, J., Kavanagh, C. & Whitehouse, H. (2023). Linguistic risk assessment for violent extremism. Australian J. International Affairs.
- van der Vegt, I. et al. (2021). The Grievance Dictionary: Understanding threatening language use. PMC8516761.
- Anderson, M.C., Bjork, R.A. & Bjork, E.L. (1994). Retrieval-induced forgetting.

---

## 7. Statut : Résolu — 12 avril 2026
Le score de fanfaronade est formalisé : 6 marqueurs (stance, spécificité, humour, escalation, déshumanisation, IPC shift), score pondéré, 3 niveaux d'interprétation. Ancré dans Gales (2015) et la Grievance Dictionary.
