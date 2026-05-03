# Context: [[nb:knowledge:adr-2]], [[nb:knowledge:adr-62]], [[nb:knowledge:adr-66]]
import os
import json
import subprocess
import time
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple
import core_logic as core
import constants


class AiInterface(ABC):
    """Abstract base class for AI CLI interfaces."""

    def __init__(self, binary_path: str, model: str = None):
        self.binary_path = binary_path
        self.model = model

    @abstractmethod
    def get_command(self, prompt: str) -> List[str]:
        """Returns the command list to execute the AI CLI."""
        pass

    def run(self, prompt: str, agent_name: str) -> Tuple[int, Dict[str, Any]]:
        """Executes the AI CLI and streams output with a mandatory 2s cooldown."""
        # 1. Enforce Global Rate Limit (2s between requests)
        project_root = os.getcwd()
        lock_dir = os.path.join(project_root, constants.STATE_DIR, "locks")
        os.makedirs(lock_dir, exist_ok=True)
        lock_file = os.path.join(lock_dir, "api.lock")

        try:
            now = time.time()
            if os.path.exists(lock_file):
                with open(lock_file, "r") as f:
                    last_time_str = f.read().strip()
                    last_time = float(last_time_str) if last_time_str else 0

                elapsed = now - last_time
                if elapsed < 2.0:
                    wait_time = 2.0 - elapsed
                    core.log(
                        f"Rate limiting active. Throttling for {wait_time:.2f}s...",
                        agent_name,
                    )
                    time.sleep(wait_time)
        except Exception as e:
            core.log(f"Rate limit check failed: {e}", agent_name)

        # 2. Execute command
        cmd = self.get_command(prompt)
        core.log(f"Invoking AI CLI: {' '.join(cmd)}", agent_name)

        stats = {}
        exit_code = 1

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )

            exit_code, stats = self._parse_output(process, agent_name)

            # 3. Update last run time (record when it *finished*)
            try:
                with open(lock_file, "w") as f:
                    f.write(str(time.time()))
            except Exception:
                pass

            return exit_code, stats
        except Exception as e:
            core.log(f"Error executing AI CLI: {e}", agent_name)
            return 1, {}

    @abstractmethod
    def _parse_output(
        self, process: subprocess.Popen, agent_name: str
    ) -> Tuple[int, Dict[str, Any]]:
        """Parses the output of the AI CLI and returns (exit_code, stats)."""
        pass


class GeminiInterface(AiInterface):
    """Interface for the Gemini CLI."""

    def get_command(self, prompt: str) -> List[str]:
        # -y: assume yes, -p: prompt, --output-format stream-json for token tracking
        cmd = [self.binary_path, "-y", "--output-format", "stream-json"]
        if self.model:
            cmd.extend(["-m", self.model])
        cmd.extend(["-p", prompt])
        return cmd

    def _parse_output(
        self, process: subprocess.Popen, agent_name: str
    ) -> Tuple[int, Dict[str, Any]]:
        stats = {}
        for line in process.stdout:
            line = line.strip()
            if not line:
                continue
            if line.startswith("{") and line.endswith("}"):
                try:
                    data = json.loads(line)
                    if data.get("type") == "message":
                        # Print assistant content as it arrives
                        if data.get("role") == "assistant" and "content" in data:
                            print(data["content"], end="", flush=True)
                    elif data.get("type") == "result":
                        stats = data.get("stats", {})
                except json.JSONDecodeError:
                    # Not valid JSON, just print it
                    print(line)
            else:
                # Regular output (e.g. YOLO warnings)
                print(line)

        process.wait()
        return process.returncode, stats


class OpenCodeInterface(AiInterface):
    """Interface for the OpenCode CLI."""

    def get_command(self, prompt: str) -> List[str]:
        # run: execute command, [message]: positional prompt
        # --dangerously-skip-permissions: auto-approve for autonomous execution
        return [self.binary_path, "run", prompt, "--dangerously-skip-permissions"]

    def _parse_output(
        self, process: subprocess.Popen, agent_name: str
    ) -> Tuple[int, Dict[str, Any]]:
        for line in process.stdout:
            print(line, end="", flush=True)
        process.wait()
        return process.returncode, {}


def get_interface(name: str, binary_path: str) -> AiInterface:
    """Factory function to get the appropriate AI interface."""
    if "opencode" in binary_path.lower() or name.lower() == "opencode":
        return OpenCodeInterface(binary_path)
    return GeminiInterface(binary_path)
