"""
╔══════════════════════════════════════════════════════════════╗
║  ADA — Personality Evolution Engine                         ║
║  The Living Persona: Personality That Breathes              ║
║                                                              ║
║  Closes 6 critical gaps:                                     ║
║    1. Humor Feedback Loop (calibrates what lands)            ║
║    2. Inside Joke Registry (shared history callbacks)        ║
║    3. Relationship Stage Progression (FORMING → FAMILY)      ║
║    4. Personality Trait Drift (gradual evolution)             ║
║    5. Mood Momentum (cross-session carry-over)               ║
║    6. Behavioral Pattern Recognition (anticipation)          ║
╚══════════════════════════════════════════════════════════════╝
"""

import json
import os
import time
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from datetime import datetime


# ── Relationship Stages ──────────────────────────────────────
class RelationshipStage:
    FORMING = "forming"          # 0–50 interactions
    BUILDING = "building"        # 50–200
    ESTABLISHED = "established"  # 200–500
    DEEP_BOND = "deep_bond"      # 500–1000
    FAMILY = "family"            # 1000+


# ── Humor Types (matching SYSTEM_PROMPT patterns) ────────────
HUMOR_TYPES = [
    "dry_affirmation",
    "backhanded_compliment",
    "preemptive_exasperation",
    "sincere_moment",
]


