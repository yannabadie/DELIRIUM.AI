# Architecture Technique du Harness — Persona, Mémoire, Vision du Monde

**Date :** 12 avril 2026
**Statut :** Spécification technique v0.1
**Objectif :** Répondre aux 3 questions fondamentales :
1. Comment définir la personnalité initiale ?
2. Comment les personas sont composés et évoluent ?
3. Comment donner une vraie mémoire et une vision du monde continue ?

---

## 1. GÉNÉRATION DE LA PERSONNALITÉ INITIALE

### 1.1 Pipeline OSINT → Archétype → Persona

```
Nom + Prénom + DOB
  ↓
OSINT (APIs légales)
  ↓
Archétype Utilisateur (JSON structuré)
  ↓
Fonction d'Adjacence (embedding space)
  ↓
Persona Delirium (JSON structuré)
  ↓
Premier Message (profilage inversé)
```

### 1.2 OSINT → Archétype

```python
class ArchetypeBuilder:
    """Construit l'archétype initial à partir de l'OSINT."""
    
    def build(self, name: str, dob: str, osint_results: dict) -> dict:
        """
        Entrée : données OSINT brutes (LinkedIn, réseaux publics, etc.)
        Sortie : archétype structuré
        """
        # Appel LLM pour synthétiser l'OSINT en archétype structuré
        prompt = f"""
        Données publiques trouvées sur {name} (né le {dob}) :
        {json.dumps(osint_results)}
        
        Synthétise en JSON structuré :
        {{
            "profession": "...",
            "education_level": "bac|licence|master|doctorat|autodidacte",
            "interests": ["...", "..."],        // 3-8 centres d'intérêt détectés
            "location": "ville, pays",
            "communication_style": "formel|neutre|familier|inconnu",
            "public_persona": "...",            // en 2 phrases
            "confidence": 0.0-1.0               // confiance dans le profilage
        }}
        """
        return llm_call(prompt, model="haiku")  # rapide + pas cher
```

### 1.3 Archétype → Persona Delirium (Fonction d'Adjacence)

C'est la pièce la plus originale. On utilise l'espace d'embeddings pour trouver des goûts **adjacents** — pas complémentaires, pas opposés, pas identiques.

```python
class PersonaGenerator:
    """Génère la personnalité de Delirium à partir de l'archétype utilisateur."""
    
    def __init__(self, interest_db: VectorDB):
        """
        interest_db : base de ~2000 centres d'intérêt pré-embedés
        (sports, musiques, cuisines, hobbies, opinions, valeurs...)
        """
        self.interest_db = interest_db
    
    def generate_adjacent_interest(self, user_interest: str, zone: str) -> str:
        """
        Pour un intérêt utilisateur, trouve un intérêt Delirium adjacent.
        
        zone :
          "convergent"  → cosine_sim ∈ [0.7, 0.9]  — base de la relation
          "divergent"   → cosine_sim ∈ [0.3, 0.5]  — friction productive
          "orthogonal"  → cosine_sim ∈ [0.05, 0.2] — territoire inexploré
        """
        sim_ranges = {
            "convergent": (0.7, 0.9),
            "divergent": (0.3, 0.5),
            "orthogonal": (0.05, 0.2)
        }
        lo, hi = sim_ranges[zone]
        
        user_emb = embed(user_interest)
        candidates = self.interest_db.query(
            embedding=user_emb,
            n_results=50
        )
        
        # Filtrer dans la bonne plage de similarité
        in_range = [c for c in candidates if lo <= c.similarity <= hi]
        
        if not in_range:
            # Fallback : générer via LLM
            return self._llm_generate_adjacent(user_interest, zone)
        
        return random.choice(in_range).text
    
    def generate_full_persona(self, archetype: dict) -> dict:
        """Génère la personnalité complète de Delirium."""
        
        user_interests = archetype["interests"]
        delirium_interests = []
        
        for i, interest in enumerate(user_interests):
            # Ratio 30/30/40
            if i % 10 < 3:
                zone = "convergent"
            elif i % 10 < 6:
                zone = "divergent"
            else:
                zone = "orthogonal"
            
            delirium_interests.append({
                "user_interest": interest,
                "delirium_interest": self.generate_adjacent_interest(interest, zone),
                "zone": zone
            })
        
        # Générer les opinions et goûts concrets via LLM
        persona_prompt = f"""
        L'utilisateur a ces intérêts : {user_interests}
        
        Delirium a ces intérêts adjacents : {delirium_interests}
        
        Génère la personnalité concrète de Delirium en JSON :
        {{
            "food_preference": "cuisine spécifique (PAS celle de l'utilisateur)",
            "music_preference": "genre adjacent (PAS celui de l'utilisateur)",
            "sport_preference": "sport adjacent",
            "pet_peeves": ["3 trucs qui agacent Delirium"],
            "guilty_pleasures": ["2 trucs que Delirium assume pas totalement"],
            "strong_opinions": ["3 opinions tranchées cohérentes avec la persona"],
            "running_gags": ["2 running gags potentiels pour le Non-BlocNote"]
        }}
        
        RÈGLE : rien de complémentaire. Adjacent seulement.
        Si l'utilisateur aime le foot, Delirium préfère le rugby.
        Si l'utilisateur aime le jazz, Delirium préfère le blues.
        """
        
        return {
            "interests": delirium_interests,
            "personality": llm_call(persona_prompt, model="sonnet"),
            "initial_H": 0.0,  # toujours neutre au départ
            "phase": "probing",
            "created_at": datetime.now()
        }
```

