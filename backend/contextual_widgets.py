"""
Contextual Widgets — Smart floating widget system for spatial UI.
Generates context-aware widget configurations based on user activity,
cursor position, active application, and ongoing tasks.
Rate-limit safe: all local context analysis.
"""
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class Widget:
    """A contextual floating widget."""
    id: str
    widget_type: str  # "suggestion", "status", "shortcut", "info", "alert"
    title: str
    content: str
    position: str  # "near_cursor", "top_right", "bottom_right", "center"
    priority: int  # 1-10
    auto_dismiss_seconds: float  # 0 = persistent
    actions: List[Dict[str, str]]  # clickable actions
    context_trigger: str  # what triggered this widget
    created: float = field(default_factory=time.time)
    dismissed: bool = False


class ContextualWidgets:
    """
    Smart contextual widget generation:
    - Monitors active application context
    - Generates relevant suggestions, tips, shortcuts
    - Positions widgets near the area of activity
    - Manages widget lifecycle (show, dismiss, expire)
    - Learns which widgets the user finds useful

    Rate-limit safe — all local context processing.
    """

    def __init__(self, notify_fn: Optional[Callable] = None):
        self._notify = notify_fn
        self._active_widgets: Dict[str, Widget] = {}
        self._widget_history: List[Dict[str, Any]] = []
        self._usefulness_scores: Dict[str, float] = {}  # widget_type -> usefulness
        self._generation_count = 0
        print("[ContextualWidgets] Initialized smart widget system.")

    # ---- widget generation ----

    def generate_widgets(self, context: Dict[str, Any]) -> List[Widget]:
        """Generate contextual widgets based on current user context."""
        self._generation_count += 1
        self._expire_widgets()

        active_app = context.get("active_app", "")
        file_path = context.get("active_file", "")
        task_type = context.get("task_type", "")
        time_on_task = context.get("time_on_task_minutes", 0)
        errors_recent = context.get("recent_errors", 0)

        new_widgets = []

        # Code editor context
        if any(ext in file_path.lower() for ext in [".py", ".js", ".ts", ".cpp", ".java"]):
            new_widgets.extend(self._code_editor_widgets(file_path, context))

        # CAD context
        if any(kw in active_app.lower() for kw in ["cad", "3d", "blender", "freecad"]):
            new_widgets.extend(self._cad_widgets(context))

        # Long task detection
        if time_on_task > 45:
            new_widgets.append(Widget(
                id=f"break_{int(time.time())}",
                widget_type="info",
                title="⏱ Time Check",
                content=f"You've been working for {time_on_task} minutes. Consider a short break?",
                position="top_right",
                priority=3,
                auto_dismiss_seconds=30,
                actions=[{"label": "Dismiss", "action": "dismiss"}, {"label": "Set Timer", "action": "set_break_timer"}],
                context_trigger="long_session",
            ))

        # Error assistance
        if errors_recent > 2:
            new_widgets.append(Widget(
                id=f"error_help_{int(time.time())}",
                widget_type="suggestion",
                title="🔧 Error Pattern Detected",
                content="I've noticed repeated errors. Want me to analyze the pattern?",
                position="near_cursor",
                priority=7,
                auto_dismiss_seconds=20,
                actions=[{"label": "Analyze", "action": "analyze_errors"}, {"label": "Dismiss", "action": "dismiss"}],
                context_trigger="error_pattern",
            ))

        # Register new widgets
        for widget in new_widgets:
            self._active_widgets[widget.id] = widget

        return new_widgets

    def _code_editor_widgets(self, file_path: str, context: Dict[str, Any]) -> List[Widget]:
        """Generate widgets for code editing context."""
        widgets = []
        ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""

        if ext == "py":
            widgets.append(Widget(
                id=f"py_assist_{int(time.time())}",
                widget_type="shortcut",
                title="🐍 Python Assistant",
                content="Quick actions: Run file, Debug, Format, Type check",
                position="bottom_right",
                priority=4,
                auto_dismiss_seconds=0,
                actions=[
                    {"label": "▶ Run", "action": "run_python"},
                    {"label": "🐛 Debug", "action": "debug_python"},
                    {"label": "✨ Format", "action": "format_python"},
                ],
                context_trigger="python_file",
            ))

        cursor_line = context.get("cursor_line", 0)
        if cursor_line > 0 and context.get("function_at_cursor"):
            widgets.append(Widget(
                id=f"fn_info_{int(time.time())}",
                widget_type="info",
                title=f"📝 {context['function_at_cursor']}",
                content="Ask me about this function: optimize, test, document, or explain",
                position="near_cursor",
                priority=5,
                auto_dismiss_seconds=15,
                actions=[
                    {"label": "Explain", "action": "explain_function"},
                    {"label": "Test", "action": "generate_test"},
                ],
                context_trigger="function_context",
            ))

        return widgets

    def _cad_widgets(self, context: Dict[str, Any]) -> List[Widget]:
        """Generate widgets for CAD context."""
        return [Widget(
            id=f"cad_assist_{int(time.time())}",
            widget_type="shortcut",
            title="🔩 CAD Assistant",
            content="Quick: Generate part, Check tolerances, Export",
            position="bottom_right",
            priority=5,
            auto_dismiss_seconds=0,
            actions=[
                {"label": "🆕 Generate", "action": "generate_cad"},
                {"label": "📏 Tolerance", "action": "check_tolerances"},
                {"label": "📤 Export", "action": "export_cad"},
            ],
            context_trigger="cad_context",
        )]

    # ---- widget management ----

    def dismiss_widget(self, widget_id: str):
        """Dismiss a widget and record feedback."""
        if widget_id in self._active_widgets:
            widget = self._active_widgets[widget_id]
            widget.dismissed = True
            self._widget_history.append({
                "type": widget.widget_type, "trigger": widget.context_trigger,
                "action": "dismissed", "timestamp": time.time(),
            })
            del self._active_widgets[widget_id]

    def widget_action_taken(self, widget_id: str, action: str):
        """Record when user takes action on a widget (positive signal)."""
        if widget_id in self._active_widgets:
            widget = self._active_widgets[widget_id]
            # Boost usefulness score for this widget type
            key = f"{widget.widget_type}_{widget.context_trigger}"
            self._usefulness_scores[key] = min(1.0, self._usefulness_scores.get(key, 0.5) + 0.1)
            self._widget_history.append({
                "type": widget.widget_type, "trigger": widget.context_trigger,
                "action": action, "timestamp": time.time(),
            })

    def _expire_widgets(self):
        """Remove expired widgets."""
        now = time.time()
        to_remove = []
        for wid, widget in self._active_widgets.items():
            if widget.auto_dismiss_seconds > 0 and (now - widget.created) > widget.auto_dismiss_seconds:
                to_remove.append(wid)
        for wid in to_remove:
            del self._active_widgets[wid]

    def get_active_widgets(self) -> List[Dict[str, Any]]:
        """Get all currently active widgets."""
        self._expire_widgets()
        return [
            {"id": w.id, "type": w.widget_type, "title": w.title,
             "content": w.content, "position": w.position, "actions": w.actions}
            for w in sorted(self._active_widgets.values(), key=lambda x: x.priority, reverse=True)
        ]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "active_widgets": len(self._active_widgets),
            "total_generated": self._generation_count,
            "history_length": len(self._widget_history),
            "usefulness_scores": dict(sorted(
                self._usefulness_scores.items(), key=lambda x: x[1], reverse=True
            )[:5]),
        }
