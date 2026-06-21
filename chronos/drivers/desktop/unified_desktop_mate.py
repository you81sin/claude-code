# -*- coding: utf-8 -*-
"""
Unified Desktop Mate System
AI character appears on screen, understands user, performs actions
"""

import json
import subprocess
import time
from pathlib import Path
from typing import Optional, Dict
import threading


class UnifiedDesktopMate:
    """Single unified AI desktop mate across all devices"""

    def __init__(self, char_name: str = "desktpomate"):
        self.char_name = char_name
        self.identity = self._load_identity()
        self.running = False
        self.action_thread = None

    def _load_identity(self) -> Dict:
        """Load character identity"""
        path = Path(f"apps/{self.char_name}/data/identity.json")
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def display_avatar(self) -> bool:
        """Display avatar on screen (web viewer)"""
        try:
            # Start web server if not running
            print(f"[{self.char_name.upper()}] Starting display...")

            # Open viewer in browser
            viewer_url = f"http://localhost:8001/{self.char_name}_viewer.html"
            subprocess.Popen(["start", viewer_url], shell=True)

            print(f"[{self.char_name.upper()}] Avatar displayed")
            return True

        except Exception as e:
            print(f"[{self.char_name.upper()}] Display error: {e}")
            return False

    def understand_user_input(self, user_input: str) -> Dict:
        """
        Understand what user wants
        Parse intent and extract actions
        """

        print(f"\n[{self.char_name.upper()}] User: {user_input}")

        intent = {
            "raw": user_input,
            "intent": self._classify_intent(user_input),
            "actions": self._extract_actions(user_input),
            "urgency": self._assess_urgency(user_input)
        }

        return intent

    def _classify_intent(self, text: str) -> str:
        """Classify user intent"""
        text_lower = text.lower()

        intents = {
            "file_operation": ["ファイル", "file", "folder", "open", "save", "delete"],
            "code_execution": ["実行", "run", "test", "execute", "python", "script"],
            "web_search": ["検索", "search", "find", "look up", "google"],
            "system_control": ["開く", "open", "close", "start", "stop"],
            "information": ["教えて", "what", "how", "why", "explain"],
            "reminder": ["リマインド", "remind", "notification", "alert"],
        }

        for intent_type, keywords in intents.items():
            if any(kw in text_lower for kw in keywords):
                return intent_type

        return "chat"

    def _extract_actions(self, text: str) -> list:
        """Extract actionable items from user input"""
        actions = []

        # Pattern matching for common actions
        if "ファイル" in text or "file" in text.lower():
            actions.append("file_operation")

        if "実行" in text or "run" in text.lower():
            actions.append("execute_code")

        if "検索" in text or "search" in text.lower():
            actions.append("web_search")

        if "開く" in text or "open" in text.lower():
            actions.append("open_app")

        return actions

    def _assess_urgency(self, text: str) -> float:
        """Assess urgency level (0-1)"""
        urgent_keywords = ["今すぐ", "immediately", "urgent", "asap", "critical"]

        for kw in urgent_keywords:
            if kw in text:
                return 0.9

        return 0.5

    def perform_action(self, intent: Dict) -> bool:
        """Execute action based on intent"""

        print(f"[{self.char_name.upper()}] Intent: {intent['intent']}")
        print(f"[{self.char_name.upper()}] Actions: {intent['actions']}")

        for action in intent['actions']:
            if action == "file_operation":
                self._action_file_operation(intent['raw'])

            elif action == "execute_code":
                self._action_execute_code(intent['raw'])

            elif action == "web_search":
                self._action_web_search(intent['raw'])

            elif action == "open_app":
                self._action_open_app(intent['raw'])

        return True

    def _action_file_operation(self, intent: str):
        """Handle file operations"""
        print(f"[ACTION] Processing file operation...")

        # TODO: Implement actual file operations
        # For now, just suggestion
        if "open" in intent.lower():
            print(f"[SUGGESTION] Use Ctrl+O to open file")

        elif "save" in intent.lower():
            print(f"[SUGGESTION] Use Ctrl+S to save")

        elif "delete" in intent.lower():
            print(f"[WARNING] Are you sure? File deletion is permanent")

    def _action_execute_code(self, intent: str):
        """Handle code execution"""
        print(f"[ACTION] Executing code...")

        # Try to detect language
        if "python" in intent.lower():
            print(f"[SUGGESTION] Running Python script...")

        elif "bash" in intent.lower() or "shell" in intent.lower():
            print(f"[SUGGESTION] Running shell command...")

    def _action_web_search(self, intent: str):
        """Handle web search"""
        print(f"[ACTION] Searching web...")

        # Extract search term
        search_term = intent.replace("検索", "").replace("search", "").strip()

        if search_term:
            print(f"[SEARCH] Query: {search_term}")
            print(f"[SUGGESTION] Opening Google search...")

    def _action_open_app(self, intent: str):
        """Handle app opening"""
        print(f"[ACTION] Opening application...")

        apps = {
            "notepad": "notepad.exe",
            "calc": "calc.exe",
            "explorer": "explorer.exe",
            "chrome": "chrome.exe",
            "vscode": "code.exe"
        }

        for app_name, exe in apps.items():
            if app_name in intent.lower():
                print(f"[SUGGESTION] Opening {app_name}...")
                try:
                    subprocess.Popen(exe)
                    return
                except Exception as e:
                    print(f"[ERROR] Could not open {app_name}: {e}")
                    return

        print(f"[SUGGESTION] App not found in standard list")

    def respond_to_user(self, intent: Dict) -> str:
        """Generate response to user"""

        char_personality = self.identity.get('personality', {})
        helpfulness = char_personality.get('helpfulness', 0.8)

        if intent['intent'] == "chat":
            responses = [
                "何かお手伝いしましょうか？",
                "What can I do for you?",
                "お待たせしました！",
                "Always happy to help!",
            ]
            return responses[hash(intent['raw']) % len(responses)]

        elif intent['intent'] == "file_operation":
            return "ファイル操作了解。手伝いますよ。"

        elif intent['intent'] == "code_execution":
            return "コード実行しますね。少々お待ちください。"

        elif intent['intent'] == "web_search":
            return "検索開始。結果を探しています。"

        else:
            return "理解しました。処理中です。"

    def speak(self, text: str):
        """Output speech (via TTS)"""
        print(f"\n[{self.char_name.upper()}] Speaking: {text}\n")

        # TODO: Integrate with SBV2 TTS
        # subprocess.run([...sbv2_api...])

    def run_interaction_loop(self):
        """Main interaction loop"""

        print(f"\n{'='*60}")
        print(f"[{self.char_name.upper().replace('_', ' ')} Desktop Mate]")
        print(f"{'='*60}\n")

        print(f"[{self.char_name.upper()}] Ready to assist!")
        print(f"[INFO] Displaying avatar on screen...")

        # Display avatar
        self.display_avatar()

        print(f"[INFO] Type commands or questions. 'quit' to exit.\n")

        self.running = True

        while self.running:
            try:
                # Get user input
                user_input = input(f"\n> ").strip()

                if user_input.lower() in ["quit", "exit", "q"]:
                    print(f"\n[{self.char_name.upper()}] Goodbye!")
                    break

                if not user_input:
                    continue

                # Understand input
                intent = self.understand_user_input(user_input)

                # Perform action
                self.perform_action(intent)

                # Respond
                response = self.respond_to_user(intent)
                self.speak(response)

            except KeyboardInterrupt:
                print(f"\n[{self.char_name.upper()}] Interrupted. Goodbye!")
                break

            except Exception as e:
                print(f"[ERROR] {e}")


def main():
    agent = UnifiedDesktopMate("desktpomate")
    agent.run_interaction_loop()


if __name__ == "__main__":
    main()
