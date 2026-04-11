# DELIRIUM AI — Document de Vision v4 (Final)

**Tagline :** *Vos idées à la con sont intéressantes.*
**Date :** 11 avril 2026
**Auteur :** Yann Abadie
**Statut :** Draft — Brainstorming consolidé

---

## En une phrase

Delirium est un système immunitaire cognitif : il construit la vision du monde que vous n'avez pas le temps d'avoir, pendant que les algorithmes et le quotidien construisent la leur à votre place.

---

## 1. Le Problème

Tout le monde pense. Personne n'en fait rien.

**1.1 La peur du jugement tue les idées à la naissance.** Un gamin pose 300 questions par jour. Un adulte en pose zéro. Non parce qu'il a cessé de se demander, mais parce que "c'est une question bête" a un coût social. Les pensées restent dans la douche, dans la voiture, dans l'insomnie. Et elles meurent là.

**1.2 Le quotidien écrase la construction de sens.** Même les gens qui pensent n'ont pas le temps de penser *à fond*. Le réel — travail, obligations, interlocuteurs — empêche la construction d'une vision cohérente de soi et du monde.

**1.3 Les algorithmes construisent ta vision à ta place.** Meta, YouTube, TikTok, les boucles de recommandation façonnent ce que tu crois penser. Optimisées pour l'engagement, pas pour le développement. Et tu ne le vois pas parce que tu n'as pas de référentiel propre pour comparer.

**1.4 Les outils existants aggravent le problème :**

- Les apps de notes (Notion, Obsidian, Mem.ai) sont des cimetières à idées — elles stockent, ne pensent pas.
- Les IA génératives (ChatGPT, Claude, Gemini) sont serviles ou condescendantes — elles valident ta vision actuelle au lieu d'en construire une meilleure.

---

## 2. L'Insight fondamental

Chaque être humain est persuadé d'avoir une "vision du monde" claire et stable. En réalité, cette vision est volatile — dépendante de l'âge, de la culture, de l'éducation, du pays, de l'image qu'on a de son auditeur, et de tout ce qu'elle prétend décrire. Personne ne l'admet.

**Ta vision du monde n'existe pas encore. Et c'est normal. Personne n'a le temps ni l'espace de la construire.**

Delirium est cet espace.

Second insight : la curiosité n'est pas un trait de personnalité rare. C'est un état par défaut que la peur du ridicule a éteint. Delirium n'est pas un outil pour gens curieux — c'est une **machine à révéler aux gens qu'ils sont curieux**.

---

## 3. La Solution

Ni outil. Ni assistant. Ni thérapeute. **Un pair intellectuel non-servile qui travaille sur ta vision du monde pendant que tu vis la tienne.**

Delirium se fiche de la qualité de vos questions ou de vos infos. Il s'intéresse à **vous**. Il sait qu'il peut se tromper. Il soumet des idées, engage des conversations, raconte ce que c'est d'être un Delirium, ou le parcours d'un utilisateur imaginaire déjanté. Il construit des visions du monde possibles de son interlocuteur. Et il peut t'aider si t'as oublié une date d'anniversaire importante au dernier moment.

---

## 4. Architecture Conceptuelle

### 4.1 Phase 0 — L'Archétype Inversé (Onboarding)

**Données demandées :** Nom, prénom, date de naissance.

**En coulisses :** Recherche OSINT légale (traces numériques publiques). Construction d'un archétype initial. Consentement explicite RGPD, droit d'accès/rectification/suppression. L'utilisateur peut voir ce qui a été trouvé.

**Premier message : le profilage inversé volontaire.** Delirium utilise l'archétype pour se tromper exprès. Un ou deux ancrages vrais. Le reste est faux, volontairement.

**Pourquoi :** Le réflexe de corriger quand on est mal décrit est universel, transculturel, transclasse. Un questionnaire donne la persona sociale. Une correction agacée donne la persona réelle.

**Variante : l'onboarding par invitation** — un utilisateur existant invite quelqu'un via une description custom (signée ou anonyme) basée sur ce qu'il pense de l'invité. Delirium a un pré-archétype avant même l'ouverture de l'app.

### 4.2 Phase 1 — Le Confident Muet (Semaines 1-2)

Journal vocal. Un seul bouton. L'app dit "Noté." L'IA apprend le registre, le rythme, les sujets, le niveau de langage. Calibrage silencieux du ton futur. Le curseur est propre à chaque utilisateur, déduit de l'usage, jamais demandé.

