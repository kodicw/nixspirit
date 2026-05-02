# Context: [[nb:jbot:adr-2]]
import os
import subprocess
import time
from abc import ABC, abstractmethod
from typing import List
import jbot_core as core


class AiInterface(ABC):
    """Abstract base class for AI CLI interfaces."""

    def __init__(self, binary_path: str, model: str = None):
        self.binary_path = binary_path
        self.model = model

    @abstractmethod
    def get_command(self, prompt: str) -> List[str]:
        """Returns the command list to execute the AI CLI."""
        pass

    def run(self, prompt: str, agent_name: str) -> int:
        """Executes the AI CLI and streams output with a mandatory 2s cooldown."""
        # 1. Enforce Global Rate Limit (2s between requests)
        project_root = os.getcwd()
        lock_dir = os.path.join(project_root, ".jbot/locks")
        os.makedirs(lock_dir, exist_ok=True)
        lock_file = os.path.join(lock_dir, "api.lock")

        try:
            now = time.time()
            if os.path.exists(lock_file):
                with open(lock_file, "r") as f:
                    last_time = float(f.read().strip() or 0)

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

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            for line in process.stdout:
                print(line, end="", flush=True)
            process.wait()

            # 3. Update last run time (record when it *finished*)
            try:
                with open(lock_file, "w") as f:
                    f.write(str(time.time()))
            except Exception:
                pass

            return process.returncode
        except Exception as e:
            core.log(f"Error executing AI CLI: {e}", agent_name)
            return 1


class GeminiInterface(AiInterface):
    """Interface for the Gemini CLI."""

    def get_command(self, prompt: str) -> List[str]:
        # -y: assume yes, -p: prompt
        cmd = [self.binary_path, "-y"]
        if self.model:
            cmd.extend(["-m", self.model])
        cmd.extend(["-p", prompt])
        return cmd


class OpenCodeInterface(AiInterface):
    """Interface for the OpenCode CLI."""

    def get_command(self, prompt: str) -> List[str]:
        # run: execute command, [message]: positional prompt
        # --dangerously-skip-permissions: auto-approve for autonomous execution
        return [self.binary_path, "run", prompt, "--dangerously-skip-permissions"]


def get_interface(name: str, binary_path: str) -> AiInterface:
    """Factory function to get the appropriate AI interface."""
    if "opencode" in binary_path.lower() or name.lower() == "opencode":
        return OpenCodeInterface(binary_path)
    return GeminiInterface(binary_path)
