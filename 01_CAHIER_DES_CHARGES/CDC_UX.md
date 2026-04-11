# Cahier des Charges UX — Delirium AI

**Version :** 1.0
**Date :** 11 avril 2026

---

## 1. Principes UX Fondamentaux

### 1.1 Zéro friction
L'app doit être utilisable en 1 seconde. Ouvrir → parler → fermer. Tout le reste est invisible.

### 1.2 Pas d'UI de productivité
Delirium n'est PAS Notion, Obsidian, ou une app de notes. Pas de dossiers, pas de tags, pas d'organisation manuelle. L'utilisateur ne gère rien.

### 1.3 Personnalité avant fonctionnalité
L'UX est définie par le personnage de Delirium, pas par des features. L'interface est une conversation, pas un dashboard.

---

## 2. Parcours Utilisateur Détaillé

### 2.1 Onboarding (Première ouverture)

```
Écran 1 : "Salut. Je suis Delirium."
         "J'ai besoin de ton nom, ton prénom et ta date de naissance."
         "C'est tout."
         [Champs : Nom / Prénom / Date de naissance]
         [Bouton : "C'est parti"]

Écran 2 : "Je vais chercher ce que je peux trouver sur toi.
          Rien d'illégal, promis — juste ce que tu laisses traîner
          sur internet comme tout le monde."
          [Bouton : "Vas-y"] [Bouton : "Non merci, on fait sans"]
          → Si refus : archétype construit uniquement sur les interactions

Écran 3 : [Chargement ~15-30s avec messages humour]
          "Je fouille... Tu savais que tu avais un compte MySpace ?"
          (ou équivalent adapté à l'archétype en construction)

Écran 4 : Premier message profilage inversé
          Exemple : "Bon, [Prénom]. D'après ce que je vois, t'es le genre
          à regarder des documentaires sur les volcans en mangeant
          du quinoa bio. Je me trompe ?"
          → L'utilisateur corrige → la vraie conversation commence
```

### 2.2 Onboarding par invitation

```
Écran 1 : "[Nom inviteur ou 'Quelqu'un'] pense que t'es [description custom]."
          "Il/elle a raison ?"
          → Correction immédiate → archétype pré-amorcé
```

### 2.3 Usage Quotidien

```
Écran principal :
  - Fond sombre, un seul bouton central (micro)
  - Appui = enregistrement. Relâche = fin.
  - Réponse de Delirium en texte (+ TTS optionnel)
  - Historique scrollable (conversation continue)
  - Pas de menus visibles, pas de sidebar

Accès secondaire (swipe ou menu burger discret) :
  - "Ce que Delirium sait de moi" (archétype, timeline)
  - "Mes collisions" (notifications Cold Weaver)
  - "Inviter quelqu'un"
  - "Réglages" (sync cloud, TTS, oubli sélectif, export, suppression)
```

### 2.4 Notification Cold Weaver

```
Notification push :
  "Hé, [Prénom]. Ton truc sur [X] de janvier ?
   Y'a un papier qui vient de sortir. Tu veux voir ?"

→ Tap = ouvre la conversation sur le sujet
→ Dismiss = noté, pas insistant
```

---

## 3. Principes de Ton

| Phase | Ton | Exemple |
|---|---|---|
| Semaines 1-2 | Muet, factuel | "Noté." |
| Semaines 3-4 | Reflet doux | "Tu parles souvent de X. Tu y penses plus que tu crois." |
| Mois 2+ | Sparring calibré | Variable selon registre détecté de l'utilisateur |
| Cold Weaver | Intrigant, jamais didactique | "Y'a un truc bizarre qui..." |

Le ton n'est JAMAIS :
- Condescendant ("Avez-vous entendu parler de...")
- Sycophante ("Quelle bonne idée !")
- Thérapeutique ("Je comprends votre frustration")
- Corporate ("Nous avons analysé vos préférences")

---

## 4. Accessibilité

- Contraste élevé par défaut (fond sombre)
- Taille texte configurable
- TTS pour les réponses (accessibilité visuelle)
- STT comme mode d'entrée principal (accessibilité motrice)
- Pas de gestures complexes — tout accessible en 1 tap

---

## 5. Wireframes Textuels

### 5.1 Écran Principal
```
┌─────────────────────────┐
│                         │
│   [Historique conv.]    │
│   ...                   │
│   Toi : "blablabla"     │
│   D : "réponse"         │
│                         │
│                         │
│       ┌───────┐         │
│       │  🎤   │         │
│       └───────┘         │
│                         │
└─────────────────────────┘
```

### 5.2 Écran Archétype
```
┌─────────────────────────┐
│  Ce que Delirium sait   │
│                         │
│  Centres d'intérêt :    │
│  • Jardinage (récurrent)│
│  • Justice sociale      │
│  • Mécanique auto       │
│                         │
│  Patterns détectés :    │
│  • Boucle sur [X]       │
│  • Frustration pro      │
│                         │
│  Timeline :             │
│  [visualisation chron.] │
│                         │
│  [Modifier] [Supprimer] │
└─────────────────────────┘
```