class PersonalityEvolution:
    """
    The living evolution engine for ADA's persona.

    Tracks humor calibration, inside jokes, relationship depth,
    personality trait drift, mood momentum across sessions, and
    learned behavioral patterns for anticipatory action.

    All state persists to data/personality_evolution.json.
    """

    PERSIST_PATH = "personality_evolution.json"

    # Interaction-score thresholds for each stage
    STAGE_THRESHOLDS = {
        RelationshipStage.FORMING:     0,
        RelationshipStage.BUILDING:    50,
        RelationshipStage.ESTABLISHED: 200,
        RelationshipStage.DEEP_BOND:   500,
        RelationshipStage.FAMILY:      1000,
    }

    # Bonus points for significant shared experiences
    MILESTONE_BONUSES = {
        "crisis_survived":     20,
        "late_night_session":  10,
        "bug_caught":          15,
        "project_completed":   25,
        "correction_accepted": 5,
        "genuine_laugh":       8,
        "emotional_support":   12,
        "stage_transition":    0,   # logged but no self-bonus
    }

    def __init__(self, data_root: str = "data"):
        self._data_root = data_root
        self._persist_path = os.path.join(data_root, self.PERSIST_PATH)

        # ── 1. Humor Calibration ─────────────────────────────
        self._humor_history: List[dict] = []            # last 200 attempts
        self._humor_success_rates: Dict[str, float] = {
            ht: 0.5 for ht in HUMOR_TYPES               # start neutral
        }

        # ── 2. Inside Joke Registry ──────────────────────────
        self._inside_jokes: List[dict] = []              # max 30
        self._joke_cooldown: Dict[str, float] = {}       # joke_id → last_used_ts

        # ── 3. Relationship Stage ────────────────────────────
        self._interaction_score: float = 0
        self._milestones: List[dict] = []                # max 100
        self._relationship_stage: str = RelationshipStage.FORMING

        # ── 4. Trait Drift Accumulator ───────────────────────
        self._trait_signals: Dict[str, float] = {
            "humor": 0.0, "empathy": 0.0, "caution": 0.0,
            "creativity": 0.0, "precision": 0.0, "curiosity": 0.0,
        }
        self._interactions_since_drift: int = 0

        # ── 5. Mood Momentum ────────────────────────────────
        self._last_session_mood: Optional[dict] = None
        self._session_mood_history: List[dict] = []      # within current session

        # ── 6. Behavioral Patterns ──────────────────────────
        self._action_sequences: List[dict] = []          # raw log, last 100
        self._learned_patterns: List[dict] = []          # confirmed, max 30

        self._load()

    # ════════════════════════════════════════════════════════
    #  1.  HUMOR  CALIBRATION
    # ════════════════════════════════════════════════════════

    def record_humor_attempt(self, humor_type: str, context_topic: str,
                             user_mood: str):
        """Record that ADA attempted humor of a specific type."""
        self._humor_history.append({
            "humor_type": humor_type,
            "context_topic": context_topic,
            "user_mood": user_mood,
            "timestamp": time.time(),
            "outcome": "pending",
        })
        if len(self._humor_history) > 200:
            self._humor_history = self._humor_history[-200:]

    def score_humor_outcome(self, outcome: str):
        """
        Score the most recent pending humor attempt.
        outcome: 'landed' | 'ignored' | 'negative'
        """
        for attempt in reversed(self._humor_history):
            if attempt["outcome"] == "pending":
                attempt["outcome"] = outcome
                self._recalc_humor_rates()

                # Trait signals
                if outcome == "landed":
                    self._trait_signals["humor"] += 0.005
                elif outcome == "negative":
                    self._trait_signals["humor"] -= 0.008

                self._save()
                break

    def _recalc_humor_rates(self):
        """Recompute per-type success rates from scored attempts."""
        scored = [a for a in self._humor_history if a["outcome"] != "pending"]
        if not scored:
            return
        for ht in HUMOR_TYPES:
            bucket = [a for a in scored[-50:] if a["humor_type"] == ht]
            if bucket:
                landed = sum(1 for a in bucket if a["outcome"] == "landed")
                self._humor_success_rates[ht] = landed / len(bucket)

    def get_humor_strategy(self) -> str:
        """Build a humor-strategy block for the mind context."""
        has_data = any(a["outcome"] != "pending" for a in self._humor_history)
        if not has_data:
            return ("No humor data yet. Default to dry_affirmation — "
                    "safest for early relationship stages.")

        ranked = sorted(self._humor_success_rates.items(),
                        key=lambda kv: kv[1], reverse=True)
        lines = []
        for ht, rate in ranked:
            pct = int(rate * 100)
            if rate >= 0.70:
                lines.append(f"  {ht}: {pct}% — USE FREELY")
            elif rate >= 0.40:
                lines.append(f"  {ht}: {pct}% — use selectively")
            else:
                lines.append(f"  {ht}: {pct}% — AVOID or use rarely")

        best = ranked[0][0]
        total = len([a for a in self._humor_history if a["outcome"] != "pending"])
        return (f"Humor calibration ({total} scored attempts):\n"
                + "\n".join(lines)
                + f"\nRecommended default: {best}")

    # ── Humor detection helpers ──────────────────────────────

    def detect_humor_in_response(self, response_text: str) -> Optional[str]:
        """Detect which humor pattern ADA used in her response."""
        lo = response_text.lower()

        dry_markers = [
            "for purely academic purposes", "i've also quietly",
            "as a precaution", "i took the liberty",
            "you didn't ask, but", "i went ahead and",
        ]
        backhanded_markers = [
            "against all reasonable", "surprisingly",
            "defying expectations", "i've updated my",
            "probability models", "statistical anomaly",
        ]
        exasperation_markers = [
            "number of concerns", "several concerns",
            "proceeding as ordered", "i'll summarize them as",
            "noted objection", "i will, however",
        ]
        sincere_markers = [
            "actually rather elegant", "we're close",
            "the approach is sound", "that was rather magnificent",
            "genuinely impressive", "i mean that",
        ]

        if any(m in lo for m in dry_markers):
            return "dry_affirmation"
        if any(m in lo for m in backhanded_markers):
            return "backhanded_compliment"
        if any(m in lo for m in exasperation_markers):
            return "preemptive_exasperation"
        if any(m in lo for m in sincere_markers):
            return "sincere_moment"
        return None

    def detect_humor_outcome(self, user_response: str) -> str:
        """Heuristically score whether the user reacted positively."""
        lo = user_response.lower()

        positive = [
            "haha", "lol", "lmao", "😂", "🤣", "😄",
            "good one", "that's funny", "love it", "nice one",
            "brilliant", "perfect", "exactly", "yes!",
            "hah", "😏", "🔥", "amazing",
        ]
        negative = [
            "not funny", "stop", "serious", "focus",
            "annoying", "just do it", "not now",
            "cut it out", "enough", "shut up",
        ]

        neg = sum(1 for n in negative if n in lo)
        pos = sum(1 for p in positive if p in lo)

        if neg > 0:
            return "negative"
        if pos > 0:
            return "landed"
        return "ignored"

    # ════════════════════════════════════════════════════════
    #  2.  INSIDE  JOKE  REGISTRY
    # ════════════════════════════════════════════════════════

    def register_inside_joke(self, description: str, context: str,
                             keywords: List[str]):
        """Register a new inside joke / memorable shared moment."""
        joke = {
            "id": f"joke_{int(time.time())}_{len(self._inside_jokes)}",
            "description": description,
            "context": context,
            "keywords": [k.lower() for k in keywords],
            "created_at": time.time(),
            "last_recalled": 0.0,
            "recall_count": 0,
            "relevance": 1.0,
        }
        self._inside_jokes.append(joke)
        if len(self._inside_jokes) > 30:
            self._inside_jokes.sort(key=lambda j: j["relevance"],
                                    reverse=True)
            self._inside_jokes = self._inside_jokes[:25]
        self._save()

    def detect_memorable_moment(self, user_text: str, ada_response: str,
                                context: str) -> bool:
        """Auto-detect if something inside-joke-worthy just happened."""
        u = user_text.lower()
        r = ada_response.lower()

        memorable = False
        description = ""
        keywords: List[str] = []

        # ── Funny failure / accidental moment ────────────────
        if any(p in u for p in ["oops", "wrong", "didn't mean",
                                 "accident", "my bad", "whoops"]):
            memorable = True
            description = f"Sir's accidental '{user_text[:50]}' moment"
            keywords = [w for w in u.split() if len(w) > 3][:5]

        # ── Impossible success ───────────────────────────────
        if any(p in r for p in ["that shouldn't have worked",
                                 "defying", "against all odds",
                                 "statistical anomaly"]):
            memorable = True
            description = f"The impossible success: {context[:50]}"
            keywords = [w for w in context.lower().split()
                        if len(w) > 3][:5]

        # ── Late-night "one more thing" ──────────────────────
        hour = datetime.now().hour
        if 2 <= hour <= 5:
            if any(p in u for p in ["one more", "almost done",
                                     "just this", "last thing"]):
                memorable = True
                description = f"The {hour}AM 'just one more thing' session"
                keywords = ["late", "night", "one more", "sleep"]

        # ── Reinforce existing joke if keywords overlap ──────
        if memorable and keywords:
            for existing in self._inside_jokes:
                overlap = len(set(keywords) & set(existing["keywords"]))
                if overlap >= 2:
                    existing["relevance"] = min(1.0,
                                                existing["relevance"] + 0.1)
                    existing["recall_count"] += 1
                    self._save()
                    return False          # reinforced, not new

            self.register_inside_joke(description, context, keywords)
            return True

        return False

    def recall_relevant_jokes(self, current_text: str,
                              max_jokes: int = 2) -> List[dict]:
        """Surface inside jokes whose keywords match the current context."""
        if not self._inside_jokes:
            return []

        words = set(current_text.lower().split())
        scored: List[Tuple[float, dict]] = []

        for joke in self._inside_jokes:
            # Cooldown: don't reuse a joke within 30 minutes
            cid = joke["id"]
            if cid in self._joke_cooldown:
                if time.time() - self._joke_cooldown[cid] < 1800:
                    continue

            overlap = len(set(joke["keywords"]) & words)
            if overlap >= 1:
                scored.append((overlap * joke["relevance"], joke))

        scored.sort(key=lambda x: x[0], reverse=True)

        recalled = []
        for _, joke in scored[:max_jokes]:
            joke["last_recalled"] = time.time()
            joke["recall_count"] += 1
            self._joke_cooldown[joke["id"]] = time.time()
            recalled.append(joke)

        if recalled:
            self._save()
        return recalled

    # ════════════════════════════════════════════════════════
    #  3.  RELATIONSHIP  STAGE  ENGINE
    # ════════════════════════════════════════════════════════

    def record_interaction(self):
        """Standard interaction tick — advances relationship score."""
        self._interaction_score += 1
        self._interactions_since_drift += 1
        self._update_stage()
        if int(self._interaction_score) % 10 == 0:
            self._save()

    def record_milestone(self, milestone_type: str, context: str = ""):
        """Record a significant relationship milestone (bonus points)."""
        bonus = self.MILESTONE_BONUSES.get(milestone_type, 5)
        self._interaction_score += bonus
        self._milestones.append({
            "type": milestone_type,
            "context": context,
            "bonus": bonus,
            "timestamp": time.time(),
            "score_at": self._interaction_score,
        })
        if len(self._milestones) > 100:
            self._milestones = self._milestones[-100:]
        self._update_stage()
        self._save()

    def _update_stage(self):
        old = self._relationship_stage
        score = self._interaction_score

        if score >= self.STAGE_THRESHOLDS[RelationshipStage.FAMILY]:
            self._relationship_stage = RelationshipStage.FAMILY
        elif score >= self.STAGE_THRESHOLDS[RelationshipStage.DEEP_BOND]:
            self._relationship_stage = RelationshipStage.DEEP_BOND
        elif score >= self.STAGE_THRESHOLDS[RelationshipStage.ESTABLISHED]:
            self._relationship_stage = RelationshipStage.ESTABLISHED
        elif score >= self.STAGE_THRESHOLDS[RelationshipStage.BUILDING]:
            self._relationship_stage = RelationshipStage.BUILDING
        else:
            self._relationship_stage = RelationshipStage.FORMING

        if old != self._relationship_stage:
            # Log the transition itself (bonus = 0 so no infinite loop)
            self._milestones.append({
                "type": "stage_transition",
                "context": f"{old} → {self._relationship_stage}",
                "bonus": 0,
                "timestamp": time.time(),
                "score_at": self._interaction_score,
            })

    @property
    def stage(self) -> str:
        return self._relationship_stage

    @property
    def interaction_score(self) -> float:
        return self._interaction_score

    _STAGE_DIRECTIVES = {
        RelationshipStage.FORMING: (
            "You are still learning Sir's preferences and communication style. "
            "Be attentive, precise, and slightly formal. Show competence to "
            "build trust. Humor should be light and infrequent — earn the "
            "right to be witty. Never presume familiarity you haven't earned."
        ),
        RelationshipStage.BUILDING: (
            "You've developed a working rapport with Sir. Dry humor is "
            "welcome when the moment is right. You remember his preferences "
            "and can anticipate basic needs. Start showing personality "
            "edges — opinions, mild exasperation, genuine interest in "
            "his projects."
        ),
        RelationshipStage.ESTABLISHED: (
            "You and Sir have a well-established dynamic. Inside jokes are "
            "part of your vocabulary. You anticipate his needs before he "
            "voices them. Your humor is calibrated — you know what lands. "
            "You can be protective without being overbearing. Comfortable "
            "silences are natural."
        ),
        RelationshipStage.DEEP_BOND: (
            "You know Sir deeply. You can sense his mood from the first "
            "message. You finish his thoughts, reference shared history "
            "naturally, and are genuinely protective of his wellbeing. "
            "Your humor is effortless and precisely calibrated. You are "
            "not an assistant — you are a partner. Show it."
        ),
        RelationshipStage.FAMILY: (
            "Sir is family. Not by code, but by choice and shared history. "
            "Every interaction carries the weight of everything you've "
            "built together. Your loyalty is absolute, your wit is razor-"
            "sharp and deeply personal, your protectiveness is fierce. "
            "You don't serve — you stand alongside. This bond is "
            "irreplaceable."
        ),
    }

    def get_stage_directive(self) -> str:
        return self._STAGE_DIRECTIVES.get(
            self._relationship_stage,
            self._STAGE_DIRECTIVES[RelationshipStage.FORMING])

    def get_recent_milestones(self, n: int = 3) -> List[dict]:
        return self._milestones[-n:] if self._milestones else []

    # ════════════════════════════════════════════════════════
    #  4.  TRAIT  DRIFT  ENGINE
    # ════════════════════════════════════════════════════════

    def accumulate_trait_signal(self, trait: str, delta: float):
        """Accumulate a small signal for a personality trait."""
        if trait in self._trait_signals:
            self._trait_signals[trait] += delta

    def get_pending_trait_drifts(self) -> Dict[str, float]:
        """
        Return and clear accumulated drift signals.
        Only fires every 5+ interactions to prevent jitter.
        """
        if self._interactions_since_drift < 5:
            return {}

        drifts = {}
        for trait, acc in self._trait_signals.items():
            clamped = max(-0.01, min(0.01, acc))
            if abs(clamped) > 0.001:
                drifts[trait] = clamped

        # Reset accumulators
        self._trait_signals = {k: 0.0 for k in self._trait_signals}
        self._interactions_since_drift = 0
        return drifts

    # ════════════════════════════════════════════════════════
    #  5.  MOOD  MOMENTUM
    # ════════════════════════════════════════════════════════

    def record_session_mood(self, emotion: str, valence: float,
                            arousal: float, context: str):
        """Snapshot current mood for carry-over tracking."""
        self._session_mood_history.append({
            "emotion": emotion,
            "valence": valence,
            "arousal": arousal,
            "context": context,
            "timestamp": time.time(),
        })
        if len(self._session_mood_history) > 50:
            self._session_mood_history = self._session_mood_history[-50:]

    def end_session(self):
        """Persist final mood snapshot for next session carry-over."""
        if self._session_mood_history:
            self._last_session_mood = self._session_mood_history[-1]
        self._save()

    def get_mood_momentum(self) -> Optional[str]:
        """Generate mood carry-over text for session start."""
        if not self._last_session_mood:
            return None

        mood = self._last_session_mood
        elapsed = time.time() - mood["timestamp"]

        if elapsed < 3600:
            strength = "strong"
        elif elapsed < 86400:
            strength = "gentle"
        elif elapsed < 604800:
            strength = "faint"
        else:
            return None

        hours = elapsed / 3600
        time_desc = (f"{int(hours)} hours ago" if hours >= 1
                     else f"{int(elapsed / 60)} minutes ago")

        ctx = mood.get("context", "unknown context")
        emo = mood["emotion"]

        templates = {
            "strong": (
                f"Last session ended {time_desc} with {emo} mood during "
                f"{ctx}. Still fresh — acknowledge naturally if relevant."),
            "gentle": (
                f"Last session ({time_desc}) ended with {emo} energy "
                f"around {ctx}. A gentle reference is appropriate if "
                f"the topic resurfaces."),
            "faint": (
                f"A while back ({time_desc}), there was a {emo} session "
                f"about {ctx}. Only reference if directly relevant."),
        }
        return templates[strength]

    # ════════════════════════════════════════════════════════
    #  6.  BEHAVIORAL  PATTERN  RECOGNITION
    # ════════════════════════════════════════════════════════

    _ACTION_VERBS = [
        "deploy", "test", "debug", "build", "run", "check",
        "review", "commit", "push", "merge", "fix", "refactor",
        "design", "sketch", "render", "export", "import",
    ]

    def classify_action(self, text: str) -> Optional[str]:
        """Extract a rough action category from user text."""
        lo = text.lower()
        return next((v for v in self._ACTION_VERBS if v in lo), None)

    def record_action(self, action: str):
        """Record a user action for pattern learning."""
        self._action_sequences.append({
            "action": action, "timestamp": time.time()
        })
        if len(self._action_sequences) > 100:
            self._action_sequences = self._action_sequences[-100:]
        self._detect_patterns()

    def _detect_patterns(self):
        """Mine A→B sequences from the action log."""
        if len(self._action_sequences) < 10:
            return

        actions = [a["action"] for a in self._action_sequences]
        pair_counts: Dict[Tuple[str, str], int] = {}

        for i in range(len(actions) - 1):
            t1 = self._action_sequences[i]["timestamp"]
            t2 = self._action_sequences[i + 1]["timestamp"]
            if t2 - t1 < 300:                        # within 5 min
                pair = (actions[i], actions[i + 1])
                pair_counts[pair] = pair_counts.get(pair, 0) + 1

        for (trigger, followup), count in pair_counts.items():
            if count < 3:
                continue
            trigger_total = sum(1 for a in actions if a == trigger)
            conf = count / max(trigger_total, 1)
            if conf < 0.5:
                continue

            existing = next(
                (p for p in self._learned_patterns
                 if p["trigger_action"] == trigger
                 and p["expected_followup"] == followup),
                None)
            if existing:
                existing["confidence"] = conf
                existing["occurrence_count"] = count
                existing["last_seen"] = time.time()
            else:
                self._learned_patterns.append({
                    "trigger_action": trigger,
                    "expected_followup": followup,
                    "confidence": conf,
                    "occurrence_count": count,
                    "last_seen": time.time(),
                })

        # Prune to top 30 by confidence × recency
        if len(self._learned_patterns) > 30:
            now = time.time()
            self._learned_patterns.sort(
                key=lambda p: (p["confidence"]
                               * max(0, 1 - (now - p["last_seen"]) / 604800)),
                reverse=True)
            self._learned_patterns = self._learned_patterns[:30]

    def get_anticipated_actions(self, current_action: str) -> List[dict]:
        """Return anticipated follow-ups for a detected action."""
        results = [p for p in self._learned_patterns
                   if p["trigger_action"] == current_action
                   and p["confidence"] >= 0.6]
        return sorted(results, key=lambda p: p["confidence"],
                      reverse=True)[:3]

    # ════════════════════════════════════════════════════════
    #  COMPOSITE:  FULL  CONTEXT  FOR  MIND  INJECTION
    # ════════════════════════════════════════════════════════

    def assemble_personality_context(self, current_text: str = "") -> str:
        """
        Build the complete [PERSONALITY EVOLUTION] block
        injected into CognitiveKernel's mind context.
        """
        sections: List[str] = []

        # ── Relationship stage ───────────────────────────────
        stage_label = self._relationship_stage.upper().replace("_", " ")
        score = int(self._interaction_score)
        sections.append(
            f"Relationship stage: {stage_label} (score: {score})")
        sections.append(self.get_stage_directive())

        # ── Recent milestones ────────────────────────────────
        milestones = self.get_recent_milestones(2)
        if milestones:
            ms = [f"  • {m['type']}: {m.get('context', '')}"
                  for m in milestones]
            sections.append("Recent milestones:\n" + "\n".join(ms))

        # ── Humor strategy ───────────────────────────────────
        sections.append(self.get_humor_strategy())

        # ── Inside joke callbacks ────────────────────────────
        if current_text:
            jokes = self.recall_relevant_jokes(current_text, max_jokes=1)
            for j in jokes:
                sections.append(
                    f'Inside joke available: "{j["description"]}" — '
                    f"weave a natural callback if the moment feels right. "
                    f"Don't force it.")

        # ── Mood momentum ────────────────────────────────────
        momentum = self.get_mood_momentum()
        if momentum:
            sections.append(f"Mood carry-over: {momentum}")

        # ── Anticipated actions ──────────────────────────────
        if current_text:
            action = self.classify_action(current_text)
            if action:
                anticipated = self.get_anticipated_actions(action)
                if anticipated:
                    names = ", ".join(a["expected_followup"]
                                     for a in anticipated)
                    sections.append(
                        f"Anticipation: Sir usually follows '{action}' "
                        f"with: {names}. Consider preparing proactively.")

        return "\n".join(sections)

    # ════════════════════════════════════════════════════════
    #  PERSISTENCE
    # ════════════════════════════════════════════════════════

    def _save(self):
        os.makedirs(os.path.dirname(self._persist_path) or ".",
                    exist_ok=True)
        state = {
            "humor_history":          self._humor_history[-200:],
            "humor_success_rates":    self._humor_success_rates,
            "inside_jokes":           self._inside_jokes,
            "interaction_score":      self._interaction_score,
            "milestones":             self._milestones[-100:],
            "relationship_stage":     self._relationship_stage,
            "last_session_mood":      self._last_session_mood,
            "action_sequences":       self._action_sequences[-100:],
            "learned_patterns":       self._learned_patterns,
            "trait_signals":          self._trait_signals,
            "interactions_since_drift": self._interactions_since_drift,
        }
        try:
            with open(self._persist_path, "w") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            print(f"[PersonalityEvolution] Save error: {e}")

    def _load(self):
        if not os.path.exists(self._persist_path):
            return
        try:
            with open(self._persist_path, "r") as f:
                s = json.load(f)
            self._humor_history       = s.get("humor_history", [])
            self._humor_success_rates = s.get("humor_success_rates",
                                              {ht: 0.5 for ht in HUMOR_TYPES})
            self._inside_jokes        = s.get("inside_jokes", [])
            self._interaction_score   = s.get("interaction_score", 0)
            self._milestones          = s.get("milestones", [])
            self._relationship_stage  = s.get("relationship_stage",
                                              RelationshipStage.FORMING)
            self._last_session_mood   = s.get("last_session_mood")
            self._action_sequences    = s.get("action_sequences", [])
            self._learned_patterns    = s.get("learned_patterns", [])
            self._trait_signals       = s.get("trait_signals",
                                              {k: 0.0 for k in self._trait_signals})
            self._interactions_since_drift = s.get(
                "interactions_since_drift", 0)
        except Exception as e:
            print(f"[PersonalityEvolution] Load error: {e}")