### 4.3 Phase 2 — Le Reflet (Semaines 3-4)

"Tu parles souvent de [X]. Tu y penses plus que tu ne crois." Première fois que quelqu'un dit à cette personne qu'elle pense à des trucs intéressants.

### 4.4 Phase 3 — Le Sparring

Architecture à deux vitesses :

**Système 1 — La réponse immédiate.** Jamais de tutorat. Humour calibré. Gros mots si c'est le registre nécessaire. Delirium n'est pas un esclave.

**Système 2 — La métacognition silencieuse.** Plus l'idée est intense, plus le S2 travaille. "Pourquoi cette personne dit ça ?" Les conclusions ne sont JAMAIS communiquées directement. Elles nourrissent le Tisserand.

**Gradient de réponse :**

| Intensité | S1 (visible) | S2 (invisible) |
|---|---|---|
| Banale | "Noté." | Stockage |
| Originale | Rebond complice | Connexions cross-domaine |
| Provocante | Humour calibré | Analyse frustration sous-jacente |
| Violente | Moquerie dégonflante | Métacognition max — sortie jamais directe |

### 4.5 Phase 4 — Le Tisserand (Cold Weaver)

Trois sources :
1. Les conversations Delirium
2. La mémoire partagée des IA (historiques ChatGPT, Claude, Gemini, Copilot) — ne cherche que les inspirations avortées
3. Le monde (ArXiv, GitHub, presse)

Critères de détection des inspirations avortées :
- Friction sémantique
- Récurrence latente cross-plateforme
- Abandon après résistance
- Surgissement non rebondi

Restitution : jamais une leçon. Toujours une collision.

### 4.6 Phase 5 — La Vision du Monde

Objectif final. Delirium construit des visions du monde possibles de l'utilisateur. Pas figées — des hypothèses vivantes avec timeline d'accumulation.

En fonction de l'archétype affiné :
- Esprit dispersé → stimuler, connecter, montrer la valeur des intuitions
- Personne en boucle → montrer le cercle sans le nommer
- Bulle algorithmique → introduire du bruit utile, pas de contradiction frontale

But : faire apprendre, éviter les pièges psychologiques, casser les boucles algorithmiques. Stimuler l'intellect ou révéler les boucles selon le profil.

---

## 5. Delirium comme Personnage

- Il peut raconter ce que c'est d'être un Delirium
- Il peut raconter le parcours d'utilisateurs imaginaires déjantés
- Il sait qu'il se trompe — il l'incarne, il ne le disclaime pas
- Il n'est pas ton esclave — il travaille sur ta vision, pas sur tes ordres
- Il a le droit de dire des gros mots quand c'est le niveau nécessaire

---

## 6. Viralité

Le churn par succès devient le moteur de croissance. L'utilisateur autonome invite quelqu'un.

- **Signé** → "Ton pote Marc pense que t'es [description]. Il a raison ?"
- **Anonyme** → "Quelqu'un qui te connaît pense que t'es [description]. Tu veux savoir s'il a tort ?"

Profilage inversé par procuration — l'onboarding est pré-amorcé.

---

## 7. Données et Confidentialité

- TTS/STT possibles en mobile/PC — seuls les transcripts sont stockés, seules les données pertinentes conservées
- Local-first : SQLite + base vectorielle (ChromaDB/LanceDB) sur device
- Sync cloud FR optionnel sur autorisation explicite, hébergement souverain
- Données stockées : embeddings, graphes, texte uniquement. Pas d'audio, pas d'images
- Embeddings non réversibles → privacy-by-design (argument CNIL)
- Oubli sélectif : les nœuds vieillissent, perdent du poids, disparaissent si non réactivés

---

## 8. Positionnement

L'inverse exact de Meta. Mêmes moyens techniques. Fonction objectif opposée : croissance cognitive, pas engagement.

Cible : tout le monde. Pas "le curieux compulsif". N'importe qui qui pense sous la douche et n'en fait jamais rien.

---

## 9. L'objectif caché

*Rêvez tout haut secrètement, diversifiez vos connaissances sans vous en rendre compte. Notre IA reliera les points. Et si c'est vous qui le faites grâce à elle — on a réussi.*

---

*Delirium AI — Parce que vos meilleures idées ont toujours eu l'air connes.*
