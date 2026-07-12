"""
Parametric CAD Checkpoint Version Manager — Part of the ADA V2 Premium Essentials.
Provides Git-like versioning and rollback capabilities for active CAD parameters.
"""
import os
import json
import time
import hashlib
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict


@dataclass
class CadCheckpoint:
    version_id: str
    timestamp: float
    parameters: Dict[str, Any]
    tag: str = ""
    checksum: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CheckpointManager:
    """Manages parametric CAD states, allowing historical rollbacks and parameter diffing."""

    def __init__(self, persistence_path: str = "data/cad_checkpoints.json"):
        self.persistence_path = persistence_path
        self.checkpoints: List[CadCheckpoint] = []
        self._load_checkpoints()

    def _calculate_checksum(self, params: Dict[str, Any]) -> str:
        """Generates an MD5 checksum of the parameters dictionary to verify state uniqueness."""
        serialized = json.dumps(params, sort_keys=True)
        return hashlib.md5(serialized.encode("utf-8")).hexdigest()

    def create_checkpoint(self, params: Dict[str, Any], tag: str = "") -> CadCheckpoint:
        """Lightweight snapshot of the parameters, returning the created checkpoint."""
        checksum = self._calculate_checksum(params)
        timestamp = time.time()
        
        # Avoid creating duplicate back-to-back identical checkpoints
        if self.checkpoints and self.checkpoints[-1].checksum == checksum:
            if tag and not self.checkpoints[-1].tag:
                self.checkpoints[-1].tag = tag
                self._save_checkpoints()
            return self.checkpoints[-1]

        version_id = f"v_{int(timestamp)}_{checksum[:6]}"
        checkpoint = CadCheckpoint(
            version_id=version_id,
            timestamp=timestamp,
            parameters=params,
            tag=tag or f"Auto Checkpoint {len(self.checkpoints) + 1}",
            checksum=checksum
        )
        self.checkpoints.append(checkpoint)
        self._save_checkpoints()
        print(f"[CheckpointManager] Created version: {version_id} with checksum: {checksum}")
        return checkpoint

    def rollback_to(self, version_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves and returns the parameters matching the requested version_id."""
        for cp in self.checkpoints:
            if cp.version_id == version_id:
                print(f"[CheckpointManager] Rolling back to: {version_id}")
                return cp.parameters
        print(f"[CheckpointManager] Rollback version not found: {version_id}")
        return None

    def get_history(self) -> List[Dict[str, Any]]:
        """Returns the serialized history of all parameter checkpoints."""
        return [cp.to_dict() for cp in self.checkpoints]

    def clear_history(self) -> None:
        """Clears all checkpoint history."""
        self.checkpoints = []
        if os.path.exists(self.persistence_path):
            try:
                os.remove(self.persistence_path)
            except Exception as e:
                print(f"[CheckpointManager] Error removing checkpoints file: {e}")

    def _load_checkpoints(self) -> None:
        """Loads checkpoints from disk."""
        if not os.path.exists(self.persistence_path):
            return
        try:
            with open(self.persistence_path, "r") as f:
                raw_data = json.load(f)
            self.checkpoints = [
                CadCheckpoint(
                    version_id=item["version_id"],
                    timestamp=item["timestamp"],
                    parameters=item["parameters"],
                    tag=item["tag"],
                    checksum=item["checksum"]
                )
                for item in raw_data
            ]
            print(f"[CheckpointManager] Loaded {len(self.checkpoints)} checkpoints from {self.persistence_path}")
        except Exception as e:
            print(f"[CheckpointManager] Failed to load checkpoints: {e}")

    def _save_checkpoints(self) -> None:
        """Saves checkpoints to disk, ensuring directory existence."""
        parent_dir = os.path.dirname(self.persistence_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        try:
            with open(self.persistence_path, "w") as f:
                json.dump([cp.to_dict() for cp in self.checkpoints], f, indent=2)
        except Exception as e:
            print(f"[CheckpointManager] Failed to write checkpoints: {e}")
