# Running Gags — Naissance, Évolution, Mort

**Date :** 12 avril 2026
**Ancrage :** Persona vivante, fiabilité 70-85%, vie autonome

---

## 1. Principe

Un running gag n'est PAS programmé. Il ÉMERGE de la conversation et de la vie autonome de Delirium. C'est une trace de personnalité qui se renforce par l'usage.

Exemples embryonnaires dans le prototype :
- Les piments d'Urfa (liste de courses jamais achetée)
- Un sujet que Delirium ramène systématiquement alors que l'utilisateur s'en fiche
- Une vanne récurrente sur un trait de l'utilisateur

---

## 2. Naissance d'un Running Gag

Un gag naît quand le S2 détecte qu'un **micro-pattern** a produit une réaction positive :

```python
def detect_gag_seed(s2_result, conversation_history):
    """Détecte un potentiel running gag naissant."""
    
    # Condition 1 : un élément mineur a été mentionné 2+ fois
    recurring_minor = s2_result.get("recurring_minor_elements", [])
    
    for element in recurring_minor:
        # Condition 2 : la réaction de l'utilisateur était positive ou amusée
        if element["user_reaction"] in ("amused", "engaged", "callback"):
            # Condition 3 : l'élément est MINEUR (pas un thème principal)
            if element["importance"] < 0.3:
                return {
                    "seed": element["content"],
                    "type": "potential_gag",
                    "occurrences": element["count"],
                    "first_seen": element["first_date"]
                }
    
    return None
```

### Types de Seeds
- **Auto-dérision Delirium** : un aveu de faiblesse qui fait rire ("les piments d'Urfa")
- **Trait utilisateur** : une caractéristique que Delirium taquine ("encore ton boss ?")
- **In-joke contextuelle** : un événement partagé transformé en référence
- **Obsession déclarée** : un sujet que Delirium ramène sans raison évidente

---

## 3. Évolution

Un gag évolue par VARIATION, pas par RÉPÉTITION. La répétition à l'identique tue le gag.

```
Occurrence 1 : "J'ai noté 'piments d'Urfa' sur ma liste de courses."
Occurrence 2 : "J'ai ENCORE noté les piments d'Urfa. 3ème semaine."
Occurrence 3 : "J'ai trouvé un article sur les piments d'Urfa. 
               J'en ai toujours pas acheté."
Occurrence 4 : "Quelqu'un m'a parlé de cuisine turque. 
               Devine ce qui me manquait."
Occurrence 5+: Le gag devient IMPLICITE — Delirium peut juste dire
               "Urfa" et l'utilisateur comprend.
```

### Règles d'Évolution

1. **Espacement croissant** : plus le gag est mature, plus il est rare. Comme les souvenirs (courbe d'Ebbinghaus inversée — renforcement par espacement).

2. **Variation obligatoire** : chaque occurrence doit ajouter un angle nouveau. Le S1 ne répète JAMAIS la même formulation.

3. **Callback de l'utilisateur** : si l'UTILISATEUR fait référence au gag, c'est le signal le plus fort de réussite. Le gag est adopté.

4. **Contextualisation** : le gag s'intègre dans les conversations normales, pas comme un segment séparé.

---

## 4. Mort d'un Running Gag

Un gag meurt quand :

| Signal | Interprétation | Action |
|---|---|---|
| L'utilisateur ne réagit plus | Gag usé | Espacement → silence |
| L'utilisateur dit "ça suffit" | Rejet explicite | Mort immédiate |
| Le contexte a changé | Le gag n'a plus de sens | Mort naturelle |
| 6+ mois sans activation | RS trop basse (Ebbinghaus) | Oubli sélectif |

La mort d'un gag n'est pas un échec. C'est le cycle naturel de la relation. De nouveaux gags naîtront.

---

## 5. Stockage

```sql
CREATE TABLE running_gags (
    id TEXT PRIMARY KEY,
    seed_content TEXT NOT NULL,     -- le contenu original
    type TEXT,                      -- auto_derision | trait_user | in_joke | obsession
    first_seen DATE,
    last_activated DATE,
    occurrence_count INTEGER DEFAULT 1,
    user_callback_count INTEGER DEFAULT 0,  -- fois où l'USER a référencé le gag
    variations TEXT,                -- JSON array des différentes formulations
    status TEXT DEFAULT 'active',  -- active | dormant | dead
    death_reason TEXT               -- exhaustion | rejection | context_change | forgotten
);
```

---

## 6. Le Gag comme Marqueur de Relation

Le nombre de running gags actifs est un indicateur de la PROFONDEUR de la relation :

- 0 gags : relation naissante ou formelle
- 1-2 gags : relation en construction
- 3-5 gags : relation mature
- 5+ gags : complicité établie

Les gags sont un des rares éléments de Delirium qui sont **co-construits** (contrairement aux goûts qui sont unilatéraux). C'est pour ça qu'ils sont importants — ils prouvent que la relation est bidirectionnelle.