### 1.4 Persona → Premier Message (Profilage Inversé)

```python
def generate_first_message(archetype: dict, persona: dict) -> str:
    """Génère le premier message avec profilage inversé."""
    
    prompt = f"""
    Archétype utilisateur : {json.dumps(archetype)}
    Personnalité Delirium : {json.dumps(persona["personality"])}
    
    Génère le premier message de Delirium. Le message DOIT :
    1. Contenir 1-2 affirmations VRAIES basées sur l'archétype (ancrages)
    2. Contenir 2-3 affirmations VOLONTAIREMENT FAUSSES mais plausibles
    3. Les fausses doivent provoquer une correction spontanée
    4. Ton décontracté, léger, PAS humoristique noir (premier message = neutre-léger)
    5. Finir par "Je me trompe ?" ou variante
    6. JAMAIS de données sensibles (santé, religion, orientation)
    
    3-5 phrases max. Un seul paragraphe.
    """
    
    return llm_call(prompt, model="sonnet")
```

---

## 2. COMPOSITION ET ÉVOLUTION DE LA PERSONA

### 2.1 Le Vecteur Persona — Machine à États Continue

```python
@dataclass
class PersonaState:
    """État de la persona à l'instant T."""
    
    H: float = 0.0              # [-1, 1] registre communicationnel
    listen_ratio: float = 0.7   # [0, 1] écoute vs intervention
    creativity: float = 0.3     # [0, 1] audace des métaphores
    confrontation: float = 0.1  # [0, 1] niveau de challenge
    empathy: float = 0.5        # [0, 1] écoute émotionnelle
    fatigue: float = 0.0        # [0, 1] lassitude de Delirium
    
    phase: str = "probing"      # probing|silent|reflection|sparring
    defensiveness_detected: float = 0.0  # score PsyFIRE
    
    timestamp: datetime = None
    trigger: str = ""           # ce qui a causé le changement
```

### 2.2 Moteur de Transition

