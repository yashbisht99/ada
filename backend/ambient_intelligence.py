"""
Ambient Intelligence Layer — Always-on background awareness for ADA.
Monitors file-system events, system performance, code repo health,
screen changes, and environment signals. Triggers proactive notifications.
"""
import asyncio
import os
import time
import hashlib
import subprocess
import json
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class AmbientAlert:
    id: str
    category: str  # "file", "system", "code", "environment", "api"
    severity: str  # "info", "warning", "critical"
    title: str
    message: str
    timestamp: float
    acknowledged: bool = False
    auto_action: str = ""  # suggested automatic action


class AmbientIntelligence:
    """
    Always-on background awareness layer. Watches over the digital
    and physical environment and raises proactive alerts.
    """

    def __init__(
        self,
        notify_fn: Optional[Callable] = None,
        context_engine: Optional[Any] = None,
        system_monitor: Optional[Any] = None,
    ):
        self._notify = notify_fn
        self._context_engine = context_engine
        self._system_monitor = system_monitor

        self.alerts: List[AmbientAlert] = []
        self._running = False
        self._tick_interval = 30  # seconds

        # File monitoring
        self._watched_dirs: Dict[str, Dict[str, float]] = {}  # path -> {file: mtime}
        self._file_change_callbacks: List[Callable] = []

        # System thresholds
        self._cpu_threshold = 85.0
        self._memory_threshold = 90.0
        self._disk_threshold = 90.0
        self._cpu_high_since: float = 0.0
        self._cpu_alert_cooldown = 300  # 5 min

        # Code repo tracking
        self._repo_paths: List[str] = []
        self._uncommitted_alert_hours = 4
        self._repo_cache: Dict[str, Dict] = {}

        # Screen stare tracking
        self._screen_unchanged_since: float = 0.0
        self._screen_hash: str = ""
        self._stare_alert_minutes = 15

        # Build failure tracking
        self._last_build_status: Dict[str, bool] = {}
        self._build_fail_since: Dict[str, float] = {}

        print("[AmbientIntelligence] Initialized.")

    # ---- public api ----

    def watch_directory(self, path: str):
        """Add a directory to file monitoring."""
        if os.path.isdir(path):
            self._watched_dirs[path] = self._snapshot_dir(path)
            print(f"[Ambient] Watching directory: {path}")

    def watch_repo(self, repo_path: str):
        """Monitor a git repo for uncommitted changes."""
        if os.path.isdir(os.path.join(repo_path, ".git")):
            self._repo_paths.append(repo_path)
            print(f"[Ambient] Watching repo: {repo_path}")

    def get_alerts(self, unacknowledged_only: bool = True) -> List[Dict]:
        alerts = self.alerts
        if unacknowledged_only:
            alerts = [a for a in alerts if not a.acknowledged]
        return [
            {
                "id": a.id,
                "category": a.category,
                "severity": a.severity,
                "title": a.title,
                "message": a.message,
                "timestamp": a.timestamp,
                "auto_action": a.auto_action,
            }
            for a in alerts[-20:]
        ]

    def acknowledge_alert(self, alert_id: str):
        for a in self.alerts:
            if a.id == alert_id:
                a.acknowledged = True
                return True
        return False

    # ---- background loop ----

    async def run(self):
        self._running = True
        print("[AmbientIntelligence] Background monitoring started.")
        while self._running:
            try:
                await self._check_file_changes()
                await self._check_system_health()
                await self._check_repo_health()
                await self._check_screen_stare()
            except Exception as exc:
                print(f"[Ambient] Tick error: {exc}")
            await asyncio.sleep(self._tick_interval)

    def stop(self):
        self._running = False

    # ---- monitors ----

    async def _check_file_changes(self):
        """Detect file modifications in watched directories."""
        for dir_path, old_snapshot in list(self._watched_dirs.items()):
            if not os.path.isdir(dir_path):
                continue
            new_snapshot = self._snapshot_dir(dir_path)
            # find changes
            added = set(new_snapshot.keys()) - set(old_snapshot.keys())
            removed = set(old_snapshot.keys()) - set(new_snapshot.keys())
            modified = {
                f for f in set(old_snapshot.keys()) & set(new_snapshot.keys())
                if old_snapshot[f] != new_snapshot[f]
            }
            self._watched_dirs[dir_path] = new_snapshot

            if added:
                await self._raise_alert(
                    "file", "info",
                    f"{len(added)} new files in {os.path.basename(dir_path)}",
                    f"New: {', '.join(list(added)[:5])}",
                )
            if removed:
                await self._raise_alert(
                    "file", "warning",
                    f"{len(removed)} files deleted from {os.path.basename(dir_path)}",
                    f"Deleted: {', '.join(list(removed)[:5])}",
                )
            if len(modified) > 10:
                await self._raise_alert(
                    "file", "info",
                    f"{len(modified)} files modified in {os.path.basename(dir_path)}",
                    "Large batch of file changes detected.",
                )

    async def _check_system_health(self):
        """Monitor CPU, memory, disk usage."""
        stats = {}
        if self._system_monitor:
            try:
                stats = self._system_monitor.get_stats()
            except Exception:
                pass

        if not stats:
            # Fallback: use psutil-like approach
            try:
                import psutil
                stats = {
                    "cpu": {"percent": psutil.cpu_percent(interval=0.1)},
                    "memory": {"percent": psutil.virtual_memory().percent},
                    "disk": {"percent": psutil.disk_usage("/").percent},
                }
            except ImportError:
                return

        cpu = stats.get("cpu", {}).get("percent", 0)
        mem = stats.get("memory", {}).get("percent", 0)
        disk = stats.get("disk", {}).get("percent", 0)
        now = time.time()

        if cpu > self._cpu_threshold:
            if self._cpu_high_since == 0:
                self._cpu_high_since = now
            elif now - self._cpu_high_since > 120:  # sustained 2+ min
                await self._raise_alert(
                    "system", "warning",
                    f"CPU at {cpu:.0f}% for {int((now - self._cpu_high_since) / 60)} minutes",
                    "Consider closing heavy applications or terminating runaway processes.",
                    cooldown=self._cpu_alert_cooldown,
                )
        else:
            self._cpu_high_since = 0

        if mem > self._memory_threshold:
            await self._raise_alert(
                "system", "critical",
                f"Memory usage critical: {mem:.0f}%",
                "System may become unresponsive. Consider closing applications.",
                cooldown=600,
            )

        if disk > self._disk_threshold:
            await self._raise_alert(
                "system", "warning",
                f"Disk usage high: {disk:.0f}%",
                "Shall I identify large files for cleanup?",
                auto_action="suggest_cleanup",
                cooldown=3600,
            )

    async def _check_repo_health(self):
        """Monitor git repos for stale uncommitted changes."""
        for repo_path in self._repo_paths:
            try:
                result = subprocess.run(
                    ["git", "status", "--porcelain"],
                    cwd=repo_path, capture_output=True, text=True, timeout=10,
                )
                if result.returncode != 0:
                    continue

                changes = result.stdout.strip().splitlines()
                if not changes:
                    self._repo_cache.pop(repo_path, None)
                    continue

                # track when changes first appeared
                if repo_path not in self._repo_cache:
                    self._repo_cache[repo_path] = {
                        "first_seen": time.time(),
                        "count": len(changes),
                    }
                cache = self._repo_cache[repo_path]
                age_hours = (time.time() - cache["first_seen"]) / 3600

                if age_hours > self._uncommitted_alert_hours:
                    repo_name = os.path.basename(repo_path)
                    await self._raise_alert(
                        "code", "warning",
                        f"{len(changes)} uncommitted changes in {repo_name} ({age_hours:.0f}h old)",
                        "Consider committing your progress to avoid data loss.",
                        cooldown=7200,
                    )

                # check for build failures
                await self._check_build_status(repo_path)

            except Exception:
                continue

    async def _check_build_status(self, repo_path: str):
        """Check if the project builds successfully."""
        pkg_json = os.path.join(repo_path, "package.json")
        pyproject = os.path.join(repo_path, "pyproject.toml")
        requirements = os.path.join(repo_path, "requirements.txt")

        # detect project type and run appropriate check
        if os.path.exists(pkg_json):
            check_cmd = ["npm", "run", "build", "--", "--no-emit"]
        elif os.path.exists(pyproject) or os.path.exists(requirements):
            check_cmd = ["python", "-m", "py_compile"]
        else:
            return

        # For now just track — don't actually run builds in background
        # This would need user opt-in
        pass

    async def _check_screen_stare(self):
        """Detect if user has been staring at the same screen for too long."""
        if not self._context_engine:
            return
        try:
            snapshot = self._context_engine.snapshot()
            screen_content = str(snapshot.get("workspace", {}).get("active_file", ""))
            idle = snapshot.get("workspace", {}).get("idle_duration", 0)

            content_hash = hashlib.md5(screen_content.encode()).hexdigest()
            now = time.time()

            if content_hash == self._screen_hash and self._screen_unchanged_since > 0:
                stare_minutes = (now - self._screen_unchanged_since) / 60
                if stare_minutes > self._stare_alert_minutes and idle < 60:
                    await self._raise_alert(
                        "environment", "info",
                        f"Same screen for {stare_minutes:.0f} minutes",
                        "Would you like me to help with what you're working on?",
                        auto_action="offer_help",
                        cooldown=900,
                    )
            else:
                self._screen_hash = content_hash
                self._screen_unchanged_since = now

        except Exception:
            pass

    # ---- alert management ----

    async def _raise_alert(
        self,
        category: str,
        severity: str,
        title: str,
        message: str,
        auto_action: str = "",
        cooldown: float = 300,
    ):
        """Create and optionally push an alert."""
        # cooldown check
        for existing in reversed(self.alerts):
            if (
                existing.title == title
                and time.time() - existing.timestamp < cooldown
            ):
                return  # skip duplicate

        alert = AmbientAlert(
            id=f"alert_{int(time.time())}_{len(self.alerts)}",
            category=category,
            severity=severity,
            title=title,
            message=message,
            timestamp=time.time(),
            auto_action=auto_action,
        )
        self.alerts.append(alert)

        # keep bounded
        if len(self.alerts) > 100:
            self.alerts = self.alerts[-80:]

        print(f"[Ambient] [{severity.upper()}] {title}: {message}")

        # push to ADA
        if self._notify and severity in ("warning", "critical"):
            try:
                await self._notify(
                    f"System: [Ambient Alert — {severity.upper()}] {title}. {message}"
                )
            except Exception:
                pass

    def _snapshot_dir(self, path: str) -> Dict[str, float]:
        """Create a file -> mtime snapshot of a directory."""
        snap = {}
        skip = {".git", "node_modules", "__pycache__", "venv", ".next", "dist", "build"}
        try:
            for root, dirs, files in os.walk(path):
                dirs[:] = [d for d in dirs if d not in skip]
                for f in files:
                    fp = os.path.join(root, f)
                    try:
                        snap[os.path.relpath(fp, path)] = os.path.getmtime(fp)
                    except Exception:
                        continue
                # limit depth
                depth = root.replace(path, "").count(os.sep)
                if depth > 3:
                    dirs.clear()
        except Exception:
            pass
        return snap

    def get_stats(self) -> Dict[str, Any]:
        return {
            "is_running": self._running,
            "watched_dirs": len(self._watched_dirs),
            "watched_repos": len(self._repo_paths),
            "total_alerts": len(self.alerts),
            "unacknowledged": sum(1 for a in self.alerts if not a.acknowledged),
        }
