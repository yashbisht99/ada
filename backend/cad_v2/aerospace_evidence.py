from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List


REQUIREMENT_BY_OP = {
    "load_case": "REQ-LOAD-001",
    "fatigue": "REQ-FATIGUE-001",
    "buckling": "REQ-BUCKLING-001",
    "modal": "REQ-MODAL-001",
    "thermal": "REQ-THERMAL-001",
    "cfd": "REQ-FLUID-001",
    "gd_t": "REQ-MBD-001",
    "pmi": "REQ-MBD-002",
    "inspection": "REQ-INSPECT-001",
    "tolerance": "REQ-TOL-001",
    "fastener": "REQ-FASTENER-001",
    "fastener_stack": "REQ-FASTENER-001",
    "composite": "REQ-COMPOSITE-001",
    "composite_ply": "REQ-COMPOSITE-001",
}


def _timeline(scene: Dict[str, Any]) -> List[Dict[str, Any]]:
    direct = scene.get("feature_timeline") if isinstance(scene.get("feature_timeline"), list) else []
    if direct:
        return [op for op in direct if isinstance(op, dict)]
    source = scene.get("source_spec") if isinstance(scene.get("source_spec"), dict) else {}
    ops = source.get("operations") if isinstance(source.get("operations"), list) else []
    return [op for op in ops if isinstance(op, dict)]


def _requirement_text(req_id: str) -> str:
    return {
        "REQ-LOAD-001": "Design shall define limit loads and minimum safety factor.",
        "REQ-FATIGUE-001": "Design shall document fatigue cycle assumptions.",
        "REQ-BUCKLING-001": "Compression-bearing structures shall include buckling margin.",
        "REQ-MODAL-001": "Design shall avoid resonance below the specified modal threshold.",
        "REQ-THERMAL-001": "Design shall account for thermal environment and expansion.",
        "REQ-FLUID-001": "Flow or cooling paths shall include pressure/velocity assumptions.",
        "REQ-MBD-001": "Model shall define datums and GD&T controls.",
        "REQ-MBD-002": "Model shall include PMI for manufacturing and inspection.",
        "REQ-INSPECT-001": "Model shall define inspection method and sample plan.",
        "REQ-TOL-001": "Critical fits shall include tolerances.",
        "REQ-FASTENER-001": "Fasteners shall include preload and edge-distance assumptions.",
        "REQ-COMPOSITE-001": "Composite structures shall include ply count and layup intent.",
    }.get(req_id, "Design shall preserve traceable engineering intent.")


def build_certification_evidence_package(scene: Dict[str, Any], aerospace_report: Dict[str, Any] | None = None) -> Dict[str, Any]:
    timeline = _timeline(scene)
    by_req: Dict[str, List[Dict[str, Any]]] = {}
    for op in timeline:
        op_type = str(op.get("type", ""))
        req_id = REQUIREMENT_BY_OP.get(op_type)
        if not req_id:
            continue
        by_req.setdefault(req_id, []).append(op)

    requirements = [
        {
            "id": req_id,
            "text": _requirement_text(req_id),
            "status": "covered" if ops else "missing",
        }
        for req_id, ops in sorted(by_req.items())
    ]

    traceability = []
    for req in requirements:
        ops = by_req.get(req["id"], [])
        traceability.append(
            {
                "requirement_id": req["id"],
                "linked_feature_ids": [str(op.get("id", "")) for op in ops if str(op.get("id", ""))],
                "linked_feature_labels": [str(op.get("label", "")) for op in ops if str(op.get("label", ""))],
                "evidence_status": "analysis_required" if req["id"].startswith(("REQ-FATIGUE", "REQ-BUCKLING", "REQ-MODAL", "REQ-THERMAL", "REQ-FLUID")) else "definition_available",
            }
        )

    inspection_features = [op for op in timeline if op.get("type") in {"inspection", "gd_t", "pmi", "tolerance"}]
    inspection_plan = [
        {
            "step": idx + 1,
            "feature_id": str(op.get("id", "")),
            "method": (op.get("params", {}) or {}).get("method", "CMM" if op.get("type") != "pmi" else "PMI review"),
            "acceptance": str(op.get("label", "")),
        }
        for idx, op in enumerate(inspection_features)
    ]

    risk_register = []
    for check in (aerospace_report or {}).get("checks", []) or []:
        if isinstance(check, dict) and not check.get("ok"):
            risk_register.append(
                {
                    "risk": str(check.get("name", "unknown")),
                    "severity": str(check.get("severity", "warn")),
                    "mitigation": f"Resolve gate: {check.get('detail', '')}",
                }
            )

    return {
        "standard": "ADA_AEROSPACE_EVIDENCE_V1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "session_id": scene.get("session_id", ""),
        "requirements": requirements,
        "traceability_matrix": traceability,
        "inspection_plan": inspection_plan,
        "risk_register": risk_register,
        "aerospace_report": aerospace_report or {},
    }