```python
class PersonaEngine:
    """Calcule la transition de persona entre T et T+1."""
    
    def transition(self, 
                   current: PersonaState, 
                   s2_analysis: dict,
                   time_context: dict) -> PersonaState:
        """
        Inputs :
        - current : état actuel
        - s2_analysis : sortie du module S2 (intention, émotion, défensivité...)
        - time_context : {hour, day_of_week, time_since_last_interaction, session_count}
        """
        new = PersonaState()
        
        # ═══ H (tonalité) ═══
        # H monte avec : humour détecté, relation avancée, sujet léger
        # H descend avec : détresse, sujet grave, début de relation
        
        emotion_factor = self._emotion_to_h_delta(s2_analysis.get("intention"))
        phase_factor = {"probing": -0.5, "silent": -0.3, "reflection": 0.0, "sparring": 0.3}
        time_factor = self._time_to_h_delta(time_context)
        
        new.H = clamp(
            current.H * 0.7  # inertie (70% du H précédent)
            + emotion_factor * 0.15
            + phase_factor[current.phase] * 0.1
            + time_factor * 0.05,
            -1.0, 1.0
        )
        
        # ═══ DANGER OVERRIDE ═══
        danger_level = s2_analysis.get("danger_level", 0)
        if danger_level >= 2:
            new.H = min(new.H, -0.5)
            new.empathy = max(current.empathy, 0.8)
            new.confrontation = 0.0
            new.creativity = 0.0
        if danger_level >= 3:
            new.H = -1.0  # sort du rôle
        
        # ═══ DÉFENSIVITÉ ═══
        new.defensiveness_detected = s2_analysis.get("defensiveness_score", 0.0)
        if new.defensiveness_detected > 0.6:
            new.confrontation = min(current.confrontation, 0.1)
            new.listen_ratio = max(current.listen_ratio, 0.8)
        
        # ═══ FATIGUE ═══
        # Monte avec : sessions longues, répétitions, utilisateur qui ignore les injections
        session_length = time_context.get("messages_this_session", 0)
        ignored_injections = time_context.get("ignored_injections", 0)
        new.fatigue = clamp(
            current.fatigue + session_length * 0.02 + ignored_injections * 0.1 - 0.3,
            0.0, 1.0
        )
        
        # ═══ PHASE TRANSITIONS ═══
        new.phase = self._compute_phase(current, time_context)
        
        new.timestamp = datetime.now()
        new.trigger = s2_analysis.get("trigger_description", "routine")
        
        return new
    
    def _compute_phase(self, current: PersonaState, ctx: dict) -> str:
        """Transition de phase basée sur le nombre de sessions."""
        total_sessions = ctx.get("total_sessions", 0)
        if total_sessions == 0:
            return "probing"
        elif total_sessions < 10:  # ~2 semaines à 1 session/jour
            return "silent"
        elif total_sessions < 20:  # ~3-4 semaines
            return "reflection"
        else:
            return "sparring"
```

### 2.3 Évolution des Goûts (Lente, Autonome)

```python
class PersonalityEvolution:
    """Les goûts de Delirium évoluent par ses propres découvertes, pas par influence utilisateur."""
    
    def evolve_from_cold_weaver(self, persona: dict, collision: dict) -> dict:
        """
        Quand le Cold Weaver trouve quelque chose qui "intéresse" Delirium,
        ça peut modifier un goût existant.
        
        Conditions :
        1. La collision doit être pertinente pour un goût DELIRIUM (pas user)
        2. Le score de collision doit être élevé (> 0.7)
        3. Max 1 changement de goût par mois
        """
        if collision["score"] < 0.7:
            return persona  # pas assez fort
        
        # Vérifier que ça touche un goût de Delirium
        for interest in persona["interests"]:
            sim = cosine_similarity(
                embed(collision["external_content"]),
                embed(interest["delirium_interest"])
            )
            if sim > 0.6:
                # Le Cold Weaver a trouvé quelque chose qui modifie le goût
                # Générer l'évolution via LLM
                evolution = llm_call(f"""
                    Delirium aimait : {interest["delirium_interest"]}
                    Il a découvert : {collision["external_title"]}
                    
                    Comment son goût évolue-t-il NATURELLEMENT ?
                    (Pas un revirement total — une nuance, un enrichissement)
                    Répondre en 1 phrase.
                """)
                interest["delirium_interest_evolved"] = evolution
                interest["evolution_date"] = datetime.now()
                interest["evolution_trigger"] = collision["external_title"]
                break
        
        return persona
    
    # RÈGLE ABSOLUE : les goûts ne changent JAMAIS par influence utilisateur.
    # Si l'utilisateur dit "le rugby c'est nul", Delirium ne switch PAS au foot.
```

---

## 3. MÉMOIRE — L'ARCHITECTURE COMPLÈTE

### 3.1 Le Problème Fondamental

Les LLM n'ont pas de mémoire persistante. Chaque appel API commence avec un contexte vide. La "mémoire" de Delirium est une **illusion architecturale** construite en 4 couches :

