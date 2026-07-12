from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

try:
    from context_engine import ContextEngine
except Exception:  # pragma: no cover - optional at import time
    ContextEngine = None  # type: ignore[assignment]


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


@dataclass
class AdaptiveProfile:
    profile_name: str
    response_style: str
    explanation_depth: str
    pacing: str
    interruption_policy: str
    proactive_support: str
    cad_assist_mode: str
    ui_density: str
    planning_weights: Dict[str, float]
    guidance: List[str] = field(default_factory=list)
    reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile_name": self.profile_name,
            "response_style": self.response_style,
            "explanation_depth": self.explanation_depth,
            "pacing": self.pacing,
            "interruption_policy": self.interruption_policy,
            "proactive_support": self.proactive_support,
            "cad_assist_mode": self.cad_assist_mode,
            "ui_density": self.ui_density,
            "planning_weights": dict(self.planning_weights),
            "guidance": list(self.guidance),
            "reasons": list(self.reasons),
        }


class HumanStateAdaptor:
    """Translate cognitive and emotional signals into concrete ADA behavior policy."""

    def __init__(self, context_engine: Optional[Any] = None) -> None:
        self._context_engine = context_engine

    def current_profile(self, snapshot: Optional[Any] = None, cognitive_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        snap = snapshot or self._get_snapshot()
        state = cognitive_state if isinstance(cognitive_state, dict) else {}

        focus = _safe_float(state.get("focus_index", getattr(snap, "focus_index", 0.0)), 0.0)
        stress = _safe_float(state.get("stress_index", getattr(snap, "stress_index", 0.0)), 0.0)
        fatigue = _safe_float(state.get("fatigue_index", getattr(snap, "fatigue_index", 0.0)), 0.0)
        emotion = str(state.get("emotional_state", getattr(snap, "emotional_state", "neutral")) or "neutral").lower()
        load = str(state.get("cognitive_load", getattr(snap, "cognitive_load", "medium")) or "medium").lower()
        flow_state = bool(state.get("flow_state", getattr(snap, "flow_state", False)))
        error_on_screen = bool(getattr(snap, "error_detected_on_screen", False))
        idle_duration = _safe_float(getattr(snap, "idle_duration", 0.0), 0.0)

        profile = AdaptiveProfile(
            profile_name="balanced_operator",
            response_style="balanced",
            explanation_depth="moderate",
            pacing="steady",
            interruption_policy="normal",
            proactive_support="medium",
            cad_assist_mode="precision",
            ui_density="normal",
            planning_weights={
                "cost": 0.18,
                "risk": 0.24,
                "speed": 0.18,
                "aesthetics": 0.18,
                "manufacturability": 0.22,
            },
        )

        if flow_state and focus >= 78.0 and stress <= 40.0:
            profile.profile_name = "flow_guard"
            profile.response_style = "terse"
            profile.explanation_depth = "minimal"
            profile.pacing = "fast"
            profile.interruption_policy = "defer_noncritical"
            profile.proactive_support = "low"
            profile.cad_assist_mode = "precision"
            profile.ui_density = "minimal"
            profile.planning_weights.update({"speed": 0.26, "risk": 0.22, "manufacturability": 0.22, "aesthetics": 0.16, "cost": 0.14})
            profile.guidance.extend(
                [
                    "Keep replies short and immediately actionable.",
                    "Avoid non-critical interruptions while the user is in flow.",
                    "Default to preserving local edits and minimizing UI noise.",
                ]
            )
            profile.reasons.append("high_focus_low_stress_flow")

        if stress >= 70.0 or emotion in {"stressed", "angry", "overwhelmed"}:
            profile.profile_name = "stress_relief"
            profile.response_style = "calm_direct"
            profile.explanation_depth = "stepwise"
            profile.pacing = "slowed"
            profile.interruption_policy = "only_critical"
            profile.proactive_support = "high"
            profile.cad_assist_mode = "cautious"
            profile.ui_density = "reduced"
            profile.planning_weights.update({"risk": 0.36, "manufacturability": 0.24, "speed": 0.14, "aesthetics": 0.1, "cost": 0.16})
            profile.guidance.extend(
                [
                    "Break tasks into short validated steps.",
                    "Prefer reversible actions and explicit confirmation of risky changes.",
                    "Reduce UI density and surface only the next best action.",
                ]
            )
            profile.reasons.append("high_stress_detected")

        if fatigue >= 68.0 or emotion in {"tired", "sad"}:
            profile.profile_name = "fatigue_support"
            profile.response_style = "supportive_direct"
            profile.explanation_depth = "moderate"
            profile.pacing = "steady"
            profile.interruption_policy = "normal"
            profile.proactive_support = "high"
            profile.cad_assist_mode = "simplify"
            profile.ui_density = "reduced"
            profile.planning_weights.update({"risk": 0.3, "speed": 0.2, "manufacturability": 0.24, "cost": 0.16, "aesthetics": 0.1})
            profile.guidance.extend(
                [
                    "Prefer simpler plans with fewer branches and fewer simultaneous decisions.",
                    "Offer to continue work in the background when possible.",
                ]
            )
            profile.reasons.append("fatigue_detected")

        if focus <= 35.0 or load == "high":
            profile.profile_name = "guided_focus_recovery"
            profile.response_style = "guided"
            profile.explanation_depth = "stepwise"
            profile.pacing = "steady"
            profile.interruption_policy = "normal"
            profile.proactive_support = "high"
            profile.cad_assist_mode = "scaffolded"
            profile.ui_density = "focused"
            profile.planning_weights.update({"risk": 0.28, "speed": 0.18, "manufacturability": 0.24, "aesthetics": 0.12, "cost": 0.18})
            profile.guidance.extend(
                [
                    "Explain the next step before the full plan.",
                    "Highlight the active part and suppress non-essential options.",
                    "Offer recovery actions when errors are visible on screen.",
                ]
            )
            profile.reasons.append("low_focus_or_high_load")

        if error_on_screen:
            profile.guidance.append("Prioritize error recovery and verification before exploration.")
            profile.reasons.append("screen_error_detected")

        if idle_duration >= 60.0:
            profile.guidance.append("Offer a concise resume summary with the last active CAD/browser/task context.")
            profile.reasons.append("resume_after_idle")

        summary = self._summary(profile, focus=focus, stress=stress, fatigue=fatigue, emotion=emotion, load=load)
        payload = profile.to_dict()
        payload.update(
            {
                "focus_index": round(focus, 2),
                "stress_index": round(stress, 2),
                "fatigue_index": round(fatigue, 2),
                "emotional_state": emotion,
                "cognitive_load": load,
                "flow_state": flow_state,
                "summary": summary,
            }
        )
        return payload

    def prompt_guidance(self, profile: Optional[Dict[str, Any]] = None) -> str:
        state = profile if isinstance(profile, dict) else self.current_profile()
        guidance = state.get("guidance", []) if isinstance(state.get("guidance"), list) else []
        summary = str(state.get("summary", "")).strip()
        if not guidance:
            return summary
        return f"{summary} {' '.join(str(item).strip() for item in guidance if str(item).strip())}".strip()

    def _get_snapshot(self) -> Any:
        engine = self._context_engine or (ContextEngine() if ContextEngine is not None else None)
        if engine is None:
            return None
        try:
            return engine.get_snapshot()
        except Exception:
            return None

    @staticmethod
    def _summary(profile: AdaptiveProfile, focus: float, stress: float, fatigue: float, emotion: str, load: str) -> str:
        return (
            f"Adaptive mode={profile.profile_name}; style={profile.response_style}; depth={profile.explanation_depth}; "
            f"pace={profile.pacing}; CAD={profile.cad_assist_mode}; focus={focus:.1f}; stress={stress:.1f}; "
            f"fatigue={fatigue:.1f}; emotion={emotion}; load={load}."
        )
