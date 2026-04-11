# Détection d'Inspirations Avortées — Spécification

**Version :** 1.0 | **Date :** 11 avril 2026

---

## 1. Définition

Une **inspiration avortée** est un fragment conversationnel humain-IA où un signal cognitif réel existait (association nouvelle, connexion inattendue, intuition) mais où la boucle s'est cassée avant de produire une idée exploitable.

Causes de l'avortement :
- LLM sycophante ("bonne idée !") → validation creuse, pas d'approfondissement
- Malentendu IA → la réponse à côté contenait un concept intéressant non vu
- Formulation chaotique → l'utilisateur ne savait pas ce qu'il disait de valable
- Abandon par friction → l'IA résiste, l'utilisateur lâche
- Récurrence non reliée → la même intuition revient sous des formes différentes sans connexion

---

## 2. Les 4 Critères de Détection

### 2.1 Friction Sémantique
- **Quoi :** Distance cosinus élevée entre l'embedding de la question et celui de la réponse
- **Seuil :** > 0.6 (configurable)
- **Interprétation :** L'IA a compris de travers → le malentendu est peut-être plus intéressant que l'intention
- **Limite :** Beaucoup de faux positifs. Doit être croisé avec les autres critères.

### 2.2 Récurrence Latente
- **Quoi :** Clustering HDBSCAN des fragments utilisateur cross-plateforme
- **Condition :** Cluster de ≥3 fragments, ≥2 sources différentes, formulations différentes
- **Interprétation :** L'utilisateur tourne autour d'un thème qu'il n'arrive pas à nommer
- **Signal fort :** C'est le critère le plus fiable — une obsession récurrente cross-plateforme est un vrai signal

### 2.3 Abandon Après Résistance
- **Quoi :** Séquence insistance → reformulation → reformulation → changement de sujet
- **Détection :** Fenêtre glissante de 5 messages, comptage des reformulations sur le même topic
- **Interprétation :** L'idée a été tuée par la friction, pas par sa médiocrité
- **Nuance :** Distinguer l'abandon par lassitude (faible signal) de l'abandon par frustration (fort signal)

### 2.4 Surgissement Non Rebondi
- **Quoi :** L'IA introduit un concept que l'utilisateur n'a jamais mentionné. L'utilisateur ne rebondit pas. Mais ce concept matche avec un fragment ultérieur (autre conversation/plateforme).
- **Détection :** Extraction de concepts nouveaux dans les réponses IA → recherche dans les conversations futures
- **Interprétation :** L'IA a "vu" quelque chose que l'utilisateur n'a pas capté sur le moment
- **Limite :** Nécessite un historique suffisant pour détecter les matches futurs

---

## 3. Scoring et Priorisation

```python
class InspirationScore:
    friction_score: float       # 0.0 - 1.0
    recurrence_score: float     # 0.0 - 1.0 (nombre de récurrences normalisé)
    abandonment_score: float    # 0.0 - 1.0 (intensité de la résistance)
    emergence_score: float      # 0.0 - 1.0 (distance temporelle du match)
    
    @property
    def composite_score(self):
        weights = {
            'friction': 0.15,     # Beaucoup de faux positifs
            'recurrence': 0.40,   # Signal le plus fiable
            'abandonment': 0.25,  # Bon signal
            'emergence': 0.20    # Intéressant mais nécessite historique
        }
        return sum(getattr(self, k+'_score') * v for k, v in weights.items())
```

Seuil de qualification : composite_score > 0.5

---

## 4. Limites et Risques

- **Faux positifs :** Inévitables. Le taux acceptable est < 30% des fragments qualifiés.
- **Biais de volume :** Les utilisateurs bavards produiront plus de fragments → normaliser par volume.
- **Biais de plateforme :** ChatGPT encourage les échanges longs, Claude les échanges structurés → les patterns d'abandon diffèrent.
- **Privacy :** Les historiques importés sont traités localement uniquement. Pas de transmission au cloud.
