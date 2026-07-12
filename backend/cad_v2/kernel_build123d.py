from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Any, Dict, Optional

from .primitives.involute_gear import render_involute_gear_body
from .standard_parts import resolve_standard_part


def _float(value: Any, default: float) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _int(value: Any, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def _effective_role(part: Dict[str, Any]) -> str:
    role = str(part.get("role", "component")).lower()
    name = str(part.get("name", "")).lower()

    # Reactor-specific semantic geometry mapping (kept for arc reactor prompts).
    if name.startswith("arc_outer_ring") or name.startswith("arc_middle_ring") or name.startswith("arc_inner_flux_ring"):
        return "reactor_ring"
    if "arc_core" in name:
        return "reactor_core"
    if name.startswith("arc_coil_post"):
        return "reactor_coil"
    if name.startswith("arc_energy_channel"):
        return "reactor_channel"
    if name.startswith("arc_emitter_pin"):
        return "reactor_emitter"

    if role == "ring_gear":
        return "ring_gear"
    if role not in {"component", "assembly"}:
        return role
    if "ring" in name and "gear" in name:
        return "ring_gear"
    if "gear" in name:
        return "gear"
    if "shaft" in name or "axle" in name or "spindle" in name:
        return "shaft"
    if "lid" in name or "cover" in name:
        return "lid"
    if "mount" in name:
        return "mount_plate"
    if "bearing" in name:
        return "bearing_block"
    if "coupler" in name:
        return "coupler"
    if "standoff" in name or "spacer" in name:
        return "standoff"
    if "vent" in name or "panel" in name:
        return "vent_panel"
    if "housing" in name or "enclosure" in name or "case" in name:
        return "enclosure"
    return role


def _default_params(role: str, params: Dict[str, Any]) -> Dict[str, Any]:
    p = dict(params or {})
    width = _float(p.get("width_mm", 80), 80)
    depth = _float(p.get("depth_mm", 40), 40)
    height = _float(p.get("height_mm", 20), 20)
    thickness = _float(p.get("thickness_mm", max(3, height * 0.2)), max(3, height * 0.2))
    diameter = _float(p.get("diameter_mm", max(width, depth) * 0.5), max(width, depth) * 0.5)
    radius = _float(p.get("radius_mm", diameter * 0.5), diameter * 0.5)

    if role == "reinforcement":
        width = _float(p.get("width_mm", 40), 40)
        depth = _float(p.get("depth_mm", 6), 6)
        height = _float(p.get("height_mm", 20), 20)

    return {
        "width_mm": width,
        "depth_mm": depth,
        "height_mm": height,
        "thickness_mm": thickness,
        "diameter_mm": diameter,
        "radius_mm": radius,
        "hole_diameter_mm": _float(p.get("hole_diameter_mm", 3.2), 3.2),
        "hole_count": float(max(0, min(64, _int(p.get("hole_count", 4), 4)))),
        "vent_slots": float(max(0, min(80, _int(p.get("vent_slots", 0), 0)))),
        "lip_height_mm": _float(p.get("lip_height_mm", max(2.0, thickness)), max(2.0, thickness)),
        "shaft_diameter_mm": _float(p.get("shaft_diameter_mm", max(4.0, diameter * 0.3)), max(4.0, diameter * 0.3)),
        "bore_diameter_mm": _float(p.get("bore_diameter_mm", max(2.0, diameter * 0.25)), max(2.0, diameter * 0.25)),
        "gear_teeth": float(max(8, min(120, _int(p.get("gear_teeth", 24), 24)))),
        "gear_module": _float(p.get("gear_module", 2.0), 2.0),
        "flange_diameter_mm": _float(p.get("flange_diameter_mm", max(10.0, diameter * 1.7)), max(10.0, diameter * 1.7)),
        "cross_hole_diameter_mm": _float(p.get("cross_hole_diameter_mm", max(1.5, diameter * 0.15)), max(1.5, diameter * 0.15)),
        "rib_count": float(max(1, min(24, _int(p.get("rib_count", 2), 2)))),
        "fillet_radius_mm": _float(p.get("fillet_radius_mm", 0.0), 0.0),
        "chamfer_mm": _float(p.get("chamfer_mm", 0.0), 0.0),
        "lattice_density": _float(p.get("lattice_density", 0.0), 0.0),
        "lattice_type": str(p.get("lattice_type", "")),
        "hole_pattern": str(p.get("hole_pattern", "rectangular")),
        "bolt_circle_mm": _float(p.get("bolt_circle_mm", max(width, depth) * 0.68), max(width, depth) * 0.68),
        "thread_size": str(p.get("thread_size", "")),
        "thread_pitch_mm": _float(p.get("thread_pitch_mm", 0.0), 0.0),
        "threaded_hole_count": float(max(0, min(64, _int(p.get("threaded_hole_count", p.get("hole_count", 0)), 0)))),
        "pattern_type": str(p.get("pattern_type", "")),
        "manufacturing_process": str(p.get("manufacturing_process", "")),
        "heat_sink_fin_count": float(max(0, min(96, _int(p.get("heat_sink_fin_count", 0), 0)))),
        "heat_sink_fin_thickness_mm": _float(p.get("heat_sink_fin_thickness_mm", 1.2), 1.2),
        "heat_sink_fin_height_mm": _float(p.get("heat_sink_fin_height_mm", max(2.0, height * 0.18)), max(2.0, height * 0.18)),
        "duct_count": float(max(0, min(24, _int(p.get("duct_count", 0), 0)))),
        "duct_diameter_mm": _float(p.get("duct_diameter_mm", max(2.0, min(width, depth) * 0.08)), max(2.0, min(width, depth) * 0.08)),
        "fastener_count": float(max(0, min(32, _int(p.get("fastener_count", 0), 0)))),
        "fastener_size": str(p.get("fastener_size", "")),
        "fastener_preload_n": _float(p.get("fastener_preload_n", 0.0), 0.0),
        "fastener_edge_distance_diameters": _float(p.get("fastener_edge_distance_diameters", 2.0), 2.0),
        "composite_ply_count": float(max(0, min(256, _int(p.get("composite_ply_count", 0), 0)))),
        "composite_core_mm": _float(p.get("composite_core_mm", 0.0), 0.0),
    }


# ─── Minimal fallback templates (used ONLY when agentic coder is unavailable)

def _fallback_body_for_role(role: str, params: Dict[str, float]) -> str:
    """Return a minimal build123d body for a role when agentic coder fails.

    These are NOT the primary generation path — they are emergency fallbacks.
    """
    p = params

    if role == "ring_gear":
        return render_involute_gear_body(internal=True, hub=False)
    if role == "gear":
        return render_involute_gear_body(internal=False, hub=True)

    if role == "bracket":
        return f"""
with BuildPart() as p:
    with BuildSketch() as base:
        Rectangle({p['width_mm']}, {p['depth_mm']})
    extrude(amount={p['thickness_mm']})
    with BuildSketch(Plane.XZ) as wall:
        Rectangle({p['width_mm']}, {p['height_mm']})
    extrude(amount={p['thickness_mm']})
    rib_n = int({p['rib_count']})
    if rib_n >= 1:
        with Locations(({p['width_mm'] * 0.25 - p['width_mm'] * 0.5}, 0, {p['thickness_mm'] * 0.5})):
            with BuildSketch(Plane.YZ) as g1:
                Polygon((0, 0), ({p['height_mm'] * 0.6}, 0), (0, {p['height_mm'] * 0.6}))
            extrude(amount={p['thickness_mm']})
        with Locations(({p['width_mm'] * 0.75 - p['width_mm'] * 0.5}, 0, {p['thickness_mm'] * 0.5})):
            with BuildSketch(Plane.YZ) as g2:
                Polygon((0, 0), ({p['height_mm'] * 0.6}, 0), (0, {p['height_mm'] * 0.6}))
            extrude(amount={p['thickness_mm']})
    for x_pos in (-{p['width_mm'] * 0.28}, {p['width_mm'] * 0.28}):
        with Locations((x_pos, 0, 0)):
            Cylinder(radius=max({p['hole_diameter_mm']} * 0.5, 1.2), height=max({p['thickness_mm']} * 1.6, 2.0), mode=Mode.SUBTRACT)
result_part = p.part
"""
    if role == "enclosure":
        return f"""
with BuildPart() as p:
    t = {p['thickness_mm']}
    Box({p['width_mm']}, {p['depth_mm']}, {p['height_mm']})
    Box(max({p['width_mm']} - 2*t, 4), max({p['depth_mm']} - 2*t, 4), max({p['height_mm']} - t, 4), mode=Mode.SUBTRACT)
    for x_pos in (-{p['width_mm'] * 0.36}, {p['width_mm'] * 0.36}):
        for y_pos in (-{p['depth_mm'] * 0.3}, {p['depth_mm'] * 0.3}):
            with Locations((x_pos, y_pos, -{p['height_mm'] * 0.25})):
                Cylinder(radius=max({p['hole_diameter_mm']} * 0.75, 2.2), height=max({p['height_mm']} * 0.5, 6.0))
            with Locations((x_pos, y_pos, -{p['height_mm'] * 0.2})):
                Cylinder(radius=max({p['hole_diameter_mm']} * 0.5, 1.2), height=max({p['height_mm']} * 0.6, 6.0), mode=Mode.SUBTRACT)
result_part = p.part
"""
    if role == "shaft":
        return f"""
with BuildPart() as p:
    shaft_len = max({p['height_mm']}, max({p['width_mm']}, {p['depth_mm']}))
    shaft_r = max({p['shaft_diameter_mm']} * 0.5, 2.0)
    Cylinder(radius=shaft_r, height=shaft_len)
    with Locations((0, 0, shaft_len * 0.32)):
        Cylinder(radius=max({p['flange_diameter_mm']} * 0.5, shaft_r * 1.4), height=max({p['thickness_mm']}, 1.6))
    with Locations((0, 0, 0)):
        Cylinder(radius=max({p['bore_diameter_mm']} * 0.5, 0.8), height=shaft_len * 1.1, mode=Mode.SUBTRACT)
    with Locations((0, 0, 0)):
        Box(max(shaft_r * 2.2, 4.0), max({p['cross_hole_diameter_mm']}, 1.2), max({p['cross_hole_diameter_mm']}, 1.2), mode=Mode.SUBTRACT)
result_part = p.part
"""
    if role == "standoff":
        return f"""
with BuildPart() as p:
    hex_r = max(min({p['width_mm']}, {p['depth_mm']}) * 0.45, 2.4)
    with BuildSketch() as sketch:
        RegularPolygon(radius=hex_r, side_count=6)
    extrude(amount=max({p['height_mm']}, 4.0))
    with Locations((0, 0, 0)):
        Cylinder(radius=max({p['hole_diameter_mm']} * 0.5, 1.0), height=max({p['height_mm']} * 1.2, 5.0), mode=Mode.SUBTRACT)
result_part = p.part
"""
    # Generic fallback — simple box with optional features
    return f"""
with BuildPart() as p:
    Box({p['width_mm']}, {p['depth_mm']}, {p['height_mm']})
    with Locations((0, 0, {p['height_mm']} * 0.2)):
        Cylinder(radius=max(min({p['width_mm']}, {p['depth_mm']}) * 0.16, 2.0), height=max({p['thickness_mm']} * 0.9, 1.6))
    if {p['hole_count']} > 0:
        x_off = max({p['width_mm']} * 0.24, 3.0)
        y_off = max({p['depth_mm']} * 0.24, 3.0)
        for x_pos in (-x_off, x_off):
            for y_pos in (-y_off, y_off):
                with Locations((x_pos, y_pos, 0)):
                    Cylinder(radius=max({p['hole_diameter_mm']} * 0.45, 1.0), height=max({p['height_mm']} * 1.2, 4.0), mode=Mode.SUBTRACT)
result_part = p.part
"""


def _common_feature_body() -> str:
    """Shared operation-driven geometry applied inside the BuildPart context."""
    return """
    if hole_count > 0 and hole_pattern == "bolt_circle":
        pcd = max(bolt_circle_mm, hole_diameter * 3.2)
        for idx in range(max(1, min(48, hole_count))):
            theta = 2 * math.pi * idx / max(1, hole_count)
            with Locations((math.cos(theta) * pcd * 0.5, math.sin(theta) * pcd * 0.5, 0)):
                Cylinder(radius=max(hole_diameter * 0.5, 0.8), height=max(height * 1.45, thickness * 3, 5.0), mode=Mode.SUBTRACT)
    if lattice_density > 0.0 and min(width, depth) > 14 and height > 2:
        cell = max(5.0, min(width, depth) / max(3.0, 4.0 + lattice_density * 8.0))
        cut_radius = max(0.65, min(cell * lattice_density * 0.36, min(width, depth) * 0.055))
        x_count = max(1, min(7, int(width / cell)))
        y_count = max(1, min(7, int(depth / cell)))
        for ix in range(x_count):
            x_pos = -width * 0.36 + (width * 0.72) * (ix / max(1, x_count - 1))
            for iy in range(y_count):
                y_pos = -depth * 0.36 + (depth * 0.72) * (iy / max(1, y_count - 1))
                if abs(x_pos) < hole_diameter * 1.4 and abs(y_pos) < hole_diameter * 1.4:
                    continue
                with Locations((x_pos, y_pos, 0)):
                    Cylinder(radius=cut_radius, height=max(height * 1.35, thickness * 3, 5.0), mode=Mode.SUBTRACT)
    if pattern_type == "generative_ribs" and rib_count > 0 and width > 18 and depth > 12:
        rib_h = max(thickness * 0.7, 1.2)
        rib_w = max(min(width, depth) * 0.035, 1.2)
        for idx in range(max(1, min(12, rib_count))):
            frac = (idx + 1) / (max(1, rib_count) + 1)
            x_pos = -width * 0.36 + width * 0.72 * frac
            with Locations((x_pos, 0, height * 0.5 + rib_h * 0.25)):
                Box(rib_w, max(depth * 0.78, 4.0), rib_h)
    if thread_size:
        tap_radius = max(hole_diameter * 0.5, 0.8)
        with Locations((0, 0, 0)):
            Cylinder(radius=tap_radius, height=max(height * 1.35, thickness * 3, 5.0), mode=Mode.SUBTRACT)
        if width > tap_radius * 4 and depth > tap_radius * 4:
            with Locations((0, 0, height * 0.42)):
                Cylinder(radius=tap_radius * 1.7, height=max(thickness * 0.45, 1.0))
    if heat_sink_fin_count > 0 and width > 12 and depth > 12:
        # heat_sink fins
        fin_n = max(1, min(48, heat_sink_fin_count))
        fin_gap_span = max(width * 0.78, fin_thickness * fin_n)
        fin_h = max(heat_sink_fin_height, 1.0)
        for idx in range(fin_n):
            frac = 0.5 if fin_n == 1 else idx / max(1, fin_n - 1)
            x_pos = -fin_gap_span * 0.5 + fin_gap_span * frac
            with Locations((x_pos, 0, height * 0.5 + fin_h * 0.5)):
                Box(max(fin_thickness, 0.4), max(depth * 0.82, 4.0), fin_h)
    if duct_count > 0 and width > duct_diameter * 3 and depth > duct_diameter * 3:
        # cooling duct bores
        duct_n = max(1, min(12, duct_count))
        span = max(width * 0.58, duct_diameter * max(1, duct_n - 1) * 1.6)
        for idx in range(duct_n):
            frac = 0.5 if duct_n == 1 else idx / max(1, duct_n - 1)
            x_pos = -span * 0.5 + span * frac
            with Locations((x_pos, 0, 0)):
                Cylinder(radius=max(duct_diameter * 0.5, 0.8), height=max(height * 1.45, thickness * 3, 5.0), mode=Mode.SUBTRACT)
    if fastener_count > 0 and width > hole_diameter * 4 and depth > hole_diameter * 4:
        # fastener stack bosses
        fast_n = max(1, min(16, fastener_count))
        boss_radius = max(hole_diameter * 0.95, 1.8)
        boss_height = max(thickness * 0.75, 1.2)
        for idx in range(fast_n):
            theta = 2 * math.pi * idx / fast_n
            radius_xy = min(width, depth) * 0.32
            x_pos = math.cos(theta) * radius_xy
            y_pos = math.sin(theta) * radius_xy
            with Locations((x_pos, y_pos, height * 0.5 + boss_height * 0.5)):
                Cylinder(radius=boss_radius, height=boss_height)
            with Locations((x_pos, y_pos, 0)):
                Cylinder(radius=max(hole_diameter * 0.5, 0.8), height=max(height * 1.55, thickness * 3, 5.0), mode=Mode.SUBTRACT)
    if composite_ply_count > 0 and width > 12 and depth > 12:
        # composite ply witness ridges
        ply_marker_count = max(1, min(8, int(math.ceil(composite_ply_count / 4))))
        marker_w = max(min(width, depth) * 0.018, 0.45)
        for idx in range(ply_marker_count):
            y_pos = -depth * 0.42 + idx * max(marker_w * 2.2, depth * 0.08)
            with Locations((0, y_pos, height * 0.5 + marker_w * 0.5)):
                Box(max(width * 0.72, 4.0), marker_w, marker_w)
    if chamfer_mm > 0.0:
        try:
            chamfer(p.edges(), length=min(chamfer_mm, max(0.2, min(width, depth, height) * 0.08)))
        except Exception:
            pass
    if fillet_radius > 0.0:
        try:
            fillet(p.edges(), radius=min(fillet_radius, max(0.2, min(width, depth, height) * 0.12)))
        except Exception:
            pass
"""


def _inject_common_feature_body(body: str) -> str:
    return body.replace("result_part = p.part", _common_feature_body() + "result_part = p.part")


# ─── Script rendering (agentic-first, fallback to templates) ────────────────

def render_part_script(
    part: Dict[str, Any],
    stl_path: str,
    step_path: str,
    *,
    research_context: Optional[Dict[str, Any]] = None,
    use_agentic: bool = True,
) -> str:
    """Generate a build123d Python script for a part.

    Primary path: delegates to agentic_coder for fully custom geometry.
    Fallback path: uses hardcoded templates when agentic coder is unavailable.

    Args:
        part: Part specification dict (part_id, name, role, params, material, etc.).
        stl_path: Target STL file path.
        step_path: Target STEP file path.
        research_context: Optional engineering research context for agentic generation.
        use_agentic: Whether to try agentic generation first (default True).

    Returns:
        Python source code string for the build123d script.
    """
    role = _effective_role(part)
    raw_params = dict(part.get("params", {}) or {})
    sp_id = str(raw_params.get("standard_part_id", "")).strip()
    if sp_id:
        resolved = resolve_standard_part(sp_id)
        if resolved:
            role = str(resolved.get("role", role))
            raw_params.update(resolved.get("params", {}))
    params = _default_params(role, raw_params)
    metadata = part.get("metadata", {}) if isinstance(part.get("metadata"), dict) else {}
    feature_execution = metadata.get("feature_execution", {}) if isinstance(metadata.get("feature_execution"), dict) else {}
    feature_operations = feature_execution.get("applied_features", []) if isinstance(feature_execution.get("applied_features"), list) else []

    # ── Agentic path ──────────────────────────────────────────────────────
    if use_agentic:
        try:
            from .agentic_coder import _build_coder_prompt, _call_llm_for_code

            prompt = _build_coder_prompt(
                part_name=part.get("name", "component"),
                role=role,
                params=params,
                research_context=research_context,
            )
            source = _call_llm_for_code(prompt, timeout_s=60)

            # Ensure export calls
            if "export_stl" not in source:
                source += f"\nexport_stl(result_part, r'{stl_path}')\n"
            if "export_step" not in source:
                source += f"\nexport_step(result_part, r'{step_path}')\n"

            return source
        except Exception:
            pass  # Fall through to fallback

    # ── Fallback path — hardcoded templates ───────────────────────────────
    body = _inject_common_feature_body(_fallback_body_for_role(role, params))

    common_header = "\n".join(
        [
            "from build123d import *",
            "import math",
            f"PARAMS = {json.dumps(params)}",
            f"FEATURE_OPERATIONS = {json.dumps(feature_operations)}",
            "",
            "width = PARAMS['width_mm']",
            "depth = PARAMS['depth_mm']",
            "height = PARAMS['height_mm']",
            "thickness = PARAMS['thickness_mm']",
            "diameter = PARAMS['diameter_mm']",
            "radius = PARAMS['radius_mm']",
            "hole_diameter = PARAMS['hole_diameter_mm']",
            "hole_count = int(PARAMS['hole_count'])",
            "vent_slots = int(PARAMS['vent_slots'])",
            "lip_height = PARAMS['lip_height_mm']",
            "shaft_diameter = PARAMS['shaft_diameter_mm']",
            "bore_diameter = PARAMS['bore_diameter_mm']",
            "gear_teeth = int(PARAMS['gear_teeth'])",
            "gear_module = PARAMS['gear_module']",
            "flange_diameter = PARAMS['flange_diameter_mm']",
            "cross_hole_diameter = PARAMS['cross_hole_diameter_mm']",
            "rib_count = int(PARAMS['rib_count'])",
            "fillet_radius = PARAMS['fillet_radius_mm']",
            "chamfer_mm = PARAMS['chamfer_mm']",
            "lattice_density = PARAMS['lattice_density']",
            "lattice_type = PARAMS['lattice_type']",
            "hole_pattern = PARAMS['hole_pattern']",
            "bolt_circle_mm = PARAMS['bolt_circle_mm']",
            "thread_size = PARAMS['thread_size']",
            "thread_pitch_mm = PARAMS['thread_pitch_mm']",
            "threaded_hole_count = int(PARAMS['threaded_hole_count'])",
            "pattern_type = PARAMS['pattern_type']",
            "manufacturing_process = PARAMS['manufacturing_process']",
            "heat_sink_fin_count = int(PARAMS['heat_sink_fin_count'])",
            "heat_sink_fin_thickness_mm = PARAMS['heat_sink_fin_thickness_mm']",
            "heat_sink_fin_height = PARAMS['heat_sink_fin_height_mm']",
            "fin_thickness = heat_sink_fin_thickness_mm",
            "duct_count = int(PARAMS['duct_count'])",
            "duct_diameter = PARAMS['duct_diameter_mm']",
            "fastener_count = int(PARAMS['fastener_count'])",
            "fastener_size = PARAMS['fastener_size']",
            "fastener_preload_n = PARAMS['fastener_preload_n']",
            "fastener_edge_distance_diameters = PARAMS['fastener_edge_distance_diameters']",
            "composite_ply_count = int(PARAMS['composite_ply_count'])",
            "composite_core_mm = PARAMS['composite_core_mm']",
            "",
        ]
    )

    footer = "\n".join(
        [
            "assert result_part.volume > 0, 'Generated part has zero volume.'",
            "assert result_part.is_valid, 'Generated geometry is invalid.'",
            f"export_stl(result_part, r'{stl_path}')",
            f"export_step(result_part, r'{step_path}')",
            "",
        ]
    )

    return common_header + body + footer


def _resolve_python_exe() -> str:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(current_dir))
    venv_python = os.path.join(project_root, "venv_cad", "bin", "python")
    if os.path.exists(venv_python):
        return venv_python
    return sys.executable


