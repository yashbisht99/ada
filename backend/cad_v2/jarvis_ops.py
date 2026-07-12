from __future__ import annotations

from typing import Any, Dict, Optional


def point_pick_to_hole_fragment(
    part_id: str,
    diameter_mm: float = 3.0,
    depth_mm: Optional[float] = None,
    face_hint: str = "picked",
) -> Dict[str, Any]:
    """Build cad_edit_fragment for a hole at pointed part (face-level when mesh pick unavailable)."""
    return {
        "part_id": part_id,
        "intent": {
            "op": "hole",
            "diameter_mm": float(diameter_mm),
            "depth_mm": depth_mm,
            "face": face_hint,
            "source": "point_pick",
        },
        "updates": {
            "params": {
                "hole_diameter_mm": float(diameter_mm),
            },
            "feature_ops": [
                {
                    "op": "hole",
                    "diameter_mm": float(diameter_mm),
                    "depth_mm": depth_mm,
                    "face": face_hint,
                }
            ],
        },
    }


def apply_hole_to_part(part: Dict[str, Any], diameter_mm: float, depth_mm: Optional[float] = None) -> Dict[str, Any]:
    """Increase hole count / diameter on part params for rebuild."""
    params = dict(part.get("params", {}) or {})
    params["hole_diameter_mm"] = max(float(params.get("hole_diameter_mm", 3.2)), diameter_mm)
    params["hole_count"] = max(int(params.get("hole_count", 4) or 4), 4)
    if depth_mm:
        params["hole_depth_mm"] = depth_mm
    part = dict(part)
    part["params"] = params
    return part
