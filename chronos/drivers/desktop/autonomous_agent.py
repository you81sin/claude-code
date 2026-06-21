# -*- coding: utf-8 -*-
"""
Desktop Autonomous Agent for desktpomate
Monitor PC screen and autonomously decide next actions
"""

import time
import json
import subprocess
from pathlib import Path
from typing import Optional, Dict, List
import threading


class DesktopMonitor:
    """Monitor screen state and application context"""

    def __init__(self):
        self.last_screenshot = None
        self.last_action = None
        self.action_history = []
        self.screen_state = {}

    def take_screenshot(self, save_path: str = "temp_screen.png") -> bool:
        """Capture current screen"""
        try:
            # PowerShell で screenshot を取得
            ps_cmd = f"""
            Add-Type -AssemblyName System.Windows.Forms
            [System.Windows.Forms.Screen]::PrimaryScreen | Format-List
            $screen = [System.Windows.Forms.Screen]::PrimaryScreen
            $bitmap = New-Object System.Drawing.Bitmap($screen.Bounds.Width, $screen.Bounds.Height)
            $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
            $graphics.CopyFromScreen($screen.Bounds.Location, [System.Drawing.Point]::Empty, $screen.Bounds.Size)
            $bitmap.Save('{save_path}')
            """

            result = subprocess.run(
                ["powershell", "-Command", ps_cmd],
                capture_output=True,
                timeout=5
            )

            if result.returncode == 0 and Path(save_path).exists():
                self.last_screenshot = save_path
                return True

            return False

        except Exception as e:
            print(f"[MONITOR] Screenshot error: {e}")
            return False

    def analyze_screen_simple(self) -> Dict:
        """Simple screen state analysis (text-based)"""
        state = {
            "timestamp": time.time(),
            "active_processes": self._get_active_windows(),
            "screen_description": "Desktop monitoring active"
        }

        return state

    def _get_active_windows(self) -> List[str]:
        """Get list of active windows"""
        try:
            ps_cmd = """
            [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
            Get-Process | Where-Object {$_.MainWindowTitle -ne ''} |
            Select-Object -ExpandProperty MainWindowTitle | Select-Object -First 5
            """

            result = subprocess.run(
                ["powershell", "-Command", ps_cmd],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore',
                timeout=5
            )

            if result.returncode == 0:
                windows = [w.strip() for w in result.stdout.strip().split('\n') if w.strip()]
                return windows

            return []

        except Exception as e:
            print(f"[MONITOR] Error getting windows: {e}")
            return []


class AutonomousDecisionEngine:
    """Decide what to do based on screen state"""

    def __init__(self, char_name: str = "desktpomate"):
        self.char_name = char_name
        self.identity = self._load_identity()
        self.action_queue = []
        self.last_decision_time = 0
        self.decision_interval = 10  # 10 seconds

    def _load_identity(self) -> Dict:
        """Load character identity"""
        path = Path(f"apps/{self.char_name}/data/identity.json")
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)

        return {
            "name": self.char_name,
            "personality": {},
            "capabilities": {}
        }

    def analyze_and_decide(self, screen_state: Dict) -> Optional[str]:
        """
        Analyze screen state and decide next action
        Returns action description or None
        """

        # Rate limiting
        now = time.time()
        if now - self.last_decision_time < self.decision_interval:
            return None

        self.last_decision_time = now

        # Get active windows
        active = screen_state.get("active_processes", [])

        # Simple decision logic
        suggestions = []

        # Detect various scenarios
        for app in active:
            if not app:
                continue

            app_lower = app.lower()

            # Code editor: suggest test/format
            if any(x in app_lower for x in ["vscode", "code", "pycharm", "jetbrains"]):
                suggestions.append("code_check")

            # File explorer: suggest organize
            elif any(x in app_lower for x in ["explorer", "file"]):
                suggestions.append("file_organize")

            # Browser: suggest research
            elif any(x in app_lower for x in ["chrome", "edge", "firefox"]):
                suggestions.append("research_summary")

            # Word processor: suggest format
            elif any(x in app_lower for x in ["word", "document"]):
                suggestions.append("document_format")

        if suggestions:
            action = suggestions[0]
            print(f"[DECISION] Suggested action: {action}")
            return action

        # Default: idle suggestion
        print(f"[DECISION] No specific action detected. Desktop idle.")
        return None

    def execute_action(self, action: str) -> bool:
        """Execute decided action"""

        print(f"[ACTION] Executing: {action}")

        try:
            if action == "code_check":
                print("[ACTION] Suggestion: Run tests in your code editor")
                return True

            elif action == "file_organize":
                print("[ACTION] Suggestion: Organize your desktop files")
                return True

            elif action == "research_summary":
                print("[ACTION] Suggestion: Summary current research topic")
                return True

            elif action == "document_format":
                print("[ACTION] Suggestion: Check document formatting")
                return True

        except Exception as e:
            print(f"[ACTION] Error: {e}")
            return False

        return False


class DesktopAutonomousAgent:
    """Main agent: monitor + decide + act"""

    def __init__(self, char_name: str = "desktpomate"):
        self.char_name = char_name
        self.monitor = DesktopMonitor()
        self.decision_engine = AutonomousDecisionEngine(char_name)
        self.running = False
        self.monitor_thread = None
        self.monitoring_interval = 5  # Check every 5 seconds

    def start(self):
        """Start autonomous monitoring and decision loop"""

        print(f"\n[{self.char_name.upper()}] Starting desktop autonomous agent...")
        print(f"[{self.char_name.upper()}] Monitoring interval: {self.monitoring_interval}s")
        print(f"[{self.char_name.upper()}] Decision interval: {self.decision_engine.decision_interval}s\n")

        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()

    def stop(self):
        """Stop monitoring"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)

        print(f"\n[{self.char_name.upper()}] Autonomous agent stopped.")

    def _monitor_loop(self):
        """Main monitoring and decision loop"""

        while self.running:
            try:
                # Monitor screen
                screen_state = self.monitor.analyze_screen_simple()

                # Decide action
                action = self.decision_engine.analyze_and_decide(screen_state)

                # Execute action
                if action:
                    self.decision_engine.execute_action(action)

                time.sleep(self.monitoring_interval)

            except KeyboardInterrupt:
                break

            except Exception as e:
                print(f"[MONITOR] Loop error: {e}")
                time.sleep(5)


def main():
    print("=" * 60)
    print("[DESKTPOMATE] Desktop Autonomous Agent")
    print("=" * 60)

    agent = DesktopAutonomousAgent("desktpomate")
    agent.start()

    try:
        print("\n[INFO] Running... (Ctrl+C to stop)\n")

        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n[INFO] Shutting down...")
        agent.stop()


if __name__ == "__main__":
    main()