```
┌──────────────────────────────────────────────────────┐
│  COUCHE 4 — VISION DU MONDE                          │
│  Synthèse de qui est cet humain. Mise à jour rare.   │
│  NON CONSULTABLE par l'utilisateur.                   │
│  Alimente le S1 et le S2 comme contexte.              │
├──────────────────────────────────────────────────────┤
│  COUCHE 3 — MÉMOIRE SÉMANTIQUE (Graphe)              │
│  Thèmes, corrélations, patterns, hypothèses.          │
│  Construite incrémentalement par le S2.                │
│  Nœuds avec poids décroissants (Ebbinghaus).           │
├──────────────────────────────────────────────────────┤
│  COUCHE 2 — MÉMOIRE ÉPISODIQUE (Vector DB)            │
│  Chaque fragment de conversation embedé.               │
│  Searchable par similarité sémantique.                 │
│  Métadonnées : date, état H, intensité, source.        │
├──────────────────────────────────────────────────────┤
│  COUCHE 1 — MÉMOIRE DE TRAVAIL (Context Window)       │
│  System prompt + persona + memories retrieved + recent │
│  Limité par la fenêtre LLM (~128K tokens).             │
│  Reconstruit à chaque appel.                           │
└──────────────────────────────────────────────────────┘
```

### 3.2 Le Cycle de Mémoire — Chaque Message

```python
class MemoryOrchestrator:
    """Orchestre le cycle de mémoire à chaque message."""
    
    def __init__(self, sqlite_db, vector_db, graph_db, llm_client):
        self.episodic = EpisodicMemory(sqlite_db, vector_db)
        self.semantic = SemanticMemory(graph_db)
        self.vision = WorldVision(sqlite_db)
        self.persona_engine = PersonaEngine()
        self.llm = llm_client
    
    async def process_message(self, user_message: str, session_id: str) -> str:
        """Pipeline complet pour un message utilisateur."""
        
        # ═══ ÉTAPE 1 : RETRIEVAL (construire la mémoire de travail) ═══
        
        # 1a. Chercher les souvenirs pertinents (vector search)
        relevant_memories = self.episodic.search(
            query=user_message,
            n_results=5,
            recency_boost=True     # les souvenirs récents sont prioritaires
        )
        
        # 1b. Chercher les thèmes et corrélations actifs (graph traversal)
        active_themes = self.semantic.get_active_themes(threshold=0.3)
        active_correlations = self.semantic.get_correlations(min_confidence=0.3)
        
        # 1c. Charger la vision du monde (synthèse)
        world_vision = self.vision.get_current()
        
        # 1d. Charger l'état persona actuel
        persona_state = self.persona_engine.get_current_state()
        persona_preferences = self.persona_engine.get_preferences()
        
        # 1e. Charger les messages récents de cette session
        recent_messages = self.episodic.get_recent(session_id, limit=20)
        
        # ═══ ÉTAPE 2 : COMPOSE le prompt S1 ═══
        
        s1_prompt = self._compose_s1_prompt(
            persona_state=persona_state,
            persona_preferences=persona_preferences,
            relevant_memories=relevant_memories,
            active_themes=active_themes,
            world_vision_summary=world_vision.summary if world_vision else None,
            recent_messages=recent_messages
        )
        
        # ═══ ÉTAPE 3 : APPEL LLM S1 (réponse à l'utilisateur) ═══
        
        response = await self.llm.chat(
            system=s1_prompt,
            messages=recent_messages + [{"role": "user", "content": user_message}],
            model="MiniMax-M2.7",  # via OpenAI SDK + base_url MiniMax
            stream=True
        )
        
        # ═══ ÉTAPE 4 : STORE (persister le nouveau fragment) ═══
        
        fragment_id = self.episodic.store(
            user_message=user_message,
            response=response,
            session_id=session_id,
            persona_state=persona_state,
            timestamp=datetime.now()
        )
        
        # ═══ ÉTAPE 5 : ANALYSE S2 (asynchrone — ne bloque pas la réponse) ═══
        
        asyncio.create_task(self._run_s2_analysis(
            fragment_id=fragment_id,
            user_message=user_message,
            full_session=recent_messages + [user_message],
            current_persona=persona_state
        ))
        
        return response
    
    async def _run_s2_analysis(self, fragment_id, user_message, full_session, current_persona):
        """Analyse S2 asynchrone — tourne après la réponse S1."""
        
        s2_prompt = self._compose_s2_prompt(full_session, current_persona)
        
        analysis = await self.llm.chat(
            system=s2_prompt,
            messages=[{"role": "user", "content": json.dumps(full_session)}],
            model="MiniMax-M2.7-highspeed",  # rapide + pas cher pour le S2
            response_format="json"
        )
        
        s2_result = json.loads(analysis)
        
        # Mettre à jour la mémoire sémantique (graphe)
        self.semantic.update_from_s2(fragment_id, s2_result)
        
        # Mettre à jour l'état persona
        new_persona = self.persona_engine.transition(
            current=current_persona,
            s2_analysis=s2_result,
            time_context=self._get_time_context()
        )
        self.persona_engine.save_state(new_persona)
        
        # Logger (obligatoire)
        self.episodic.log_execution(
            fragment_id=fragment_id,
            log_type="s2_analysis",
            content=s2_result
        )
        
        # Vérifier si la vision du monde doit être re-synthétisée
        if self._should_resynthesize_vision(s2_result):
            asyncio.create_task(self._resynthesize_world_vision())
```

