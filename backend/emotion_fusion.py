"""
Emotion Fusion Engine — Multimodal emotion signal fusion.
Combines face, voice, text sentiment, behavioral, and contextual signals
into a unified emotional state with Bayesian confidence weighting.
Predicts emotional trajectory 5-10 minutes ahead.
Rate-limit safe: all local signal processing.
"""
import math
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple


@dataclass
class EmotionSignal:
    """A single emotion signal from one modality."""
    modality: str  # "face", "voice", "text", "behavioral", "contextual"
    emotion: str
    confidence: float
    valence: float  # -1 (negative) to +1 (positive)
    arousal: float  # 0 (calm) to 1 (excited)
    timestamp: float = field(default_factory=time.time)


@dataclass
class FusedEmotionalState:
    """The unified emotional state after fusion."""
    primary_emotion: str
    secondary_emotion: Optional[str]
    valence: float
    arousal: float
    confidence: float
    modality_agreement: float  # 0-1, how much modalities agree
    emotional_intensity: float  # 0-1
    signals_fused: int
    timestamp: float = field(default_factory=time.time)


@dataclass
class EmotionalTrajectory:
    """Predicted emotional trajectory."""
    current_emotion: str
    predicted_emotion: str
    predicted_valence: float
    predicted_arousal: float
    confidence: float
    minutes_ahead: float
    trend: str  # "improving", "declining", "stable", "volatile"