def build_part(
    part: Dict[str, Any],
    part_dir: str,
    timeout_s: int = 40,
    *,
    research_context: Optional[Dict[str, Any]] = None,
    use_agentic: bool = True,
    max_attempts: int = 5,
) -> Dict[str, Any]:
    """Build a part from its spec, using agentic code generation with self-healing.

    Args:
        part: Part specification dict.
        part_dir: Directory for part outputs.
        timeout_s: Subprocess timeout per build attempt.
        research_context: Engineering research context for agentic generation.
        use_agentic: Whether to use agentic coder (default True).
        max_attempts: Maximum self-heal attempts.

    Returns:
        Build result dict with ok, paths, error info.
    """
    os.makedirs(part_dir, exist_ok=True)
    script_path = os.path.join(part_dir, "part.py")
    stl_path = os.path.join(part_dir, "part.stl")
    step_path = os.path.join(part_dir, "part.step")

    if use_agentic:
        try:
            from .agentic_coder import generate_part_code

            result = generate_part_code(
                part_id=part.get("part_id", "unknown"),
                part_name=part.get("name", "component"),
                role=_effective_role(part),
                params=part.get("params", {}),
                stl_path=stl_path,
                step_path=step_path,
                research_context=research_context,
                max_attempts=max_attempts,
                build_timeout_s=timeout_s,
            )

            # Save the generated source
            if result.source_code:
                with open(script_path, "w", encoding="utf-8") as handle:
                    handle.write(result.source_code)

            if result.build_ok:
                return {
                    "ok": True,
                    "script_path": script_path if result.source_code else "",
                    "stl_path": result.stl_path or stl_path,
                    "step_path": result.step_path or step_path,
                    "agentic": True,
                    "attempts": result.attempts,
                    "generation_time_s": result.generation_time_s,
                    "errors": result.errors[-1] if result.errors else "",
                }
        except Exception as exc:
            # Fall through to template-based build if agentic coder fails
            pass

    # ── Fallback: template-based build ────────────────────────────────────
    script = render_part_script(part, stl_path=stl_path, step_path=step_path, use_agentic=False)
    with open(script_path, "w", encoding="utf-8") as handle:
        handle.write(script)

    python_exe = _resolve_python_exe()

    try:
        proc = subprocess.run(
            [python_exe, script_path],
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "error": f"timeout after {timeout_s}s",
            "script_path": script_path,
            "stl_path": stl_path,
            "step_path": step_path,
            "agentic": False,
        }

    if proc.returncode != 0:
        return {
            "ok": False,
            "error": proc.stderr[-2000:] if proc.stderr else "build failed",
            "stdout": proc.stdout[-1000:] if proc.stdout else "",
            "script_path": script_path,
            "stl_path": stl_path,
            "step_path": step_path,
            "agentic": False,
        }

    return {
        "ok": os.path.exists(stl_path),
        "script_path": script_path,
        "stl_path": stl_path,
        "step_path": step_path if os.path.exists(step_path) else "",
        "stdout": proc.stdout[-1000:] if proc.stdout else "",
        "agentic": False,
    }
