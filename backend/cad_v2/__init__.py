"""CAD v2 package exports.

Keep this module light. Many CAD submodules are useful offline for tests and
local geometry work, while Jarvis orchestration and agentic research may import
optional AI SDKs. Heavy symbols are loaded lazily through ``__getattr__``.
"""

from __future__ import annotations

from typing import Any


__all__ = [
    "JarvisCadEngine",
    "generate_part_code",
    "generate_assembly_parts",
    "research_design_prompt",
    "research_to_build_context",
    "research_summary_markdown",
    "compute_von_mises_stress_approx",
    "run_assembly_fea",
]


def __getattr__(name: str) -> Any:
    if name == "JarvisCadEngine":
        from .jarvis_cad_engine import JarvisCadEngine

        return JarvisCadEngine
    if name in {"generate_part_code", "generate_assembly_parts"}:
        from .agentic_coder import generate_assembly_parts, generate_part_code

        return {"generate_part_code": generate_part_code, "generate_assembly_parts": generate_assembly_parts}[name]
    if name in {"research_design_prompt", "research_to_build_context", "research_summary_markdown"}:
        from .deep_research import research_design_prompt, research_summary_markdown, research_to_build_context

        return {
            "research_design_prompt": research_design_prompt,
            "research_to_build_context": research_to_build_context,
            "research_summary_markdown": research_summary_markdown,
        }[name]
    if name in {"compute_von_mises_stress_approx", "run_assembly_fea"}:
        from .fea_solver import compute_von_mises_stress_approx, run_assembly_fea

        return {
            "compute_von_mises_stress_approx": compute_von_mises_stress_approx,
            "run_assembly_fea": run_assembly_fea,
        }[name]
    raise AttributeError(name)
