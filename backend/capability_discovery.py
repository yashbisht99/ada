"""
Capability Discovery Engine — ADA identifies what new capabilities would be most useful.
Analyzes user interaction patterns, failed requests, and knowledge gaps to propose
and prototype new capabilities autonomously.
Rate-limit safe: all local pattern analysis.
"""
import json
import os
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class CapabilityGap:
    """An identified gap in ADA's capabilities."""
    id: str
    description: str
    evidence: List[str]  # failed queries / user requests that exposed the gap
    frequency: int  # how many times this gap was encountered
    impact: float  # 0-1 estimated user impact
    domain: str
    proposed_solution: str
    status: str  # "identified", "proposed", "prototyping", "implemented", "rejected"
    created: float = field(default_factory=time.time)


@dataclass
class CapabilityProposal:
    """A proposed new capability."""
    name: str
    description: str
    gap_ids: List[str]  # which gaps this addresses
    implementation_sketch: str
    estimated_effort: str  # "trivial", "small", "medium", "large"
    estimated_impact: float  # 0-1
    priority_score: float
    status: str = "proposed"


class CapabilityDiscoveryEngine:
    """
    Autonomous capability discovery:
    - Analyzes failed/unsatisfying interactions for patterns
    - Identifies recurring user needs that aren't well served
    - Proposes new capabilities with implementation sketches
    - Ranks proposals by impact-to-effort ratio
    - Tracks capability lifecycle from gap to implementation

    Rate-limit safe — all local pattern analysis.
    """

    PERSIST_PATH = "data/capability_discovery.json"

    def __init__(self, notify_fn: Optional[Callable] = None):
        self._notify = notify_fn
        self._gaps: Dict[str, CapabilityGap] = {}
        self._proposals: List[CapabilityProposal] = []
        self._failed_queries: List[Dict[str, Any]] = []
        self._unsatisfied_patterns: Counter = Counter()
        self._discovery_count = 0
        self._load()
        print(f"[CapabilityDiscovery] Initialized with {len(self._gaps)} known gaps.")

    # ---- gap detection ----

    def record_failure(self, query: str, error_type: str, domain: str = "general"):
        """Record a failed or unsatisfying interaction."""
        self._failed_queries.append({
            "query": query[:200], "error": error_type, "domain": domain,
            "timestamp": time.time(),
        })
        if len(self._failed_queries) > 200:
            self._failed_queries = self._failed_queries[-150:]

        # Extract pattern
        pattern = self._extract_capability_pattern(query, error_type)
        if pattern:
            self._unsatisfied_patterns[pattern] += 1

    def record_user_wish(self, wish: str, domain: str = "general"):
        """Record when user explicitly asks for something ADA can't do."""
        import hashlib
        gap_id = hashlib.md5(wish[:50].encode()).hexdigest()[:8]

        if gap_id in self._gaps:
            self._gaps[gap_id].frequency += 1
            self._gaps[gap_id].evidence.append(wish[:100])
            if len(self._gaps[gap_id].evidence) > 10:
                self._gaps[gap_id].evidence = self._gaps[gap_id].evidence[-8:]
        else:
            self._gaps[gap_id] = CapabilityGap(
                id=gap_id, description=wish[:200],
                evidence=[wish[:100]], frequency=1,
                impact=0.5, domain=domain,
                proposed_solution="", status="identified",
            )
        self._save()

    def discover_gaps(self) -> List[CapabilityGap]:
        """Analyze failure patterns to discover capability gaps."""
        self._discovery_count += 1

        # Find frequent failure patterns
        for pattern, count in self._unsatisfied_patterns.most_common(10):
            if count >= 3:
                import hashlib
                gap_id = hashlib.md5(pattern.encode()).hexdigest()[:8]
                if gap_id not in self._gaps:
                    self._gaps[gap_id] = CapabilityGap(
                        id=gap_id,
                        description=f"Recurring failure pattern: {pattern}",
                        evidence=[q["query"][:100] for q in self._failed_queries if pattern.lower() in q["query"].lower()][:5],
                        frequency=count,
                        impact=min(1.0, count * 0.15),
                        domain=self._detect_domain(pattern),
                        proposed_solution=self._propose_solution(pattern),
                        status="identified",
                    )

        # Sort by impact * frequency
        gaps = sorted(
            self._gaps.values(),
            key=lambda g: g.impact * g.frequency,
            reverse=True,
        )
        self._save()
        return gaps[:10]

    # ---- capability proposals ----

    def generate_proposals(self) -> List[CapabilityProposal]:
        """Generate capability proposals from identified gaps."""
        gaps = self.discover_gaps()
        proposals = []

        for gap in gaps:
            if gap.status != "identified":
                continue

            effort = self._estimate_effort(gap)
            impact = gap.impact * min(1.0, gap.frequency / 5)
            priority = impact / max({"trivial": 0.5, "small": 1, "medium": 2, "large": 4}.get(effort, 2), 0.5)

            proposal = CapabilityProposal(
                name=f"Auto-{gap.id}: {gap.description[:50]}",
                description=gap.description,
                gap_ids=[gap.id],
                implementation_sketch=gap.proposed_solution or self._propose_solution(gap.description),
                estimated_effort=effort,
                estimated_impact=round(impact, 2),
                priority_score=round(priority, 2),
            )
            proposals.append(proposal)

        proposals.sort(key=lambda p: p.priority_score, reverse=True)
        self._proposals = proposals[:20]
        self._save()
        return self._proposals[:5]

    # ---- helpers ----

    def _extract_capability_pattern(self, query: str, error_type: str) -> Optional[str]:
        """Extract a capability pattern from a failed query."""
        q = query.lower()
        patterns = {
            "file_management": ["move file", "rename", "organize", "sort files", "copy"],
            "scheduling": ["schedule", "remind me", "calendar", "meeting", "alarm"],
            "data_analysis": ["analyze data", "chart", "graph", "statistics", "csv"],
            "communication": ["send email", "message", "notify", "slack", "discord"],
            "automation": ["automate", "every day", "recurring", "batch", "workflow"],
            "hardware": ["printer", "bluetooth", "usb", "speaker", "microphone"],
        }
        for pattern, keywords in patterns.items():
            if any(kw in q for kw in keywords):
                return pattern
        if error_type in {"tool_not_found", "capability_missing"}:
            return f"missing_tool_{query.split()[0].lower()}" if query.split() else None
        return None

    def _propose_solution(self, description: str) -> str:
        """Generate an implementation sketch for a capability gap."""
        d = description.lower()
        if any(w in d for w in ["file", "directory", "folder"]):
            return "Add file management tools (os.walk, shutil operations) with permission checks."
        if any(w in d for w in ["schedule", "remind", "alarm"]):
            return "Implement a local scheduler using APScheduler with persistent job store."
        if any(w in d for w in ["data", "chart", "graph", "csv"]):
            return "Add data analysis pipeline using pandas + matplotlib for visualization."
        if any(w in d for w in ["email", "message", "notify"]):
            return "Integrate notification system via local webhook or system notifications."
        if any(w in d for w in ["automate", "workflow", "batch"]):
            return "Build a task automation engine with cron-like scheduling and action chains."
        return "Requires further analysis to determine implementation approach."

    def _estimate_effort(self, gap: CapabilityGap) -> str:
        d = gap.description.lower()
        if any(w in d for w in ["simple", "add", "basic"]):
            return "small"
        if any(w in d for w in ["integrate", "system", "complex", "hardware"]):
            return "large"
        return "medium"

    def _detect_domain(self, text: str) -> str:
        t = text.lower()
        domains = {
            "engineering": ["cad", "design", "model", "gear"],
            "development": ["code", "debug", "api", "function"],
            "productivity": ["schedule", "organize", "automate"],
            "communication": ["email", "message", "notify"],
        }
        for domain, keywords in domains.items():
            if any(kw in t for kw in keywords):
                return domain
        return "general"

    # ---- persistence ----

    def _save(self):
        try:
            os.makedirs(os.path.dirname(self.PERSIST_PATH), exist_ok=True)
            data = {
                "gaps": {
                    gid: {"desc": g.description, "freq": g.frequency, "impact": g.impact,
                           "domain": g.domain, "solution": g.proposed_solution, "status": g.status}
                    for gid, g in self._gaps.items()
                },
                "patterns": dict(self._unsatisfied_patterns.most_common(50)),
            }
            with open(self.PERSIST_PATH, "w") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def _load(self):
        try:
            if not os.path.exists(self.PERSIST_PATH):
                return
            with open(self.PERSIST_PATH) as f:
                data = json.load(f)
            for gid, gd in data.get("gaps", {}).items():
                self._gaps[gid] = CapabilityGap(
                    id=gid, description=gd["desc"], evidence=[], frequency=gd.get("freq", 1),
                    impact=gd.get("impact", 0.5), domain=gd.get("domain", "general"),
                    proposed_solution=gd.get("solution", ""), status=gd.get("status", "identified"),
                )
            self._unsatisfied_patterns = Counter(data.get("patterns", {}))
        except Exception:
            pass

    def get_stats(self) -> Dict[str, Any]:
        return {
            "known_gaps": len(self._gaps),
            "proposals": len(self._proposals),
            "discovery_runs": self._discovery_count,
            "failure_patterns": len(self._unsatisfied_patterns),
            "top_gaps": [
                {"desc": g.description[:60], "freq": g.frequency, "impact": g.impact}
                for g in sorted(self._gaps.values(), key=lambda x: x.frequency, reverse=True)[:5]
            ],
        }
