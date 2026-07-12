from __future__ import annotations

from typing import Any, Dict, List

from contracts import VerificationResult


class ResultVerifier:
    """Heuristic verifier for tool outputs before finalization."""

    def verify(self, tool_name: str, result: Any, args: Dict[str, Any]) -> VerificationResult:
        checks: List[Dict[str, Any]] = []
        _ = args

        if isinstance(result, dict) and result.get("error"):
            checks.append({"name": "execution", "ok": False, "detail": str(result.get("error"))})
            return VerificationResult(status="fail", summary="Tool returned an error.", checks=checks)

        if tool_name in {"analyze_project", "analyze_file", "check_code_errors"}:
            has_content = bool(result)
            checks.append({"name": "non_empty", "ok": has_content, "detail": "code intel payload present"})
            if not has_content:
                return VerificationResult(status="warn", summary="Code intel returned empty output.", checks=checks)

        if tool_name in {"translate", "translate_document"}:
            ok = isinstance(result, dict) and bool(result.get("translated") or result.get("translated_path"))
            checks.append({"name": "translated_content", "ok": ok, "detail": "translation output detected"})
            if not ok:
                return VerificationResult(status="warn", summary="Translation produced incomplete output.", checks=checks)

        if tool_name in {"quantum_optimize", "quantum_simulate_circuit", "quantum_analyze_problem"}:
            ok = isinstance(result, dict) and not bool(result.get("error"))
            checks.append({"name": "quantum_result", "ok": ok, "detail": "quantum payload validated"})
            if not ok:
                return VerificationResult(status="warn", summary="Quantum result needs review.", checks=checks)

        if tool_name == "quantum_discovery_simulation":
            required = {
                "run_id",
                "status",
                "ranked_candidates",
                "rejected_candidates",
                "frontier_summary",
                "provider_usage",
                "cost_summary",
                "uncertainty_summary",
                "recommended_next_experiments",
                "artifacts",
            }
            has_contract = isinstance(result, dict) and required.issubset(set(result.keys()))
            checks.append({"name": "discovery_contract", "ok": has_contract, "detail": "normalized result contract"})
            artifacts = result.get("artifacts", {}) if isinstance(result, dict) else {}
            artifacts_ok = isinstance(artifacts, dict) and bool(artifacts.get("report")) and bool(artifacts.get("candidates")) and bool(artifacts.get("provenance"))
            checks.append({"name": "discovery_artifacts", "ok": artifacts_ok, "detail": "artifact paths present"})
            if not has_contract:
                return VerificationResult(status="fail", summary="Discovery result contract incomplete.", checks=checks)
            if not artifacts_ok:
                return VerificationResult(status="warn", summary="Discovery artifacts missing.", checks=checks)

        if tool_name in {
            "cad_create_assembly",
            "cad_create_from_image",
            "cad_create_from_reference",
            "cad_iterate_design",
            "generate_cad",
            "generate_cad_from_image",
            "iterate_cad",
            "cad_restore_snapshot",
            "cad_live_edit_loop",
            "cad_merge_variant",
        }:
            ok = isinstance(result, dict) and bool((result.get("scene") or {}).get("parts"))
            checks.append({"name": "cad_scene_parts", "ok": ok, "detail": "scene contains parts"})
            if not ok:
                return VerificationResult(status="warn", summary="CAD scene is incomplete.", checks=checks)

        if tool_name == "cad_validate_model":
            status = str((result.get("validation") or {}).get("status", "unknown")) if isinstance(result, dict) else "unknown"
            ok = status in {"pass", "warn", "fail"}
            checks.append({"name": "cad_validation_status", "ok": ok, "detail": status})
            if status == "fail":
                return VerificationResult(status="warn", summary="CAD validation reported failures.", checks=checks)

        if tool_name == "cad_export_package":
            ok = isinstance(result, dict) and bool(result.get("exports"))
            checks.append({"name": "cad_export_files", "ok": ok, "detail": "export payload has files"})
            if not ok:
                return VerificationResult(status="warn", summary="CAD export produced no files.", checks=checks)

        if tool_name in {"cad_get_timeline", "cad_simulate_counterfactual", "cad_get_hologram_state", "multiverse_simulate", "time_travel_memory"}:
            ok = isinstance(result, dict) and not bool(result.get("error"))
            checks.append({"name": "cad_meta_payload", "ok": ok, "detail": "timeline/counterfactual payload present"})
            if not ok:
                return VerificationResult(status="warn", summary="CAD metadata payload incomplete.", checks=checks)

        return VerificationResult(status="pass", summary="Verification checks passed.", checks=checks)
