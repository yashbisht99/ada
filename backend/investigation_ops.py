"""
Investigation operations — lawful agency workflow layer for ADA.

Does NOT perform live GPS, SS7, carrier intrusion, or NCIC hacking.
Provides: attestation logging, chain-of-custody, licensed connector orchestration.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
from typing import Any, Dict, List, Optional


class InvestigationLedger:
    """Append-only audit trail for sensitive investigations."""

    def __init__(self, data_root: str) -> None:
        self._path = os.path.join(data_root, "investigation_audit.jsonl")
        os.makedirs(data_root, exist_ok=True)

    def record(
        self,
        *,
        case_id: str,
        action: str,
        operator: str,
        attestation: Optional[Dict[str, Any]] = None,
        detail: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        entry = {
            "timestamp": _dt.datetime.now(_dt.timezone.utc).isoformat(),
            "case_id": case_id,
            "action": action,
            "operator": operator or "operator",
            "attestation": attestation or {},
            "detail": detail or {},
            "entry_hash": "",
        }
        payload = json.dumps(entry, sort_keys=True, default=str)
        entry["entry_hash"] = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
        with open(self._path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, default=str) + "\n")
        return entry

    def recent(self, limit: int = 50) -> List[Dict[str, Any]]:
        if not os.path.isfile(self._path):
            return []
        lines: List[str] = []
        with open(self._path, "r", encoding="utf-8") as handle:
            lines = handle.readlines()
        out = []
        for line in lines[-limit:]:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return out


def validate_attestation(args: Dict[str, Any]) -> Dict[str, Any]:
    """Require explicit lawful-use attestation for sensitive traces."""
    attestation = args.get("attestation") if isinstance(args.get("attestation"), dict) else {}
    case_ref = str(attestation.get("case_reference") or args.get("case_reference") or "").strip()
    operator = str(attestation.get("operator_id") or args.get("operator_id") or "").strip()
    purpose = str(attestation.get("purpose") or args.get("purpose") or args.get("context") or "").strip()
    lawful_basis = str(attestation.get("lawful_basis") or "").strip()
    confirmed = bool(
        attestation.get("confirmed")
        or args.get("authorized")
        or args.get("_confirmed")
    )
    ok = confirmed and len(case_ref) >= 3 and len(operator) >= 2 and len(purpose) >= 8
    return {
        "valid": ok,
        "case_reference": case_ref,
        "operator_id": operator,
        "purpose": purpose,
        "lawful_basis": lawful_basis or "user_attested",
        "confirmed": confirmed,
        "missing": [
            field
            for field, present in [
                ("case_reference", case_ref),
                ("operator_id", operator),
                ("purpose", purpose),
                ("authorization_confirm", confirmed),
            ]
            if not present
        ],
    }


def attestation_denied_widget(case_id: str, validation: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "type": "threat_watch",
        "title": "Attestation Required",
        "priority": 10,
        "payload": {
            "schema": "ada.mission.caseboard.v1",
            "case_id": case_id,
            "title": "Lawful Use Gate",
            "confidence": 0.0,
            "entities": [{"id": f"case:{case_id}", "label": "Sensitive trace blocked", "type": "case", "metadata": {}}],
            "relationships": [],
            "timeline": [{"label": "Gate", "detail": "Sensitive intelligence requires case reference, operator ID, and purpose."}],
            "sources": [{"name": "ADA Policy", "category": "policy", "detail": "Live location and telecom intrusion are not available in ADA."}],
            "findings": [
                "ADA does not provide live GPS, tower triangulation, SS7, or subscriber-database access.",
                f"Missing attestation fields: {', '.join(validation.get('missing') or []) or 'confirmation'}",
            ],
            "next_steps": [
                "Provide attestation.case_reference, attestation.operator_id, attestation.purpose, attestation.confirmed=true.",
                "Use licensed carrier/LPR/court-record APIs your agency already contracts — wire keys in ADA settings.",
            ],
            "safety": {
                "allowed": False,
                "status": "attestation_required",
                "mode": "lawful_ops",
                "prohibited_capabilities": [
                    "live GPS tracking of third parties",
                    "carrier tower triangulation",
                    "SS7 / telecom backdoor access",
                    "NCIC or criminal DB without licensed connector",
                ],
            },
        },
    }
