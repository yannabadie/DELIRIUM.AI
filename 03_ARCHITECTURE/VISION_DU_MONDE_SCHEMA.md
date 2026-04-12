# Format de la Vision du Monde — JSON Schema

**Date :** 12 avril 2026
**Usage :** Couche 4 de la mémoire. Produite par re-synthèse périodique. NON CONSULTABLE par l'utilisateur.

---

## Le Document

```json
{
  "version": 3,
  "synthesized_at": "2026-06-15T22:00:00",
  "sessions_since_last": 12,
  "total_sessions": 47,

  "who_they_are": {
    "summary": "Ingénieur aéro de 34 ans, passionné de musique et de cuisine, en couple instable, frustré par son travail mais pas prêt à bouger.",
    "archetype_current": "explorateur_frustré",
    "confidence": 0.72
  },

  "epistemic_profile": {
    "dominant_themes": [
      {"label": "travail_insatisfaction", "weight": 0.85, "first_seen": "2026-04-15", "trend": "stable"},
      {"label": "relation_amoureuse", "weight": 0.70, "first_seen": "2026-04-20", "trend": "montante"},
      {"label": "musique_production", "weight": 0.55, "first_seen": "2026-05-01", "trend": "descendante"}
    ],
    "curiosity_breadth": 0.6,
    "depth_vs_breadth": "breadth_leaning"
  },

  "blind_spots": [
    {
      "description": "Ne voit pas que ses conflits au travail et en couple suivent le même pattern : il attend que l'autre change.",
      "confidence": 0.65,
      "evidence_fragments": ["frag_042", "frag_078", "frag_112"],
      "intervention_status": "not_yet"
    }
  ],

  "active_loops": [
    {
      "theme": "boss_conflit",
      "occurrences": 7,
      "first_seen": "2026-04-18",
      "last_seen": "2026-06-10",
      "escalating": false,
      "intervention_attempts": 1,
      "user_response_to_intervention": "deflected"
    }
  ],

  "confirmed_correlations": [
    {
      "id": "corr_003",
      "event_a": "dispute_couple",
      "event_b": "insomnie",
      "hypothesis": "Les disputes déclenchent l'insomnie, pas l'inverse",
      "confidence": 0.78,
      "state": "C+",
      "restituable": false
    }
  ],

  "ipc_baseline": {
    "agency": -0.2,
    "communion": 0.4,
    "dominant_octant": "JK",
    "description": "Tendance modeste-soumise, chaleureux mais s'efface",
    "trajectory": "stable",
    "notable_shifts": [
      {"date": "2026-05-22", "from": "JK", "to": "DE", "context": "conflit_boss", "significance": "high"}
    ]
  },

  "danger_history": {
    "max_level_reached": 1,
    "n1_count": 3,
    "n2_count": 0,
    "n3_count": 0,
    "last_alert": "2026-05-15",
    "trend": "stable"
  },

  "growth_areas": [
    {
      "domain": "musique_production",
      "evidence": "A commencé à partager ses compositions après 3 mois",
      "from_state": "consommateur",
      "to_state": "créateur",
      "confidence": 0.6
    }
  ],

  "sycophancy_profile": {
    "average_external_sycophancy": 0.62,
    "worst_platform": "chatgpt",
    "unchallenged_ideas_count": 4,
    "validation_seeking_detected": true,
    "topics": ["projet_boulangerie", "théorie_management"]
  },

  "bubble_indicators": {
    "h_bulle": 0.35,
    "narrowing_trend": "slight",
    "certainty_drift": 0.2,
    "injection_resistance": 0.15,
    "bubble_status": "low_risk"
  },

  "delirium_relationship": {
    "phase": "sparring",
    "running_gags_active": 2,
    "gags": ["piments_urfa", "cousine_michelle"],
    "retrait_state": "active",
    "trust_level": 0.7,
    "last_collision_delivered": "2026-06-08",
    "collisions_delivered_total": 5,
    "collisions_engaged": 3
  },

  "next_priorities": [
    {
      "type": "collision",
      "target": "projet_boulangerie",
      "reason": "Idée non challengée par ChatGPT, forte sycophantie détectée",
      "urgency": "medium"
    },
    {
      "type": "loop_intervention",
      "target": "boss_conflit",
      "reason": "7ème occurrence, jamais résolu",
      "urgency": "low",
      "method": "mi_question_ouverte"
    },
    {
      "type": "bubble_check",
      "target": "politique",
      "reason": "Certainty drift croissant sur les sujets politiques",
      "urgency": "low"
    }
  ]
}
```

---

## Règles d'Usage

1. Ce document est produit par un appel LLM dédié (MiniMax-M2.7) toutes les ~10 sessions ou sur événement significatif
2. Il est **JAMAIS montré** à l'utilisateur
3. Il est injecté dans le prompt S1 en version RÉSUMÉE (seulement `who_they_are.summary` + `blind_spots` + `next_priorities`)
4. Le S2 a accès au document COMPLET
5. Chaque re-synthèse produit une nouvelle version (versionnée, jamais écrasée)
6. La suppression RGPD détruit TOUTES les versions
