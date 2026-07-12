"""
Proactive Assistant Module
Enables Ada to initiate conversations, provide suggestions, and send reminders
"""
import asyncio
import time
from typing import Optional, Callable, List, Dict
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import os

@dataclass
class ProactiveTrigger:
    """Defines when and how Ada should proactively engage"""
    trigger_id: str
    trigger_type: str  # "time", "context", "pattern", "reminder"
    condition: dict
    message_template: str
    priority: int = 5  # 1-10, higher = more important
    cooldown: float = 3600  # Seconds before triggering again
    last_triggered: float = 0
    enabled: bool = True

@dataclass
class Reminder:
    """User reminder"""
    reminder_id: str
    message: str
    trigger_time: float
    recurring: bool = False
    interval: Optional[float] = None  # Seconds for recurring
    created_at: float = 0
    triggered_count: int = 0

class ProactiveAssistant:
    """
    Manages proactive behaviors for Ada.
    Monitors context and triggers appropriate interventions.
    """
    
    def __init__(self, on_proactive_message: Optional[Callable] = None):
        self.on_proactive_message = on_proactive_message
        
        # Triggers
        self.triggers: Dict[str, ProactiveTrigger] = {}
        self.reminders: Dict[str, Reminder] = {}
        
        # Context tracking
        self.last_interaction_time = time.time()
        self.idle_threshold = 90  # 1.5 minutes (down from 30)
        self.context_history = []
        
        # State
        self.is_running = False
        self.check_interval = 60  # Check every minute
        
        # Load saved reminders
        self._load_reminders()
        
        # Register default triggers
        self._register_default_triggers()
    
    def _register_default_triggers(self):
        """Register built-in proactive triggers"""
        
        # Short idle check - Jarvis witty observation
        self.register_trigger(ProactiveTrigger(
            trigger_id="short_idle_check",
            trigger_type="time",
            condition={"idle_minutes": 1.5},
            message_template="System: The user has been quiet for a moment. Feel free to make a brief, witty observation, ask if they need assistance, or bring up something relevant to the current project context like Jarvis would.",
            priority=8,
            cooldown=300  # 5 minutes
        ))
        
        # Deep idle check - suggest tasks after inactivity
        self.register_trigger(ProactiveTrigger(
            trigger_id="idle_check",
            trigger_type="time",
            condition={"idle_minutes": 30},
            message_template="System: The user has been gone for 30 minutes. Welcome them back or make a sarcastic remark about the silence.",
            priority=3,
            cooldown=7200  # 2 hours
        ))
        
        # Project reminder - remind about open projects
        self.register_trigger(ProactiveTrigger(
            trigger_id="project_reminder",
            trigger_type="context",
            condition={"has_open_project": True, "idle_minutes": 60},
            message_template="You have an open project. Would you like to continue working on it?",
            priority=5,
            cooldown=14400  # 4 hours
        ))
        
        # Learning opportunity - suggest features
        self.register_trigger(ProactiveTrigger(
            trigger_id="feature_suggestion",
            trigger_type="pattern",
            condition={"repeated_manual_action": True},
            message_template="I noticed you're doing this manually. Would you like me to automate it?",
            priority=6,
            cooldown=86400  # 24 hours
        ))
        
        # Health check - remind to take breaks
        self.register_trigger(ProactiveTrigger(
            trigger_id="break_reminder",
            trigger_type="time",
            condition={"continuous_work_minutes": 120},
            message_template="You've been working for 2 hours. Consider taking a short break!",
            priority=4,
            cooldown=7200  # 2 hours
        ))
    
    def register_trigger(self, trigger: ProactiveTrigger):
        """Register a new proactive trigger"""
        self.triggers[trigger.trigger_id] = trigger
        print(f"[Proactive] Registered trigger: {trigger.trigger_id}")
    
    def add_reminder(self, message: str, trigger_time: datetime, recurring: bool = False, interval_minutes: Optional[int] = None) -> str:
        """Add a user reminder"""
        reminder_id = f"reminder_{int(time.time())}_{len(self.reminders)}"
        
        reminder = Reminder(
            reminder_id=reminder_id,
            message=message,
            trigger_time=trigger_time.timestamp(),
            recurring=recurring,
            interval=interval_minutes * 60 if interval_minutes else None,
            created_at=time.time()
        )
        
        self.reminders[reminder_id] = reminder
        self._save_reminders()
        
        print(f"[Proactive] Added reminder: {reminder_id} at {trigger_time}")
        return reminder_id
    
    def remove_reminder(self, reminder_id: str) -> bool:
        """Remove a reminder"""
        if reminder_id in self.reminders:
            del self.reminders[reminder_id]
            self._save_reminders()
            print(f"[Proactive] Removed reminder: {reminder_id}")
            return True
        return False
    
    def update_interaction(self):
        """Update last interaction time"""
        self.last_interaction_time = time.time()
    
    def add_context(self, context_type: str, data: dict):
        """Add context for pattern detection"""
        self.context_history.append({
            'type': context_type,
            'data': data,
            'timestamp': time.time()
        })
        
        # Keep only last 100 context items
        if len(self.context_history) > 100:
            self.context_history = self.context_history[-100:]
    
    async def check_triggers(self, current_context: dict) -> Optional[str]:
        """
        Check all triggers and return a proactive message if any trigger fires.
        Returns: message to send, or None
        """
        now = time.time()
        idle_time = now - self.last_interaction_time
        
        # Check reminders first (highest priority)
        reminder_message = self._check_reminders(now)
        if reminder_message:
            return reminder_message
        
        # Check triggers by priority
        sorted_triggers = sorted(
            self.triggers.values(),
            key=lambda t: t.priority,
            reverse=True
        )
        
        for trigger in sorted_triggers:
            if not trigger.enabled:
                continue
            
            # Check cooldown
            if now - trigger.last_triggered < trigger.cooldown:
                continue
            
            # Check condition based on trigger type
            should_trigger = False
            
            if trigger.trigger_type == "time":
                if "idle_minutes" in trigger.condition:
                    required_idle = trigger.condition["idle_minutes"] * 60
                    should_trigger = idle_time >= required_idle
                
                if "continuous_work_minutes" in trigger.condition:
                    # Check if user has been active continuously
                    work_time = trigger.condition["continuous_work_minutes"] * 60
                    # This would need more sophisticated tracking
                    should_trigger = False  # Placeholder
            
            elif trigger.trigger_type == "context":
                # Check context conditions
                if "idle_minutes" in trigger.condition:
                    required_idle = trigger.condition["idle_minutes"] * 60
                    if idle_time < required_idle:
                        continue
                
                if "has_open_project" in trigger.condition:
                    has_project = current_context.get("has_open_project", False)
                    if trigger.condition["has_open_project"] != has_project:
                        continue
                
                should_trigger = True
            
            elif trigger.trigger_type == "pattern":
                # Pattern detection (simplified)
                should_trigger = self._detect_pattern(trigger.condition)
            
            if should_trigger:
                trigger.last_triggered = now
                print(f"[Proactive] Trigger fired: {trigger.trigger_id}")
                return trigger.message_template
        
        return None
    
    def _check_reminders(self, now: float) -> Optional[str]:
        """Check if any reminders should fire"""
        for reminder_id, reminder in list(self.reminders.items()):
            if now >= reminder.trigger_time:
                message = f"Reminder: {reminder.message}"
                
                reminder.triggered_count += 1
                
                if reminder.recurring and reminder.interval:
                    # Schedule next occurrence
                    reminder.trigger_time = now + reminder.interval
                    self._save_reminders()
                else:
                    # Remove one-time reminder
                    del self.reminders[reminder_id]
                    self._save_reminders()
                
                print(f"[Proactive] Reminder fired: {reminder_id}")
                return message
        
        return None
    
    def _detect_pattern(self, condition: dict) -> bool:
        """Detect patterns in context history"""
        # Simplified pattern detection
        # In a real implementation, this would use ML or rule-based pattern matching
        
        if "repeated_manual_action" in condition:
            # Check if user has done the same action multiple times
            recent_actions = [c for c in self.context_history[-20:] if c['type'] == 'action']
            
            if len(recent_actions) >= 3:
                # Check for repeated actions
                action_types = [a['data'].get('action_type') for a in recent_actions]
                # Simple check: if same action appears 3+ times
                from collections import Counter
                counts = Counter(action_types)
                if any(count >= 3 for count in counts.values()):
                    return True
        
        return False
    
    async def run(self, get_context: Callable):
        """
        Main loop for proactive assistant.
        get_context: async function that returns current context dict
        """
        self.is_running = True
        print("[Proactive] Assistant started")
        
        while self.is_running:
            try:
                # Get current context
                context = await get_context()
                
                # Check triggers
                message = await self.check_triggers(context)
                
                if message and self.on_proactive_message:
                    # Send proactive message
                    await self.on_proactive_message(message)
                
                # Wait before next check
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                print(f"[Proactive] Error in main loop: {e}")
                await asyncio.sleep(self.check_interval)
    
    def stop(self):
        """Stop the proactive assistant"""
        self.is_running = False
        print("[Proactive] Assistant stopped")
    
    def _save_reminders(self):
        """Save reminders to disk"""
        try:
            reminders_data = {
                rid: {
                    'message': r.message,
                    'trigger_time': r.trigger_time,
                    'recurring': r.recurring,
                    'interval': r.interval,
                    'created_at': r.created_at,
                    'triggered_count': r.triggered_count
                }
                for rid, r in self.reminders.items()
            }
            
            os.makedirs('data', exist_ok=True)
            with open('data/reminders.json', 'w') as f:
                json.dump(reminders_data, f, indent=2)
                
        except Exception as e:
            print(f"[Proactive] Failed to save reminders: {e}")
    
    def _load_reminders(self):
        """Load reminders from disk"""
        try:
            if os.path.exists('data/reminders.json'):
                with open('data/reminders.json', 'r') as f:
                    reminders_data = json.load(f)
                
                for rid, data in reminders_data.items():
                    self.reminders[rid] = Reminder(
                        reminder_id=rid,
                        message=data['message'],
                        trigger_time=data['trigger_time'],
                        recurring=data['recurring'],
                        interval=data.get('interval'),
                        created_at=data.get('created_at', 0),
                        triggered_count=data.get('triggered_count', 0)
                    )
                
                print(f"[Proactive] Loaded {len(self.reminders)} reminders")
                
        except Exception as e:
            print(f"[Proactive] Failed to load reminders: {e}")
    
    def get_stats(self) -> dict:
        """Get proactive assistant statistics"""
        return {
            'is_running': self.is_running,
            'triggers_count': len(self.triggers),
            'reminders_count': len(self.reminders),
            'idle_time': time.time() - self.last_interaction_time,
            'context_history_size': len(self.context_history)
        }