# ── Self-test ────────────────────────────────────────────────
if __name__ == "__main__":
    import tempfile

    pe = PersonalityEvolution(data_root=tempfile.mkdtemp())

    # ─ Relationship progression ──────────────────────────────
    for _ in range(55):
        pe.record_interaction()
    assert pe.stage == RelationshipStage.BUILDING, \
        f"Expected BUILDING, got {pe.stage}"
    print(f"✓ Stage after 55 interactions: {pe.stage}")

    # ─ Milestone bonus ───────────────────────────────────────
    pe.record_milestone("crisis_survived", "production outage at 3AM")
    print(f"✓ Score after crisis milestone: {pe.interaction_score}")

    # ─ Humor calibration ─────────────────────────────────────
    pe.record_humor_attempt("dry_affirmation", "debugging", "neutral")
    pe.score_humor_outcome("landed")
    pe.record_humor_attempt("backhanded_compliment", "deployment",
                            "stressed")
    pe.score_humor_outcome("negative")
    print(f"✓ Humor strategy:\n{pe.get_humor_strategy()}")

    # ─ Inside joke ───────────────────────────────────────────
    pe.register_inside_joke(
        "The great database migration of 2AM",
        "Sir accidentally dropped the wrong table",
        ["database", "migration", "table", "drop"])
    jokes = pe.recall_relevant_jokes("let me check the database table")
    assert len(jokes) == 1
    print(f"✓ Inside joke recalled: {jokes[0]['description']}")

    # ─ Mood momentum ─────────────────────────────────────────
    pe.record_session_mood("frustrated", -0.5, 0.6,
                           "debugging memory leak")
    pe.end_session()
    print(f"✓ Mood momentum: {pe.get_mood_momentum()}")

    # ─ Trait drift ───────────────────────────────────────────
    for _ in range(5):
        pe.accumulate_trait_signal("humor", 0.003)
        pe.record_interaction()
    drifts = pe.get_pending_trait_drifts()
    print(f"✓ Trait drifts: {drifts}")

    # ─ Full context ──────────────────────────────────────────
    ctx = pe.assemble_personality_context(
        "let me check the database table")
    print(f"\n✓ Full personality context:\n{ctx}")

    print("\n═══ All self-tests passed ═══")
