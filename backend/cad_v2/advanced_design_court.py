from __future__ import annotations

from typing import Any, Dict, List, Set


def _timeline(scene: Dict[str, Any]) -> List[Dict[str, Any]]:
    direct = scene.get("feature_timeline") if isinstance(scene.get("feature_timeline"), list) else []
    if direct:
        return [op for op in direct if isinstance(op, dict)]
    source = scene.get("source_spec") if isinstance(scene.get("source_spec"), dict) else {}
    ops = source.get("operations") if isinstance(source.get("operations"), list) else []
    return [op for op in ops if isinstance(op, dict)]


def _op_types(scene: Dict[str, Any]) -> Set[str]:
    return {str(op.get("type", "")) for op in _timeline(scene)}


def _review(agent: str, score: float, findings: List[str], demands: List[str]) -> Dict[str, Any]:
    return {
        "agent": agent,
        "score": round(max(0.0, min(1.0, score)), 3),
        "findings": findings,
        "demands": demands,
    }


def run_advanced_design_court(scene: Dict[str, Any], validation: Dict[str, Any] | None = None) -> Dict[str, Any]:
    op_types = _op_types(scene)
    validation = validation if isinstance(validation, dict) else {}
    aerospace = validation.get("aerospace", {}) if isinstance(validation.get("aerospace"), dict) else {}
    readiness = float(aerospace.get("readiness_score", 0.55) or 0.55)

    reviews = [
        _review(
            "aero_structures",
            0.45 + 0.12 * ("load_case" in op_types) + 0.1 * ("fatigue" in op_types) + 0.1 * ("buckling" in op_types) + 0.08 * ("modal" in op_types),
            [
                "Structural domains encoded: " + ", ".join(sorted(op_types & {"load_case", "fatigue", "buckling", "modal"})),
            ],
            [
                "Run stress, buckling, modal, and fatigue margins before flight classification.",
                "Track load paths to named faces, fasteners, and datums.",
            ],
        ),
        _review(
            "thermal_fluids",
            0.5 + 0.16 * ("thermal" in op_types) + 0.14 * ("cfd" in op_types) + 0.08 * ("duct" in op_types or "heat_sink" in op_types),
            [
                "Thermal/flow intent is explicit." if {"thermal", "cfd"} & op_types else "No thermal-fluid intent found.",
            ],
            [
                "Add conjugate heat transfer for ducts, fins, motors, and avionics.",
                "Require pressure drop and max temperature targets for cooling geometry.",
            ],
        ),
        _review(
            "composites",
            0.48 + 0.28 * ("composite" in op_types),
            [
                "Composite layup exists." if "composite" in op_types else "No laminate stack defined.",
            ],
            [
                "Add ply orientations, drape feasibility, core material, and delamination checks.",
                "Export ply table as certification evidence.",
            ],
        ),
        _review(
            "certification",
            0.38 + 0.16 * ("gd_t" in op_types) + 0.16 * ("pmi" in op_types) + 0.12 * ("inspection" in op_types) + 0.1 * ("tolerance" in op_types),
            [
                "MBD evidence present." if {"gd_t", "pmi", "inspection"} <= op_types else "MBD evidence incomplete.",
            ],
            [
                "Block ship status without traceability from requirement to feature to analysis to inspection.",
                "Attach GD&T to stable semantic faces and datums.",
            ],
        ),
        _review(
            "manufacturing_quality",
            0.54 + 0.12 * ("fastener" in op_types) + 0.08 * ("inspection" in op_types) + 0.08 * ("material" in op_types),
            [
                "Fastener/preload assumptions present." if "fastener" in op_types else "Fastener assumptions not explicit.",
            ],
            [
                "Add edge distance, torque, insert, and inspection rules for every fastener.",
                "Generate process-specific CNC/additive/composite quality plans.",
            ],
        ),
    ]

    disagreements = []
    if "lattice" in op_types:
        disagreements.append(
            {
                "topic": "lattice_in_flight_hardware",
                "positions": {
                    "aero_structures": "Accept only with fatigue and inspection evidence.",
                    "manufacturing_quality": "Hidden lattice surfaces complicate inspection.",
                    "thermal_fluids": "Lattice may help cooling if flow paths are controlled.",
                },
            }
        )
    if "composite" in op_types and "fastener" in op_types:
        disagreements.append(
            {
                "topic": "composite_fastener_interface",
                "positions": {
                    "composites": "Needs bearing/bypass and delamination margins.",
                    "manufacturing_quality": "Requires insert or washer stack definition.",
                },
            }
        )

    resolved_tradeoffs = [
        {
            "topic": "authority",
            "decision": "Do not ship from mesh appearance; require source feature, physics, and inspection evidence.",
        },
        {
            "topic": "autonomy",
            "decision": "ADA may propose flight-hardware diffs, but human release requires evidence package signoff.",
        },
    ]
    if disagreements:
        resolved_tradeoffs.append(
            {
                "topic": "disagreement_resolution",
                "decision": "Keep high-performance geometry as variants until inspection and physics gates pass.",
            }
        )

    consensus = sum(review["score"] for review in reviews) / float(len(reviews))
    score = round(0.68 * consensus + 0.32 * readiness, 3)
    status = "certification_candidate" if score >= 0.82 and not disagreements else "prototype_candidate" if score >= 0.68 else "flight_review_required"

    return {
        "reviews": reviews,
        "disagreements": disagreements,
        "resolved_tradeoffs": resolved_tradeoffs,
        "consensus_score": score,
        "status": status,
    }