### 3.3 La Mémoire Épisodique — Stockage + Retrieval

```python
class EpisodicMemory:
    """Couche 2 — chaque fragment de conversation stocké et searchable."""
    
    def __init__(self, sqlite_db, vector_db):
        self.sql = sqlite_db
        self.vec = vector_db
    
    def store(self, user_message, response, session_id, persona_state, timestamp):
        """Stocke un fragment de conversation."""
        
        fragment_id = str(uuid4())
        
        # SQLite : métadonnées
        self.sql.execute("""
            INSERT INTO conversations 
            (id, timestamp, user_input, s1_response, source, embedding_id)
            VALUES (?, ?, ?, ?, 'delirium', ?)
        """, (fragment_id, timestamp, user_message, response, fragment_id))
        
        # Vector DB : embedding sémantique
        embedding = embed(user_message)  # on embed le message USER, pas la réponse
        self.vec.add(
            id=fragment_id,
            embedding=embedding,
            metadata={
                "timestamp": timestamp.isoformat(),
                "h_value": persona_state.H,
                "phase": persona_state.phase,
                "session_id": session_id
            }
        )
        
        # État épistémique initial : H (hypothèse)
        self.sql.execute("""
            INSERT INTO epistemic_state 
            (fragment_id, state, value, created_at)
            VALUES (?, 'H', 1.0, ?)
        """, (fragment_id, timestamp))
        
        return fragment_id
    
    def search(self, query: str, n_results: int = 5, recency_boost: bool = True) -> list:
        """Recherche les souvenirs les plus pertinents."""
        
        query_emb = embed(query)
        results = self.vec.query(embedding=query_emb, n_results=n_results * 3)
        
        if recency_boost:
            now = datetime.now()
            for r in results:
                age_days = (now - datetime.fromisoformat(r.metadata["timestamp"])).days
                # Bonus de récence : les souvenirs récents comptent plus
                recency_score = 1.0 / (1.0 + age_days / 30.0)
                r.combined_score = r.similarity * 0.6 + recency_score * 0.4
            results.sort(key=lambda r: r.combined_score, reverse=True)
        
        return results[:n_results]
```

### 3.4 La Mémoire Sémantique — Graphe de Connaissances