class EmotionFusionEngine:
    """
    Multimodal emotion fusion:
    - Weighted combination of face, voice, text, behavior, context signals
    - Bayesian prior updating from emotional history
    - Emotional trajectory prediction using momentum
    - Emotional stability/volatility tracking
    - Empathy state detection (stress, flow, confusion, engagement)

    Rate-limit safe — all local signal processing.
    """

    MODALITY_WEIGHTS = {
        "face": 0.30,
        "voice": 0.25,
        "text": 0.20,
        "behavioral": 0.15,
        "contextual": 0.10,
    }

    EMOTION_VALENCE = {
        "happy": 0.8, "excited": 0.7, "amused": 0.6, "content": 0.5,
        "neutral": 0.0, "surprised": 0.1, "confused": -0.2,
        "bored": -0.3, "anxious": -0.4, "frustrated": -0.5,
        "sad": -0.6, "angry": -0.7, "stressed": -0.6,
    }

    EMOTION_AROUSAL = {
        "excited": 0.9, "angry": 0.8, "surprised": 0.7, "anxious": 0.7,
        "frustrated": 0.6, "happy": 0.5, "stressed": 0.6,
        "amused": 0.5, "confused": 0.4, "neutral": 0.3,
        "content": 0.2, "bored": 0.2, "sad": 0.3,
    }

    def __init__(self, notify_fn: Optional[Callable] = None, history_size: int = 100):
        self._notify = notify_fn
        self._history: deque[FusedEmotionalState] = deque(maxlen=history_size)
        self._signal_buffer: Dict[str, EmotionSignal] = {}  # modality -> latest signal
        self._emotion_priors: Dict[str, float] = defaultdict(lambda: 0.1)
        self._fusion_count = 0
        self._last_fused: Optional[FusedEmotionalState] = None
        print("[EmotionFusion] Initialized multimodal emotion fusion engine.")

    # ---- signal input ----

    def push_signal(self, modality: str, emotion: str, confidence: float = 0.7,
                    valence: Optional[float] = None, arousal: Optional[float] = None) -> None:
        """Push a new emotion signal from a modality."""
        if valence is None:
            valence = self.EMOTION_VALENCE.get(emotion, 0.0)
        if arousal is None:
            arousal = self.EMOTION_AROUSAL.get(emotion, 0.3)

        signal = EmotionSignal(
            modality=modality, emotion=emotion, confidence=confidence,
            valence=valence, arousal=arousal,
        )
        self._signal_buffer[modality] = signal

    # ---- fusion ----

    def fuse(self) -> FusedEmotionalState:
        """Fuse all current signals into a unified emotional state."""
        self._fusion_count += 1
        signals = list(self._signal_buffer.values())

        if not signals:
            state = FusedEmotionalState(
                primary_emotion="neutral", secondary_emotion=None,
                valence=0.0, arousal=0.3, confidence=0.5,
                modality_agreement=1.0, emotional_intensity=0.0,
                signals_fused=0,
            )
            self._last_fused = state
            return state

        # Weighted emotion voting
        emotion_scores: Dict[str, float] = defaultdict(float)
        total_weight = 0.0
        weighted_valence = 0.0
        weighted_arousal = 0.0

        for signal in signals:
            weight = self.MODALITY_WEIGHTS.get(signal.modality, 0.1)
            adjusted_weight = weight * signal.confidence

            # Apply Bayesian prior
            prior = self._emotion_priors.get(signal.emotion, 0.1)
            bayesian_weight = adjusted_weight * (1 + prior)

            emotion_scores[signal.emotion] += bayesian_weight
            weighted_valence += signal.valence * adjusted_weight
            weighted_arousal += signal.arousal * adjusted_weight
            total_weight += adjusted_weight

        if total_weight > 0:
            weighted_valence /= total_weight
            weighted_arousal /= total_weight

        # Determine primary and secondary emotions
        sorted_emotions = sorted(emotion_scores.items(), key=lambda x: x[1], reverse=True)
        primary = sorted_emotions[0][0] if sorted_emotions else "neutral"
        secondary = sorted_emotions[1][0] if len(sorted_emotions) > 1 else None

        # Calculate modality agreement
        unique_emotions = set(s.emotion for s in signals)
        agreement = 1.0 / max(len(unique_emotions), 1)

        # Emotional intensity
        intensity = min(1.0, abs(weighted_valence) + weighted_arousal * 0.5)

        # Overall confidence
        confidence = min(1.0, agreement * 0.4 + (sum(s.confidence for s in signals) / len(signals)) * 0.6)

        state = FusedEmotionalState(
            primary_emotion=primary,
            secondary_emotion=secondary,
            valence=round(weighted_valence, 3),
            arousal=round(weighted_arousal, 3),
            confidence=round(confidence, 3),
            modality_agreement=round(agreement, 3),
            emotional_intensity=round(intensity, 3),
            signals_fused=len(signals),
        )

        # Update priors
        self._emotion_priors[primary] = min(1.0, self._emotion_priors[primary] + 0.02)
        # Decay other priors
        for emotion in self._emotion_priors:
            if emotion != primary:
                self._emotion_priors[emotion] *= 0.98

        self._history.append(state)
        self._last_fused = state
        return state

    # ---- trajectory prediction ----

    def predict_trajectory(self, minutes_ahead: float = 5.0) -> EmotionalTrajectory:
        """Predict emotional state minutes_ahead based on momentum."""
        if len(self._history) < 3:
            current = self._last_fused or FusedEmotionalState(
                "neutral", None, 0.0, 0.3, 0.5, 1.0, 0.0, 0
            )
            return EmotionalTrajectory(
                current_emotion=current.primary_emotion,
                predicted_emotion=current.primary_emotion,
                predicted_valence=current.valence,
                predicted_arousal=current.arousal,
                confidence=0.3,
                minutes_ahead=minutes_ahead,
                trend="stable",
            )

        recent = list(self._history)[-10:]

        # Calculate valence and arousal momentum
        valence_deltas = [recent[i].valence - recent[i - 1].valence for i in range(1, len(recent))]
        arousal_deltas = [recent[i].arousal - recent[i - 1].arousal for i in range(1, len(recent))]

        avg_v_delta = sum(valence_deltas) / len(valence_deltas)
        avg_a_delta = sum(arousal_deltas) / len(arousal_deltas)

        # Project with decay (momentum decreases over time)
        decay = math.exp(-0.1 * minutes_ahead)
        predicted_valence = max(-1.0, min(1.0, recent[-1].valence + avg_v_delta * minutes_ahead * decay))
        predicted_arousal = max(0.0, min(1.0, recent[-1].arousal + avg_a_delta * minutes_ahead * decay))

        # Determine predicted emotion
        predicted_emotion = self._valence_arousal_to_emotion(predicted_valence, predicted_arousal)

        # Determine trend
        if abs(avg_v_delta) < 0.01:
            trend = "stable"
        elif avg_v_delta > 0.03:
            trend = "improving"
        elif avg_v_delta < -0.03:
            trend = "declining"
        else:
            # Check volatility
            valence_variance = sum((d - avg_v_delta) ** 2 for d in valence_deltas) / len(valence_deltas)
            trend = "volatile" if valence_variance > 0.01 else "stable"

        # Confidence decreases with prediction horizon
        base_confidence = min(1.0, len(recent) / 10)
        confidence = base_confidence * math.exp(-0.15 * minutes_ahead)

        return EmotionalTrajectory(
            current_emotion=recent[-1].primary_emotion,
            predicted_emotion=predicted_emotion,
            predicted_valence=round(predicted_valence, 3),
            predicted_arousal=round(predicted_arousal, 3),
            confidence=round(confidence, 3),
            minutes_ahead=minutes_ahead,
            trend=trend,
        )

    # ---- meta-emotional analysis ----

    def get_emotional_stability(self, window: int = 20) -> float:
        """Calculate emotional stability (inverse of volatility)."""
        if len(self._history) < 3:
            return 0.5

        recent = list(self._history)[-window:]
        valences = [s.valence for s in recent]
        mean_v = sum(valences) / len(valences)
        variance = sum((v - mean_v) ** 2 for v in valences) / len(valences)
        stability = max(0.0, 1.0 - math.sqrt(variance) * 3)
        return round(stability, 3)

    def detect_emotional_state(self) -> Dict[str, float]:
        """Detect high-level emotional states (stress, flow, confusion, engagement)."""
        if not self._last_fused:
            return {"stress": 0.0, "flow": 0.0, "confusion": 0.0, "engagement": 0.5}

        state = self._last_fused
        stability = self.get_emotional_stability()

        stress = max(0.0, (-state.valence * 0.5 + state.arousal * 0.5) * (1 - stability))
        flow = max(0.0, (state.valence * 0.3 + state.arousal * 0.4 + stability * 0.3))
        confusion = max(0.0, state.arousal * 0.3 - state.valence * 0.2 - stability * 0.3 + 0.2)
        engagement = max(0.0, min(1.0, state.arousal * 0.5 + abs(state.valence) * 0.3 + state.confidence * 0.2))

        return {
            "stress": round(min(1.0, stress), 3),
            "flow": round(min(1.0, flow), 3),
            "confusion": round(min(1.0, confusion), 3),
            "engagement": round(min(1.0, engagement), 3),
        }

    def _valence_arousal_to_emotion(self, valence: float, arousal: float) -> str:
        """Map valence-arousal coordinates to an emotion label."""
        best_emotion = "neutral"
        best_dist = float("inf")
        for emotion in self.EMOTION_VALENCE:
            ev = self.EMOTION_VALENCE[emotion]
            ea = self.EMOTION_AROUSAL.get(emotion, 0.3)
            dist = math.sqrt((valence - ev) ** 2 + (arousal - ea) ** 2)
            if dist < best_dist:
                best_dist = dist
                best_emotion = emotion
        return best_emotion

    def get_current_state(self) -> Dict[str, Any]:
        """Get current fused emotional state as dict."""
        if not self._last_fused:
            return {"emotion": "neutral", "valence": 0.0, "arousal": 0.3, "confidence": 0.5}
        s = self._last_fused
        return {
            "emotion": s.primary_emotion,
            "secondary": s.secondary_emotion,
            "valence": s.valence,
            "arousal": s.arousal,
            "confidence": s.confidence,
            "intensity": s.emotional_intensity,
            "agreement": s.modality_agreement,
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            "fusions_performed": self._fusion_count,
            "history_length": len(self._history),
            "active_signals": len(self._signal_buffer),
            "emotional_stability": self.get_emotional_stability(),
            "current_state": self.get_current_state(),
            "meta_states": self.detect_emotional_state(),
        }
