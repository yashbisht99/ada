from __future__ import annotations

import json
import os
import re
import shutil
from typing import Any, Dict, List

try:
    import trimesh
except Exception:
    trimesh = None


class CADExporter:
    """Export assembly package (STL/STEP/GLB + manifest)."""

    MATERIAL_COLORS = {
        "aluminum": "#AFB8C4",
        "steel": "#7E8792",
        "titanium": "#8D98AA",
        "copper": "#C46A2D",
        "brass": "#D5B56F",
        "ceramic": "#D8E5EF",
        "ceramic_composite": "#BED0E0",
        "polymer_composite": "#2D77B8",
        "carbon_fiber": "#3D434C",
        "abs": "#3A4049",
        "pla": "#5A83A6",
        "petg": "#7FB5C8",
    }

    @staticmethod
    def _hex_to_rgba(color: str, default: List[int]) -> List[int]:
        if not color:
            return list(default)
        text = color.strip()
        match = re.fullmatch(r"#?([0-9a-fA-F]{6})", text)
        if not match:
            return list(default)
        raw = match.group(1)
        return [int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16), 255]

    def _part_rgba(self, part: Dict[str, Any]) -> List[int]:
        appearance = part.get("appearance", {}) or {}
        if isinstance(appearance, dict):
            color = str(appearance.get("color", "") or "")
            rgba = self._hex_to_rgba(color, [])
            if rgba:
                return rgba

        material = str(part.get("material", "") or "").lower()
        mat_color = self.MATERIAL_COLORS.get(material, "#8AA3C7")
        return self._hex_to_rgba(mat_color, [138, 163, 199, 255])

    @staticmethod
    def _transform_matrix(part: Dict[str, Any]) -> Any:
        if trimesh is None:
            return None
        transform = part.get("transform", {}) or {}
        tx = float(transform.get("x", 0.0))
        ty = float(transform.get("y", 0.0))
        tz = float(transform.get("z", 0.0))
        rx = float(transform.get("rx", 0.0))
        ry = float(transform.get("ry", 0.0))
        rz = float(transform.get("rz", 0.0))
        sx = float(transform.get("sx", 1.0))
        sy = float(transform.get("sy", 1.0))
        sz = float(transform.get("sz", 1.0))
        try:
            return trimesh.transformations.compose_matrix(
                scale=[sx, sy, sz],
                angles=[rx, ry, rz],
                translate=[tx, ty, tz],
            )
        except Exception:
            return None

    def export_scene(self, scene: Dict[str, Any], session_root: str, formats: List[str]) -> Dict[str, Any]:
        exports_dir = os.path.join(session_root, "exports")
        os.makedirs(exports_dir, exist_ok=True)

        normalized = {f.lower() for f in (formats or [])}
        if not normalized:
            normalized = {"stl", "step", "glb", "manifest"}

        out: Dict[str, Any] = {
            "exports": {},
            "warnings": [],
        }
        parts = scene.get("parts", []) or []
        meshes = []
        scene_graph = trimesh.Scene(base_frame="assembly") if trimesh is not None else None
        first_step = ""
        first_stl = ""
        part_glbs: Dict[str, str] = {}

        for part in parts:
            artifacts = (part.get("artifacts") or {})
            stl = artifacts.get("part_stl", "")
            step = artifacts.get("part_step", "")
            if not first_stl and stl and os.path.exists(stl):
                first_stl = stl
            if not first_step and step and os.path.exists(step):
                first_step = step
            if not stl or not os.path.exists(stl):
                continue

            if trimesh is None:
                continue
            try:
                mesh = trimesh.load(stl, force="mesh")
                try:
                    mesh.visual.face_colors = self._part_rgba(part)
                except Exception:
                    pass
                transformed = mesh.copy()
                transform_matrix = self._transform_matrix(part)
                if transform_matrix is not None:
                    try:
                        transformed.apply_transform(transform_matrix)
                    except Exception:
                        pass
                meshes.append(transformed)

                part_id = str(part.get("part_id", "") or part.get("name", "") or f"part_{len(meshes)}")
                if scene_graph is not None:
                    try:
                        node_name = part_id
                        geom_name = part_id
                        local_mesh = mesh.copy()
                        scene_graph.add_geometry(local_mesh, node_name=node_name, geom_name=geom_name, transform=transform_matrix)
                    except Exception as exc:
                        out_warning = f"scene_node_failed:{part_id}:{exc}"
                        if out_warning not in out.setdefault("warnings", []):
                            out.setdefault("warnings", []).append(out_warning)
            except Exception:
                continue

        combined = None
        if trimesh is not None and meshes:
            try:
                combined = trimesh.util.concatenate(meshes)
            except Exception as exc:
                out["warnings"].append(f"combine_failed:{exc}")

        if "stl" in normalized:
            stl_path = os.path.join(exports_dir, "assembly.stl")
            if combined is not None:
                try:
                    combined.export(stl_path)
                    out["exports"]["stl"] = stl_path
                except Exception as exc:
                    out["warnings"].append(f"stl_export_failed:{exc}")
            if "stl" not in out["exports"] and first_stl and os.path.exists(first_stl):
                shutil.copy2(first_stl, stl_path)
                out["exports"]["stl"] = stl_path
                out["warnings"].append("stl_fallback_first_part")

        if "glb" in normalized:
            glb_path = os.path.join(exports_dir, "assembly.glb")
            if scene_graph is not None and len(getattr(scene_graph, "geometry", {}) or {}) > 0:
                try:
                    glb_data = scene_graph.export(file_type="glb")
                    with open(glb_path, "wb") as handle:
                        handle.write(glb_data)
                    out["exports"]["glb"] = glb_path
                except Exception as exc:
                    out["warnings"].append(f"glb_export_failed:{exc}")
            elif combined is not None:
                try:
                    glb_data = combined.export(file_type="glb")
                    with open(glb_path, "wb") as handle:
                        handle.write(glb_data)
                    out["exports"]["glb"] = glb_path
                    out["warnings"].append("glb_export_fallback_combined_mesh")
                except Exception as exc:
                    out["warnings"].append(f"glb_export_failed:{exc}")
            else:
                out["warnings"].append("glb_export_skipped_no_combined_mesh")

            parts_glb_dir = os.path.join(exports_dir, "parts_glb")
            os.makedirs(parts_glb_dir, exist_ok=True)
            if trimesh is not None:
                for part in parts:
                    artifacts = (part.get("artifacts") or {})
                    stl = artifacts.get("part_stl", "")
                    if not stl or not os.path.exists(stl):
                        continue
                    part_id = str(part.get("part_id", "") or part.get("name", "") or "part")
                    try:
                        part_mesh = trimesh.load(stl, force="mesh")
                        try:
                            part_mesh.visual.face_colors = self._part_rgba(part)
                        except Exception:
                            pass
                        part_scene = trimesh.Scene(base_frame=part_id)
                        part_scene.add_geometry(part_mesh, node_name=part_id, geom_name=part_id)
                        part_path = os.path.join(parts_glb_dir, f"{part_id}.glb")
                        glb_data = part_scene.export(file_type="glb")
                        with open(part_path, "wb") as handle:
                            handle.write(glb_data)
                        part_glbs[part_id] = part_path
                    except Exception as exc:
                        out["warnings"].append(f"part_glb_export_failed:{part_id}:{exc}")

        if "step" in normalized:
            step_path = os.path.join(exports_dir, "assembly.step")
            if first_step:
                shutil.copy2(first_step, step_path)
                out["exports"]["step"] = step_path
                if len(parts) > 1:
                    out["warnings"].append("step_export_uses_first_part_fallback")
            else:
                out["warnings"].append("step_export_skipped_no_step_source")

        if "manifest" in normalized:
            manifest_path = os.path.join(exports_dir, "manifest.json")
            manifest = {
                "session_id": scene.get("session_id", ""),
                "project": scene.get("project", ""),
                "version": scene.get("version", 1),
                "parts": [
                    {
                        "part_id": p.get("part_id"),
                        "name": p.get("name"),
                        "role": p.get("role"),
                        "material": p.get("material"),
                        "appearance": p.get("appearance", {}),
                        "artifacts": p.get("artifacts", {}),
                        "transform": p.get("transform", {}),
                        "part_glb": part_glbs.get(str(p.get("part_id", "") or "")),
                    }
                    for p in parts
                ],
                "exports": out["exports"],
                "validation": scene.get("validation", {}),
            }
            with open(manifest_path, "w", encoding="utf-8") as handle:
                json.dump(manifest, handle, indent=2)
            out["exports"]["manifest"] = manifest_path
        if part_glbs:
            out["part_glbs"] = part_glbs

        return out