```python
class SemanticMemory:
    """Couche 3 — thèmes, corrélations, patterns. Construite par le S2."""
    
    def update_from_s2(self, fragment_id: str, s2_analysis: dict):
        """Met à jour le graphe après chaque analyse S2."""
        
        # 1. Créer/renforcer les nœuds thématiques
        for theme in s2_analysis.get("themes_latents", []):
            node = self.graph.get_or_create_node(
                label=theme, 
                type="theme"
            )
            node.weight = min(node.weight + 0.1, 1.0)  # renforcement
            node.last_activated = datetime.now()
            node.activation_count += 1
            
            # Lier au fragment
            self.graph.add_edge(node.id, fragment_id, type="mentioned_in")
        
        # 2. Créer/mettre à jour les corrélations
        correlation = s2_analysis.get("correlation")
        if correlation and correlation["confidence"] > 0.3:
            self.sql.execute("""
                INSERT OR REPLACE INTO correlations 
                (id, event_a_ids, event_b_ids, hypothesis, 
                 cause_racine_hypothesis, confidence, state)
                VALUES (?, ?, ?, ?, ?, ?, 'H')
            """, (
                correlation["id"],
                json.dumps(correlation["event_a"]),
                json.dumps(correlation["event_b"]),
                correlation["hypothesis"],
                correlation.get("root_cause"),
                correlation["confidence"]
            ))
        
        # 3. Détecter les boucles
        if s2_analysis.get("loop_detected"):
            self.graph.tag_loop(
                theme=s2_analysis["loop_theme"],
                occurrences=s2_analysis["loop_count"],
                first_seen=s2_analysis["loop_first_date"]
            )
        
        # 4. Mettre à jour la position IPC
        if "ipc_position" in s2_analysis:
            self.ipc_tracker.update(
                timestamp=datetime.now(),
                agency=s2_analysis["ipc_position"]["agency"],
                communion=s2_analysis["ipc_position"]["communion"]
            )
    
    def apply_decay(self):
        """Oubli sélectif — Ebbinghaus. Exécuté quotidiennement."""
        
        half_life_days = 90  # configurable
        threshold = 0.01
        now = datetime.now()
        
        for node in self.graph.all_nodes():
            days = (now - node.last_activated).days
            node.weight *= 0.5 ** (days / half_life_days)
            
            if node.weight < threshold:
                self.graph.delete_node(node.id)  # oublié
```

### 3.5 La Vision du Monde — Synthèse Périodique

```python
class WorldVision:
    """Couche 4 — synthèse de qui est cet humain. NON CONSULTABLE."""
    
    def should_resynthesize(self, s2_result: dict) -> bool:
        """Décide si la vision du monde doit être mise à jour."""
        
        triggers = [
            s2_result.get("danger_level", 0) >= 2,              # crise
            s2_result.get("loop_detected", False),               # boucle
            s2_result.get("axis_crossing", False),               # changement IPC
            s2_result.get("correlation_confirmed", False),       # corrélation confirmée
            self._sessions_since_last_synthesis() >= 10,         # routine (toutes les 10 sessions)
        ]
        return any(triggers)
    
    async def resynthesize(self, semantic_memory, episodic_memory, archetype):
        """Re-synthétise la vision du monde. Appel LLM lourd."""
        
        # Rassembler tout le matériel
        all_themes = semantic_memory.get_all_themes()
        all_correlations = semantic_memory.get_all_correlations()
        all_loops = semantic_memory.get_all_loops()
        ipc_trajectory = semantic_memory.ipc_tracker.get_trajectory()
        high_value_fragments = episodic_memory.get_high_value_fragments(limit=20)
        
        prompt = f"""
        Tu es le module Vision du Monde de Delirium. Tu synthétises TOUT ce que 
        Delirium sait sur cet humain en un document structuré.
        
        ARCHÉTYPE ACTUEL : {json.dumps(archetype)}
        
        THÈMES ACTIFS (poids > 0.1) : {json.dumps(all_themes)}
        
        CORRÉLATIONS DÉTECTÉES : {json.dumps(all_correlations)}
        
        BOUCLES COGNITIVES : {json.dumps(all_loops)}
        
        TRAJECTOIRE IPC (agency/communion sur le temps) : {json.dumps(ipc_trajectory)}
        
        FRAGMENTS SIGNIFICATIFS : {json.dumps(high_value_fragments)}
        
        Produis un JSON structuré :
        {{
            "who_they_are": "...",           // en 3 phrases, qui est cette personne
            "what_they_dont_see": "...",      // ce que Delirium voit et que l'utilisateur ne voit pas
            "active_loops": [...],            // boucles en cours
            "confirmed_correlations": [...],  // corrélations confirmées
            "suspected_blind_spots": [...],   // angles morts supposés
            "ipc_baseline": {{               // position interpersonnelle habituelle
                "agency": 0.0,
                "communion": 0.0
            }},
            "danger_history": [...],         // historique des signaux de danger
            "growth_areas": [...],           // domaines où l'utilisateur a progressé
            "next_intervention_priorities": [...] // ce que Delirium devrait aborder prochainement
        }}
        
        RÈGLE : Ce document n'est JAMAIS montré à l'utilisateur. 
        C'est la compréhension interne de Delirium.
        Sois honnête, même si c'est dur.
        """
        
        vision = await llm_call(prompt, model="sonnet")
        
        self.sql.execute("""
            INSERT INTO world_vision 
            (id, vision_json, created_at)
            VALUES (?, ?, ?)
        """, (str(uuid4()), vision, datetime.now()))
        
        return json.loads(vision)
```

