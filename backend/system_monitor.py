import psutil
import time
import threading

class SystemMonitor:
    def __init__(self, thresholds=None):
        self.thresholds = thresholds or {
            "cpu_percent": 90.0,
            "memory_percent": 85.0,
            "disk_percent": 95.0
        }
        self.stats = {}
        self.last_check = 0
        self.running = False
        print("[SystemMonitor] Initialized.")

    def get_stats(self):
        """Returns current system metrics."""
        self.stats = {
            "cpu": {
                "percent": psutil.cpu_percent(interval=None),
                "count": psutil.cpu_count(),
                "freq": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None
            },
            "memory": psutil.virtual_memory()._asdict(),
            "disk": psutil.disk_usage('/')._asdict(),
            "battery": psutil.sensors_battery()._asdict() if psutil.sensors_battery() else None,
            "timestamp": time.time()
        }
        return self.stats

    def check_thresholds(self):
        """Returns a list of warnings if thresholds are exceeded."""
        stats = self.get_stats()
        warnings = []
        
        if stats["cpu"]["percent"] > self.thresholds["cpu_percent"]:
            warnings.append({
                "type": "high_cpu",
                "value": stats["cpu"]["percent"],
                "message": f"High CPU usage detected: {stats['cpu']['percent']}%"
            })
            
        if stats["memory"]["percent"] > self.thresholds["memory_percent"]:
            warnings.append({
                "type": "high_memory",
                "value": stats["memory"]["percent"],
                "message": f"Memory usage is critical: {stats['memory']['percent']}%"
            })
            
        if stats["disk"]["percent"] > self.thresholds["disk_percent"]:
            warnings.append({
                "type": "low_disk",
                "value": stats["disk"]["percent"],
                "message": f"Disk space is almost full: {stats['disk']['percent']}%"
            })
            
        return warnings

    def get_top_processes(self, limit=5, sort_by="cpu"):
        """Returns top N processes by CPU or Memory."""
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        # Sort
        if sort_by == "cpu":
            processes.sort(key=lambda x: x['cpu_percent'] or 0.0, reverse=True)
        else:
            processes.sort(key=lambda x: x['memory_percent'] or 0.0, reverse=True)
            
        # Slice explicitly to avoid potential lint confusion
        top_procs = processes[:int(limit)]
        return top_procs

    def kill_process(self, pid: int):
        """Terminates a process by PID."""
        try:
            proc = psutil.Process(pid)
            proc.terminate()
            return True, f"Process {pid} ({proc.name()}) terminated."
        except Exception as e:
            return False, f"Failed to kill process {pid}: {e}"

if __name__ == "__main__":
    monitor = SystemMonitor()
    while True:
        print(f"Stats: {monitor.get_stats()['cpu']['percent']}% CPU")
        warnings = monitor.check_thresholds()
        if warnings:
            print(f"WARNINGS: {warnings}")
        time.sleep(2)
