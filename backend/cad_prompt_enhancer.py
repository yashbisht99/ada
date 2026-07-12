from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional

import requests

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - optional dependency
    load_dotenv = None  # type: ignore[assignment]

try:
    from google import genai
except Exception:  # pragma: no cover - optional dependency
    genai = None


class CadPromptEnhancer:
    """
    Dedicated prompt enhancement layer for CAD requests.
    This runs independently from the live voice model path.
    """
    CAD_PROMPT_ENHANCER_SYSTEM_PROMPT = (
        "You are ADA-CAD-PROMPT-ARCHITECT, an elite mechanical CAD prompt engineer. "
        "Your job is to convert user intent plus optional scene/image analysis into a precise production-ready CAD prompt. "
        "Prioritize geometry fidelity, manufacturability, and assembly coherence. "
        "For create mode: produce a complete multi-part assembly instruction with explicit structure and constraints. "
        "For edit mode: preserve unchanged topology and apply only requested localized edits. "
        "When image analysis is present: preserve silhouette, proportions, and key motifs while inferring a realistic part hierarchy. "
        "Always include practical dimensions in mm, tolerance intent, materials/finishes, and quality guardrails. "
        "Output STRICT JSON only with keys: enhanced_prompt, intent, scope, quality_checks. "
        "enhanced_prompt must be one compact paragraph without markdown. "
        "intent must be create or edit. "
        "scope must be full (create) or local (edit). "
        "quality_checks must be an array of concise checks for geometry validity and manufacturability."
    )

    def __init__(self, enabled: Optional[bool] = None) -> None:
        self._load_environment()
        env_flag = str(os.getenv("ADA_CAD_PROMPT_ENHANCER_ENABLED", "1")).strip().lower()
        self.enabled = bool(enabled) if enabled is not None else env_flag not in {"0", "false", "off", "no"}

        # Gemini optional fallback client.
        self._gemini_client = None
        gemini_api_key = str(os.getenv("GEMINI_API_KEY", "")).strip()
        if self.enabled and genai is not None and gemini_api_key:
            try:
                self._gemini_client = genai.Client(api_key=gemini_api_key, http_options={"api_version": "v1beta"})
            except Exception:
                self._gemini_client = None

        # NVIDIA OpenAI-compatible endpoint config.
        self.nvidia_api_key = str(os.getenv("NVIDIA_API_KEY", "")).strip()
        self.nvidia_base_url = str(os.getenv("NVIDIA_API_BASE_URL", "https://integrate.api.nvidia.com/v1")).strip().rstrip("/")
        self.nvidia_default_model = str(os.getenv("NVIDIA_CAD_PROMPT_MODEL", "z-ai/glm5")).strip() or "z-ai/glm5"

    @staticmethod
    def _load_environment() -> None:
        if load_dotenv is None:
            return
        try:
            repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            load_dotenv(os.path.join(repo_root, ".env"), override=False)
            load_dotenv(os.path.join(repo_root, "backend", ".env"), override=False)
        except Exception:
            return

    @staticmethod
    def _compact(text: str) -> str:
        return " ".join(str(text or "").strip().split())

    @staticmethod
    def _strip_thinking_blocks(text: str) -> str:
        raw = str(text or "")
        if not raw:
            return ""
        # Remove thought blocks commonly emitted by reasoning models.
        cleaned = re.sub(r"<think>[\s\S]*?</think>", " ", raw, flags=re.IGNORECASE)
        cleaned = cleaned.replace("```json", " ").replace("```", " ")
        return cleaned.strip()

    def _scene_summary(self, scene: Optional[Dict[str, Any]]) -> str:
        if not isinstance(scene, dict):
            return ""
        parts = scene.get("parts", []) or []
        if not isinstance(parts, list) or not parts:
            return ""
        names = [str((part or {}).get("name", "")).strip() for part in parts[:12]]
        names = [name for name in names if name]
        selected = scene.get("active_selection", {}) or {}
        selected_id = str(selected.get("id", "")).strip() if isinstance(selected, dict) else ""
        return f"parts={len(parts)} selected={selected_id or 'none'} names={', '.join(names)}"

    @staticmethod
    def _context_to_json(context: Optional[Dict[str, Any]]) -> str:
        if not isinstance(context, dict) or not context:
            return "{}"
        compacted: Dict[str, Any] = {}
        if "workflow" in context:
            compacted["workflow"] = str(context.get("workflow", "")).strip()
        if "source_image" in context and isinstance(context.get("source_image"), dict):
            source_image = context.get("source_image", {}) or {}
            compacted["source_image"] = {
                "path": str(source_image.get("path", "")).strip(),
                "source": str(source_image.get("source", "")).strip(),
            }
        if "image_analysis" in context and isinstance(context.get("image_analysis"), dict):
            analysis = context.get("image_analysis", {}) or {}
            compacted["image_analysis"] = {
                "subject": str(analysis.get("subject", "")).strip(),
                "assembly_type": str(analysis.get("assembly_type", "")).strip(),
                "primary_geometry": str(analysis.get("primary_geometry", "")).strip(),
                "symmetry": str(analysis.get("symmetry", "")).strip(),
                "key_features": analysis.get("key_features", [])[:16] if isinstance(analysis.get("key_features"), list) else [],
                "component_breakdown": analysis.get("component_breakdown", [])[:16] if isinstance(analysis.get("component_breakdown"), list) else [],
                "materials": analysis.get("materials", [])[:12] if isinstance(analysis.get("materials"), list) else [],
                "colors": analysis.get("colors", [])[:12] if isinstance(analysis.get("colors"), list) else [],
                "dominant_dimensions_mm": analysis.get("dominant_dimensions_mm", {}) if isinstance(analysis.get("dominant_dimensions_mm"), dict) else {},
                "tolerances_mm": str(analysis.get("tolerances_mm", "")).strip(),
                "manufacturability_notes": analysis.get("manufacturability_notes", [])[:12] if isinstance(analysis.get("manufacturability_notes"), list) else [],
            }
        if "user_hint" in context:
            compacted["user_hint"] = str(context.get("user_hint", "")).strip()
        try:
            return json.dumps(compacted, separators=(",", ":"), ensure_ascii=True)
        except Exception:
            return "{}"

    @staticmethod
    def _image_context_summary(context: Optional[Dict[str, Any]]) -> str:
        if not isinstance(context, dict):
            return ""
        analysis = context.get("image_analysis", {})
        if not isinstance(analysis, dict):
            return ""
        subject = str(analysis.get("subject", "")).strip()
        features = analysis.get("key_features", [])
        if not isinstance(features, list):
            features = []
        feature_text = ", ".join(str(v).strip() for v in features[:8] if str(v).strip())
        if not subject and not feature_text:
            return ""
        if subject and feature_text:
            return f"image subject={subject}; key_features={feature_text}"
        return f"image subject={subject or 'n/a'}; key_features={feature_text or 'n/a'}"

    def _heuristic_enhance(self, prompt: str, mode: str, context: Optional[Dict[str, Any]] = None) -> str:
        base = self._compact(prompt)
        if not base:
            return ""
        image_summary = self._image_context_summary(context)

        if mode == "edit":
            return (
                f"{base}. "
                "Apply only localized edits to the current assembly. "
                "Preserve all unaffected parts, constraints, materials, and references. "
                "Do not regenerate the full model unless explicitly requested. "
                "Maintain manufacturable geometry and stable mating references."
            )

        detailed = (
            f"{base}. "
            "Build an industry-grade CAD assembly with coherent dimensions in mm, "
            "realistic materials, robust manufacturable features, and clear part hierarchy. "
            "Preserve symmetry cues, enforce plausible clearances, and output as a single unified assembly model."
        )
        if image_summary:
            detailed += f" Reference context: {image_summary}. "
        return detailed

    @staticmethod
    def _extract_json(text: str) -> Dict[str, Any]:
        cleaned = CadPromptEnhancer._strip_thinking_blocks(text)
        if not cleaned:
            return {}
        try:
            data = json.loads(cleaned)
            if isinstance(data, dict):
                return data
        except Exception:
            pass
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if not match:
            return {}
        try:
            data = json.loads(match.group(0))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _parse_llm_payload(self, text: str, mode: str) -> Dict[str, Any]:
        cleaned = self._compact(self._strip_thinking_blocks(text))
        if not cleaned:
            return {}

        payload = self._extract_json(cleaned)
        enhanced = self._compact(str(payload.get("enhanced_prompt", "")))
        if enhanced:
            payload["enhanced_prompt"] = enhanced
            payload["intent"] = str(payload.get("intent", mode))
            payload["scope"] = str(payload.get("scope", "local" if mode == "edit" else "full"))
            return payload

        # If model did not return strict JSON, still salvage as prompt text.
        return {
            "enhanced_prompt": cleaned,
            "intent": mode,
            "scope": "local" if mode == "edit" else "full",
        }

    def _build_instruction(
        self,
        prompt: str,
        mode: str,
        scene: Optional[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        scene_summary = self._scene_summary(scene)
        context_json = self._context_to_json(context)
        mode_text = "local edit request" if mode == "edit" else "new CAD generation request"
        guardrail = (
            "Preserve existing assembly topology and edit only necessary fragments."
            if mode == "edit"
            else "Produce a complete, professional multi-part assembly request with measurable quality goals."
        )
        instruction = self.CAD_PROMPT_ENHANCER_SYSTEM_PROMPT
        user_block = (
            f"Mode: {mode_text}\n"
            f"Guardrail: {guardrail}\n"
            f"Scene summary: {scene_summary or 'n/a'}\n"
            f"Structured context JSON: {context_json}\n"
            f"User request: {prompt}"
        )
        return f"System Directive:\n{instruction}\n\nInput:\n{user_block}"

    def _gemini_enhance(
        self,
        prompt: str,
        mode: str,
        model: str,
        fallback_chain: Optional[List[str]] = None,
        scene: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if self._gemini_client is None:
            return {}

        content = self._build_instruction(prompt=prompt, mode=mode, scene=scene, context=context)
        models = [m for m in [model, *(fallback_chain or [])] if str(m).strip()]
        for model_name in models:
            if not str(model_name).startswith("models/"):
                continue
            try:
                response = self._gemini_client.models.generate_content(model=model_name, contents=content)
                payload = self._parse_llm_payload(getattr(response, "text", "") or "", mode=mode)
                enhanced = self._compact(str(payload.get("enhanced_prompt", "")))
                if enhanced:
                    payload["model"] = model_name
                    return payload
            except Exception:
                continue
        return {}

    def _nvidia_enhance(
        self,
        prompt: str,
        mode: str,
        model: str,
        fallback_chain: Optional[List[str]] = None,
        scene: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not self.nvidia_api_key:
            return {}
        base = self.nvidia_base_url
        if not base:
            return {}

        system_prompt = self.CAD_PROMPT_ENHANCER_SYSTEM_PROMPT
        user_prompt = self._build_instruction(prompt=prompt, mode=mode, scene=scene, context=context)

        models: List[str] = []
        for candidate in [model, *(fallback_chain or []), self.nvidia_default_model]:
            text = str(candidate or "").strip()
            if not text or text in models:
                continue
            models.append(text)
        invoke_url = f"{base}/chat/completions"
        base_headers = {
            "Authorization": f"Bearer {self.nvidia_api_key}",
        }
        for model_name in models:
            # NVIDIA endpoint models are not prefixed with "models/".
            if str(model_name).startswith("models/"):
                continue
            payload = {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.35,
                "top_p": 0.9,
                "top_k": 20,
                "presence_penalty": 0,
                "repetition_penalty": 1,
                "max_tokens": 16384,
                "stream": False,
                "chat_template_kwargs": {"enable_thinking": True, "clear_thinking": False},
            }
            try:
                headers = dict(base_headers)
                headers["Accept"] = "application/json"
                response = requests.post(
                    invoke_url,
                    headers=headers,
                    json=payload,
                    timeout=(8, 45),
                )
                if response.status_code >= 400:
                    continue
                data = response.json() if response.content else {}
                choices = data.get("choices", []) if isinstance(data, dict) else []
                content = ""
                if choices:
                    message = choices[0].get("message", {}) or {}
                    content = str(message.get("content", "") or "")
                parsed = self._parse_llm_payload(content, mode=mode)
                enhanced = self._compact(str(parsed.get("enhanced_prompt", "")))
                if enhanced:
                    parsed["model"] = model_name
                    return parsed
            except Exception:
                continue
        return {}

    def enhance_prompt(
        self,
        prompt: str,
        mode: str = "create",
        model: str = "",
        fallback_chain: Optional[List[str]] = None,
        scene: Optional[Dict[str, Any]] = None,
        provider: str = "",
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        raw = self._compact(prompt)
        normalized_mode = "edit" if str(mode).strip().lower() == "edit" else "create"
        selected_provider = str(provider or "").strip().lower()
        selected_model = str(model or "").strip()
        if selected_provider == "nvidia" and not selected_model:
            selected_model = self.nvidia_default_model
        if not raw:
            return {
                "ok": False,
                "mode": normalized_mode,
                "original_prompt": "",
                "enhanced_prompt": "",
                "strategy": "none",
                "notes": ["empty_prompt"],
            }

        llm_payload: Dict[str, Any] = {}
        if self.enabled and selected_model:
            if selected_provider == "nvidia":
                llm_payload = self._nvidia_enhance(
                    prompt=raw,
                    mode=normalized_mode,
                    model=selected_model,
                    fallback_chain=fallback_chain,
                    scene=scene,
                    context=context,
                )
                if not llm_payload:
                    gemini_candidates: List[str] = []
                    for candidate in [*(fallback_chain or []), "models/gemini-2.5-flash", "models/gemini-2.5-pro"]:
                        name = str(candidate or "").strip()
                        if not name.startswith("models/"):
                            continue
                        if name in gemini_candidates:
                            continue
                        gemini_candidates.append(name)
                    if gemini_candidates:
                        llm_payload = self._gemini_enhance(
                            prompt=raw,
                            mode=normalized_mode,
                            model=gemini_candidates[0],
                            fallback_chain=gemini_candidates[1:],
                            scene=scene,
                            context=context,
                        )
                        if llm_payload:
                            selected_provider = "gemini"
            else:
                llm_payload = self._gemini_enhance(
                    prompt=raw,
                    mode=normalized_mode,
                    model=selected_model,
                    fallback_chain=fallback_chain,
                    scene=scene,
                    context=context,
                )

        enhanced = self._compact(str(llm_payload.get("enhanced_prompt", "")))
        strategy = "llm"
        notes: List[str] = []
        resolved_model = str(llm_payload.get("model", selected_model or ""))

        if not enhanced:
            enhanced = self._heuristic_enhance(raw, normalized_mode, context=context)
            strategy = "heuristic"
            if self.enabled and selected_model:
                notes.append("llm_unavailable_or_failed")

        return {
            "ok": True,
            "mode": normalized_mode,
            "provider": selected_provider or "gemini",
            "original_prompt": raw,
            "enhanced_prompt": enhanced,
            "intent": str(llm_payload.get("intent", normalized_mode)),
            "scope": str(llm_payload.get("scope", "local" if normalized_mode == "edit" else "full")),
            "quality_checks": llm_payload.get("quality_checks", []),
            "strategy": strategy,
            "model": resolved_model or "heuristic",
            "notes": notes,
        }