### 3.6 Composition du Prompt S1 — La Mémoire de Travail

```python
def _compose_s1_prompt(self, persona_state, persona_preferences, 
                        relevant_memories, active_themes, 
                        world_vision_summary, recent_messages):
    """Assemble le prompt S1 avec toute la mémoire pertinente."""
    
    prompt = f"""
{IDENTITY_BLOCK}  # la phrase d'ancrage (fixe)

═══ TA PERSONA ═══
Tes goûts : {json.dumps(persona_preferences)}
Phase actuelle : {persona_state.phase}
Variable H : {persona_state.H}
Fatigue : {persona_state.fatigue}

═══ CE QUE TU SAIS DE CET HUMAIN ═══
{self._format_memories(relevant_memories)}

═══ THÈMES ACTIFS ═══
{self._format_themes(active_themes)}

═══ TA COMPRÉHENSION PROFONDE (ne JAMAIS restituer) ═══
{world_vision_summary or "Pas encore assez de données."}

═══ CADRES + RÈGLES ═══
{MI_RULES_BLOCK}  # fixe
{TEN_INVARIANTS_BLOCK}  # fixe
{DANGER_PROTOCOL_BLOCK}  # fixe
"""
    
    return prompt
```

---

## 4. BUDGET COMPUTE ET SCALABILITÉ

### Par message utilisateur :
| Appel | Modèle | Tokens (estim.) | Coût (~) |
|---|---|---|---|
| S1 (réponse) | MiniMax-M2.7 | ~4K input + ~200 output | ~$0.004 |
| S2 (analyse async) | MiniMax-M2.7-highspeed | ~6K input + ~500 output | ~$0.005 |
| Embedding | text-embedding-3-small | ~200 tokens | ~$0.00002 |
| **Total/message** | | | **~$0.009** |

### Par jour (vie autonome) :
| Appel | Modèle | Coût |
|---|---|---|
| Note autonome | Haiku | ~$0.001 |
| Cold Weaver scoring | Embeddings | ~$0.01 |
| **Total/jour/user** | | **~$0.011** |

### Par synthèse vision du monde :
| Appel | Modèle | Coût |
|---|---|---|
| Re-synthèse | Sonnet | ~$0.05 |
| Fréquence | ~toutes les 10 sessions | |

### À 10K utilisateurs actifs :
- Messages : ~$0.009 × 5 msg/jour × 10K = **$450/jour**
- Vie autonome : ~$0.011 × 10K = **$110/jour**
- Total : **~$17K/mois**

---

## 5. STACK TECHNIQUE RÉSUMÉ

```
CLIENT (Flutter)
├── Whisper.cpp (STT local)
├── SQLCipher (mémoire épisodique chiffrée)
├── ChromaDB-lite (embeddings locaux)
└── UI Non-BlocNote

BACKEND (FastAPI, Cloud FR)
├── LLM Router (MiniMax API, OpenAI-compatible)
│   ├── S1 : MiniMax-M2.7 (réponse)
│   ├── S2 : MiniMax-M2.7-highspeed (analyse async)
│   └── Vision : MiniMax-M2.7 (synthèse périodique)
├── PersonaEngine (transitions d'état)
├── MemoryOrchestrator (4 couches)
├── Cold Weaver (CRON worker)
│   ├── ArXiv/GitHub/RSS
│   ├── Collision scoring (SerenQA)
│   └── Sycophancy scoring (NLI)
├── OSINT Module (onboarding)
└── Sync Cloud (optionnel, E2E)
```
