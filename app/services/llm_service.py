import json
import os
import sys
import re
import asyncio
import shutil
import uuid
import subprocess
import threading
from datetime import datetime, timezone
import datetime as dt_pkg
from typing import Optional, List, Dict, AsyncGenerator, Any
from app.core.patterns import PATTERNS
from app.core import config

WORKSPACE_ROOT = config.WORKSPACE_ROOT

FALLBACK_MODELS = {
    "google/antigravity-gemini-3.1-pro": "google/antigravity-gemini-3-flash",
    "google/antigravity-gemini-3-flash": "google/gemini-2.5-flash",
    "google/antigravity-claude-sonnet-4-6": "google/antigravity-gemini-3.1-pro",
    "google/antigravity-claude-opus-4-6-thinking": "google/antigravity-gemini-3.1-pro",
    "google/gemini-3-flash-preview": "google/antigravity-gemini-3-flash",
    "google/gemini-2.5-pro": "google/gemini-2.5-flash",
    "google/gemini-1.5-pro": "google/gemini-1.5-flash",
}

CAPACITY_KEYWORDS = [
    "429",
    "capacity",
    "quota",
    "exhausted",
    "rate limit",
    "not found",
    "404",
]


def global_log(msg, level="INFO", user_data=None):
    # If user_data has a 'verbose_logging' setting, we might force INFO level or something.
    # For now, stick to config.
    if config.LOG_LEVEL == "NONE":
        return
    if config.LOG_LEVEL == "INFO" and level == "DEBUG":
        return

    try:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        print(f"[{ts}] [{level}] {msg}")
    except:
        pass


def log_debug(msg):
    global_log(msg, level="DEBUG")


class ThreadedStreamReader:
    """Helper to read a pipe in a thread and provide an async interface."""

    def __init__(self, pipe, loop):
        self.pipe = pipe
        self.loop = loop
        self.queue = asyncio.Queue()
        self.thread = threading.Thread(target=self._read_pipe, daemon=True)
        self.thread.start()

    def _read_pipe(self):
        try:
            while True:
                # Read in small chunks to avoid blocking and ensure low latency
                chunk = self.pipe.read(1) # Byte by byte is safest for unbuffered
                if not chunk:
                    log_debug("Pipe EOF reached")
                    break
                self.loop.call_soon_threadsafe(self.queue.put_nowait, chunk)
        except Exception as e:
            log_debug(f"Error reading pipe: {e}")
        finally:
            self.loop.call_soon_threadsafe(self.queue.put_nowait, None)

    async def readline(self, timeout=None):
        # We now act as a stream reader for bytes
        line = b""
        while True:
            try:
                # Use a short timeout internally to allow checking for cancellation
                chunk = await asyncio.wait_for(self.queue.get(), timeout=0.1)
            except asyncio.TimeoutError:
                if timeout: # If user provided a global timeout, check if we exceeded it
                    # This is a bit simplified, but for our purposes 0.1s check is fine
                    continue
                continue # Keep waiting for data

            if chunk is None:
                # EOF reached, return what we have (even if no newline)
                return line
            line += chunk
            if chunk == b"\n":
                return line


class ThreadedProcess:
    """Minimal wrapper for subprocess.Popen to match asyncio.subprocess.Process."""

    def __init__(self, popen_proc, loop):
        self.proc = popen_proc
        self.loop = loop
        self.stdout = (
            ThreadedStreamReader(popen_proc.stdout, loop) if popen_proc.stdout else None
        )
        self.stderr = (
            ThreadedStreamReader(popen_proc.stderr, loop) if popen_proc.stderr else None
        )
        self.stdin = (
            popen_proc.stdin
        )  # synchronous writing usually works ok if not blocked
        self.returncode = None

    async def wait(self):
        while self.proc.poll() is None:
            await asyncio.sleep(0.01)
        self.returncode = self.proc.returncode
        return self.returncode

    def poll(self):
        return self.proc.poll()

    async def communicate(self, input=None):
        if input:
            self.proc.stdin.write(input)
            self.proc.stdin.flush()

        stdout_content = b""
        stderr_content = b""

        if self.stdout:
            while True:
                line = await self.stdout.readline()
                if not line:
                    break
                stdout_content += line

        if self.stderr:
            while True:
                line = await self.stderr.readline()
                if not line:
                    break
                stderr_content += line

        await self.wait()
        return stdout_content, stderr_content

    def terminate(self):
        self.proc.terminate()


class AsyncProcessWrapper:
    """Wrapper for asyncio.subprocess.Process to provide poll()."""

    def __init__(self, proc):
        self.proc = proc
        self.stdout = proc.stdout
        self.stderr = proc.stderr
        self.stdin = proc.stdin

    @property
    def returncode(self):
        return self.proc.returncode

    def poll(self):
        return self.proc.returncode

    async def wait(self):
        return await self.proc.wait()

    async def communicate(self, input=None):
        return await self.proc.communicate(input)

    def terminate(self):
        self.proc.terminate()


class OpenCodeAgent:
    WORKSPACE_ROOT = WORKSPACE_ROOT

    def __init__(
        self,
        model: str = "google/antigravity-gemini-3.1-pro",
        working_dir: Optional[str] = None,
    ):
        self.model_name = model
        self.working_dir = working_dir or os.getcwd()
        self.session_file = os.path.join(self.working_dir, "user_sessions.json")
        
        # Cross-platform command resolution
        cmd_base = config.OPENCODE_CMD
        if sys.platform == "win32" and not cmd_base.lower().endswith(".cmd"):
            self.opencode_cmd = shutil.which(f"{cmd_base}.cmd") or shutil.which(cmd_base) or cmd_base
        else:
            self.opencode_cmd = shutil.which(cmd_base) or cmd_base
            
        self.user_data = self._load_user_data()
        self.yolo_mode = False
        self.active_tasks: Dict[str, asyncio.Task] = {}

        # Ensure prompts directory exists
        prompts_dir = os.path.join(self.working_dir, "prompts")
        if not os.path.exists(prompts_dir):
            os.makedirs(prompts_dir, exist_ok=True)
            
        # Ensure workspace root exists
        if not os.path.exists(WORKSPACE_ROOT):
            try:
                os.makedirs(WORKSPACE_ROOT, exist_ok=True)
                global_log(f"Created workspace root: {WORKSPACE_ROOT}")
            except Exception as e:
                global_log(f"Failed to create workspace root: {e}", level="ERROR")

    def _load_user_data(self) -> Dict:
        if os.path.exists(self.session_file):
            try:
                with open(self.session_file, "r") as f:
                    data = json.load(f)
                    if not data:
                        return {}
                    if isinstance(next(iter(data.values())), str):
                        return {
                            uid: {
                                "active_session": suid,
                                "sessions": [suid],
                                "session_tools": {},
                            }
                            for uid, suid in data.items()
                        }
                    for uid in data:
                        if "sessions" not in data[uid]:
                            data[uid]["sessions"] = []
                        if "active_session" not in data[uid]:
                            data[uid]["active_session"] = None
                        if "session_tools" not in data[uid]:
                            data[uid]["session_tools"] = {}
                        if "session_tags" not in data[uid]:
                            data[uid]["session_tags"] = {}
                        if "pending_tools" not in data[uid]:
                            data[uid]["pending_tools"] = []
                        if "pinned_sessions" not in data[uid]:
                            data[uid]["pinned_sessions"] = []
                        if "session_metadata" not in data[uid]:
                            data[uid]["session_metadata"] = {}
                        if "settings" not in data[uid]:
                            data[uid]["settings"] = {
                                "show_mic": True,
                                "interactive_mode": True,
                                "copy_formatted": False,
                                "default_model": "google/antigravity-gemini-3.1-pro",
                            }
                        else:
                            # Ensure defaults for existing settings objects
                            if "copy_formatted" not in data[uid]["settings"]:
                                data[uid]["settings"]["copy_formatted"] = False
                            if "default_model" not in data[uid]["settings"]:
                                data[uid]["settings"]["default_model"] = (
                                    "google/antigravity-gemini-3.1-pro"
                                )
                    return data
            except:
                return {}
        return {}

    def _save_user_data(self):
        with open(self.session_file, "w") as f:
            json.dump(self.user_data, f, indent=2)

    async def get_git_status(self, workspace_path: str) -> Dict:
        """Fetch basic Git status for the workspace."""
        if not os.path.exists(os.path.join(workspace_path, ".git")):
            return {"is_repo": False}
            
        try:
            # Get current branch
            proc = await self._create_subprocess(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=workspace_path.replace("\\", "/"),
            )
            stdout, _ = await proc.communicate()
            branch = stdout.decode().strip()
            
            # Check for changes
            proc = await self._create_subprocess(
                ["git", "status", "--porcelain"],
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=workspace_path.replace("\\", "/"),
            )
            stdout, _ = await proc.communicate()
            changes = stdout.decode().strip()
            has_changes = len(changes) > 0
            
            return {
                "is_repo": True,
                "branch": branch,
                "has_changes": has_changes,
                "change_count": len(changes.splitlines()) if has_changes else 0
            }
        except Exception as e:
            global_log(f"Error fetching Git status: {e}", level="DEBUG")
            return {"is_repo": False, "error": str(e)}

    async def get_available_models(self) -> List[str]:
        try:
            proc = await self._create_subprocess(
                [self.opencode_cmd, "models"],
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.working_dir.replace("\\", "/"),
            )
            stdout, stderr = await proc.communicate()
            content = stdout.decode().strip()
            if not content:
                return []
            # Split by lines and filter empty
            return [line.strip() for line in content.splitlines() if line.strip()]
        except Exception as e:
            global_log(f"Error fetching models: {e}", level="ERROR")
            return []

    async def get_available_agents(self) -> List[Dict]:
        try:
            # Try 'agent list' without JSON format since it's not supported
            proc = await self._create_subprocess(
                [self.opencode_cmd, "agent", "list"],
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.working_dir.replace("\\", "/"),
            )
            stdout, stderr = await proc.communicate()
            content = stdout.decode().strip()
            
            agents = [{"id": "default", "name": "Default Agent"}]
            seen = {"default"}
            
            if content:
                # Parse lines like "general (subagent)"
                for line in content.splitlines():
                    line = line.strip()
                    if "(" in line and ")" in line and not line.startswith("[") and not line.startswith("{"):
                        parts = line.split("(")
                        agent_id = parts[0].strip()
                        if agent_id and agent_id not in seen:
                            agents.append({
                                "id": agent_id,
                                "name": agent_id.capitalize() + " Agent"
                            })
                            seen.add(agent_id)
            
            return agents
        except Exception as e:
            global_log(f"Error fetching agents: {e}", level="ERROR")
            return [
                {"id": "default", "name": "Default Agent"},
                {"id": "github", "name": "GitHub Agent"},
                {"id": "expert", "name": "Expert Agent"}
            ]

    def get_user_settings(self, user_id: str) -> Dict:
        default_settings = {
            "show_mic": True,
            "interactive_mode": True,
            "copy_formatted": False,
            "default_model": "google/antigravity-gemini-3.1-pro",
            "default_workspace": WORKSPACE_ROOT,
        }
        if user_id not in self.user_data:
            return default_settings

        settings = self.user_data[user_id].get("settings", default_settings)
        # Ensure all keys exist
        for k, v in default_settings.items():
            if k not in settings:
                settings[k] = v
        return settings

    def update_user_settings(self, user_id: str, settings: Dict):
        if user_id not in self.user_data:
            self.user_data[user_id] = {
                "active_session": None,
                "sessions": [],
                "session_tools": {},
                "pending_tools": [],
                "pinned_sessions": [],
                "session_metadata": {},
                "settings": {
                    "show_mic": True,
                    "interactive_mode": True,
                    "copy_formatted": False,
                    "default_model": "google/antigravity-gemini-3.1-pro",
                    "default_workspace": WORKSPACE_ROOT,
                },
            }

        if "settings" not in self.user_data[user_id]:
            self.user_data[user_id]["settings"] = {
                "show_mic": True,
                "interactive_mode": True,
                "copy_formatted": False,
                "default_model": "google/antigravity-gemini-3.1-pro",
                "default_workspace": WORKSPACE_ROOT,
            }

        if "default_workspace" in settings:
            if not settings["default_workspace"].startswith(WORKSPACE_ROOT):
                del settings["default_workspace"]

        self.user_data[user_id]["settings"].update(settings)
        self._save_user_data()

    async def _create_subprocess(self, args, **kwargs):
        if sys.platform == "win32":
            # Always use ThreadedProcess on Windows for maximum reliability across loop types
            from subprocess import Popen, PIPE

            loop = asyncio.get_running_loop()

            # Adapt kwargs for Popen
            popen_kwargs = {
                "stdout": kwargs.get("stdout", PIPE),
                "stderr": kwargs.get("stderr", PIPE),
                "stdin": kwargs.get("stdin", PIPE),
                "cwd": kwargs.get("cwd"),
                "env": kwargs.get("env"),
                "bufsize": 0,  # Unbuffered
            }
            
            # Explicitly find opencode.cmd if it exists to avoid shell dependency
            if args[0] == self.opencode_cmd and not args[0].lower().endswith(".cmd"):
                cmd_path = shutil.which(f"{args[0]}.cmd") or shutil.which(args[0])
                if cmd_path:
                    args[0] = cmd_path

            proc = Popen(args, **popen_kwargs)
            return ThreadedProcess(proc, loop)

        try:
            p = await asyncio.create_subprocess_exec(*args, **kwargs)
            return AsyncProcessWrapper(p)
        except Exception as e:
            global_log(f"Subprocess creation failed: {e}", level="ERROR")
            raise

    def toggle_pin(self, user_id: str, session_uuid: str) -> bool:
        if user_id not in self.user_data:
            self.user_data[user_id] = {
                "active_session": None,
                "sessions": [],
                "session_tools": {},
                "pending_tools": [],
                "pinned_sessions": [],
                "session_metadata": {},
            }

        user_info = self.user_data[user_id]
        if "pinned_sessions" not in user_info:
            user_info["pinned_sessions"] = []

        if session_uuid in user_info["pinned_sessions"]:
            user_info["pinned_sessions"].remove(session_uuid)
            res = False
        else:
            user_info["pinned_sessions"].append(session_uuid)
            res = True

        self._save_user_data()
        return res

    def get_session_tools(self, user_id: str, session_uuid: str) -> List[str]:
        user_info = self.user_data.get(user_id)
        if not user_info:
            return []
        if session_uuid == "pending":
            return user_info.get("pending_tools", [])
        return user_info.get("session_tools", {}).get(session_uuid, [])

    def set_session_tools(self, user_id: str, session_uuid: str, tools: List[str]):
        if user_id not in self.user_data:
            self.user_data[user_id] = {
                "active_session": None,
                "sessions": [],
                "session_tools": {},
                "pending_tools": [],
                "session_metadata": {},
            }
        if session_uuid == "pending":
            self.user_data[user_id]["pending_tools"] = tools
        else:
            if "session_tools" not in self.user_data[user_id]:
                self.user_data[user_id]["session_tools"] = {}
            self.user_data[user_id]["session_tools"][session_uuid] = tools
        self._save_user_data()

    def list_patterns(self) -> List[str]:
        return sorted([k for k in PATTERNS.keys() if k != "__explanations__"])

    async def apply_pattern(
        self,
        user_id: str,
        pattern_name: str,
        input_text: str,
        model: Optional[str] = None,
        file_paths: Optional[List[str]] = None,
    ) -> str:
        # Check if it's a custom prompt file
        prompts_dir = os.path.join(self.working_dir, "prompts")
        if os.path.exists(prompts_dir):
            # Try exact match first
            custom_path = os.path.join(prompts_dir, pattern_name)
            if os.path.exists(custom_path):
                try:
                    with open(custom_path, "r", encoding="utf-8") as f:
                        system = f.read()
                    return await self.generate_response(
                        user_id,
                        f"{system}\n\nUSER INPUT:\n{input_text}",
                        model=model,
                        file_paths=file_paths,
                    )
                except Exception as e:
                    return f"Error reading custom prompt '{pattern_name}': {str(e)}"

        # Fallback to system patterns
        system = PATTERNS.get(pattern_name)
        if not system:
            # Try removing colon if present (common issue)
            clean_name = pattern_name.rstrip(":")
            system = PATTERNS.get(clean_name)

        if not system:
            return f"Error: Pattern '{pattern_name}' not found."
        return await self.generate_response(
            user_id,
            f"{system}\n\nUSER INPUT:\n{input_text}",
            model=model,
            file_paths=file_paths,
        )

    def _filter_errors(self, err: str) -> str:
        err = re.sub(r".*?\[DEP0151\] DeprecationWarning:.*?(\n|$)", "", err)
        err = re.sub(
            r".*?Default \"index\" lookups for the main are deprecated for ES modules..*?(\n|$)",
            "",
            err,
        )
        return "\n".join([s for s in err.splitlines() if s.strip()]).strip()

    def _get_text_content(self, content: Any) -> str:
        """Extracts plain text from potentially multimodal or structured content."""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            text_parts = []
            for part in content:
                if isinstance(part, dict) and "text" in part:
                    text_parts.append(part["text"])
                elif isinstance(part, str):
                    text_parts.append(part)
            return "".join(text_parts)
        return str(content)

    def filter_title_text(self, text: str) -> str:
        """
        Filters out system instructions and file paths from the text to generate a clean title.
        """
        if not text:
            return "New Conversation"

        # 1. Remove [SYSTEM INSTRUCTION: ... ] blocks (including multi-line)
        text = re.sub(r"\[SYSTEM INSTRUCTION:.*?\]", "", text, flags=re.DOTALL)

        # 2. Remove file path references starting with @
        # Matches @ followed by non-whitespace characters
        text = re.sub(r"@\S+", "", text)

        # 3. Remove common file path patterns (absolute or relative)
        # Windows paths: C:\Users\..., D:\... (Stopped matching spaces to preserve sentence structure)
        text = re.sub(r"[a-zA-Z]:\\[\w\-.\\\\]+", "", text)
        # Unix paths: /var/log/..., /tmp/...
        text = re.sub(r"(?<!\w)/[\w\-./]+", "", text)

        # 4. Cleanup whitespace
        text = re.sub(r"\s+", " ", text).strip()

        # 5. Fallback and truncation
        if not text or len(text) < 3:
            return "New Conversation"

        if len(text) > 50:
            return text[:47] + "..."

        return text

    async def stop_chat(self, user_id: str):
        task = self.active_tasks.pop(user_id, None)
        if task:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            return True
        return False

    async def _get_latest_session_uuid(self) -> Optional[str]:
        try:
            global_log("Executing session list --format json...")
            proc = await self._create_subprocess(
                [self.opencode_cmd, "session", "list", "--format", "json"],
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.working_dir.replace("\\", "/"),
            )
            stdout, stderr = await proc.communicate()
            content = stdout.decode().strip()
            if not content:
                return None

            sessions = json.loads(content)
            if not sessions:
                return None

            sessions.sort(key=lambda x: x.get("created", 0), reverse=True)
            res = sessions[0].get("id")
            global_log(f"Latest session ID found: {res}")
            return res
        except Exception as e:
            global_log(f"Error in _get_latest_session_uuid: {str(e)}")
            return None

    async def generate_response_stream(
        self,
        user_id: str,
        prompt: str,
        model: Optional[str] = None,
        agent_name: Optional[str] = None,
        file_paths: Optional[List[str]] = None,
        resume_session: Optional[str] = "AUTO",
        plan_mode: bool = False,
    ) -> AsyncGenerator[Dict, None]:
        def log_debug(msg):
            global_log(f"[{user_id}] {msg}", level="DEBUG")

        if user_id not in self.user_data:
            self.user_data[user_id] = {
                "active_session": None,
                "sessions": [],
                "session_tools": {},
                "pending_tools": [],
                "session_metadata": {},
            }
        else:
            self.user_data[user_id].setdefault("sessions", [])
            self.user_data[user_id].setdefault("active_session", None)
            self.user_data[user_id].setdefault("session_tools", {})
            self.user_data[user_id].setdefault("pending_tools", [])
            self.user_data[user_id].setdefault("session_metadata", {})

        if resume_session == "AUTO":
            session_uuid = self.user_data[user_id].get("active_session")
        else:
            session_uuid = resume_session

        settings = self.get_user_settings(user_id)
        current_model = model or settings.get("default_model") or self.model_name
        
        # Signal start immediately to clear UI loading state
        yield {"type": "step_start", "message": "Initializing OpenCode Agent..."}

        if plan_mode:
            yield {
                "type": "plan_status",
                "status": "active",
                "message": "Entering Plan Mode...",
            }
            # Inject Plan Mode instruction
            plan_instruction = (
                "\n\n[SYSTEM INSTRUCTION: PLAN MODE ACTIVE]\n"
                "Provide a comprehensive, step-by-step plan for the user's request. "
                "Describe exactly what tools you would use and why. "
                "CRITICAL: Do NOT execute any modification tools (like write, edit, shell) yet. "
                "Wait for the user to approve your plan."
            )
            prompt = f"{plan_instruction}\n\n{prompt}"

        # System Prompt Injection for Interactive Mode
        if settings.get("interactive_mode", True):
            enabled_tools = self.get_session_tools(user_id, session_uuid or "pending")
            if enabled_tools:
                log_debug(f"User intended tools: {enabled_tools}")

            default_interactive = (
                "You can ask interactive multiple-choice or open-ended questions to the user in their preferred language (e.g., Greek).\n"
                "To trigger a question card, include a JSON block in your response using this format:\n"
                '{"type": "question", "question": "Your question text here", "options": ["Option 1", "Option 2"], "allow_multiple": false}\n'
                "- The 'question' and 'options' values should match the language of the conversation.\n"
                "- If 'allow_multiple' is true, users can select several options.\n"
                "- If 'options' is empty [], it is an open-ended question.\n"
                "The user's response will be sent back to you as a normal message."
            )
            global_setting = config.get_global_setting("interactive_mode_instructions")
            interactive_instruction = (
                global_setting if global_setting is not None else default_interactive
            )
            prompt = f"\n\n[SYSTEM INSTRUCTION: INTERACTIVE QUESTIONING ENABLED]\n{interactive_instruction}\n\n{prompt}"
        else:
            # Subtle instruction to avoid JSON questioning without being overly rigid about identity.
            prompt = f"\n\n[SYSTEM INSTRUCTION: Provide standard text responses only. Do not use JSON formatting for questions.]\n\n{prompt}"

        attempt = 0
        max_attempts = 2

        # Prepare environment with tool permissions
        env = os.environ.copy()
        enabled_tools = self.get_session_tools(user_id, session_uuid or "pending")
        if enabled_tools:
            perms = {"*": "deny"}
            for t in enabled_tools:
                perms[t] = "allow"
                # Map common aliases/guards
                if t == "google_search" or t == "google_web_search":
                    perms["websearch"] = "allow"
                if t in ["edit", "write", "replace", "write_file"]:
                    perms["edit"] = "allow"
                if t in ["read", "read_file", "list", "list_directory"]:
                    perms["read"] = "allow"
                    perms["list"] = "allow"

            # Core helper tools that should generally be allowed for app integration
            perms["question"] = "allow"

            opencode_config = {"permission": perms}
            env["OPENCODE_CONFIG_CONTENT"] = json.dumps(opencode_config)
            log_debug(
                f"Applying tool permissions via OPENCODE_CONFIG_CONTENT: {enabled_tools}"
            )

        # Resolve Workspace
        workspace = self.get_session_workspace(user_id, session_uuid or "pending")
        norm_workspace = os.path.normcase(os.path.abspath(workspace))
        norm_root = os.path.normcase(os.path.abspath(WORKSPACE_ROOT))
        
        log_debug(f"Resolved workspace: {workspace} (norm: {norm_workspace})")
        
        # Check if workspace is within root in a cross-platform way
        is_within_root = False
        try:
            common = os.path.normcase(os.path.commonpath([norm_root, norm_workspace]))
            is_within_root = common == norm_root
        except:
            pass
        
        # Sanitize for CLI (use forward slashes)
        cli_workspace = workspace.replace("\\", "/")

        if not os.path.exists(workspace) and is_within_root:
            try:
                os.makedirs(workspace, exist_ok=True)
                global_log(f"Created missing workspace: {workspace}")
            except Exception as e:
                global_log(f"Error creating workspace {workspace}: {e}", level="ERROR")
                workspace = WORKSPACE_ROOT.replace("\\", "/")  # Fallback

        while attempt < max_attempts:
            attempt += 1

            args = [
                self.opencode_cmd,
                "run",
                "--format",
                "json",
                "--thinking",
                "--dir",
                workspace.replace("\\", "/"),
            ]
            if session_uuid:
                args.extend(["-s", session_uuid])
            if current_model:
                args.extend(["-m", current_model])
            if agent_name and agent_name != "default":
                args.extend(["--agent", agent_name])
            if file_paths:
                for fp in file_paths:
                    args.extend(["-f", fp.replace("\\", "/")])

            log_debug(f"Attempt {attempt}: Running command {' '.join(args)}")

            should_fallback = False
            high_demand_detected = False
            proc = None
            stderr_buffer = []
            in_reasoning = False
            try:
                try:
                    proc = await self._create_subprocess(
                        args,
                        stdin=asyncio.subprocess.PIPE,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                        cwd=workspace,
                        env=env,
                    )
                except Exception as e:
                    global_log(f"CRITICAL: Failed to start subprocess: {e}", level="ERROR")
                    yield {"type": "error", "content": f"Failed to start backend: {str(e)}"}
                    return
                
                if prompt:

                    log_debug("Writing prompt to stdin...")

                    async def write_to_stdin(proc, data):
                        if hasattr(proc.stdin, "drain"):  # asyncio.StreamWriter
                            proc.stdin.write(data)
                            await proc.stdin.drain()
                            proc.stdin.close()
                        else:  # Synchronous pipe from Popen

                            def sync_write():
                                proc.stdin.write(data)
                                proc.stdin.flush()
                                proc.stdin.close()

                            await asyncio.to_thread(sync_write)

                    await write_to_stdin(proc, prompt.encode("utf-8"))

                async def capture_stderr(pipe):
                    nonlocal high_demand_detected
                    if not pipe:
                        return
                    while True:
                        try:
                            line = await pipe.readline(timeout=0.5)
                        except:
                            line = None
                            
                        if not line:
                            if proc and proc.poll() is not None:
                                break
                            await asyncio.sleep(0.1)
                            continue
                        line_str = line.decode(errors="replace").strip()
                        log_debug(f"STDERR: {line_str}")
                        stderr_buffer.append(line_str)
                        # OpenCode high demand signal might be different, but let's keep this for now
                        if "High demand" in line_str or "429" in line_str:
                            log_debug("High demand detected in stderr")
                            high_demand_detected = True
                            try:
                                if proc:
                                    proc.terminate()
                            except:
                                pass

                stderr_task = asyncio.create_task(capture_stderr(proc.stderr))

                log_debug("Starting to read stdout")
                current_message_content = ""
                json_buffer = ""
                in_json_block = False
                captured_session_id = False

                if not proc or not proc.stdout:
                    log_debug("No stdout to read")
                    return

                while True:
                    line = await proc.stdout.readline(timeout=1.0)
                    if not line:
                        if proc.poll() is not None:
                            log_debug("Stdout closed (EOF) and process finished")
                            break
                        continue
                    line_str = line.decode(errors="replace").strip()
                    if not line_str:
                        continue

                    log_debug(f"Received line ({len(line_str)} chars)")

                    if "High demand. Retry?" in line_str:
                        log_debug("High demand detected in stdout")
                        high_demand_detected = True
                        try:
                            proc.terminate()
                        except:
                            pass
                        break

                    try:
                        data = json.loads(line_str)

                        # Capture session ID from OpenCode event
                        if not captured_session_id and data.get("sessionID"):
                            new_id = data["sessionID"]
                            if not session_uuid:
                                log_debug(f"Captured session ID: {new_id}")
                                self.user_data[user_id]["active_session"] = new_id
                                if new_id not in self.user_data[user_id]["sessions"]:
                                    self.user_data[user_id]["sessions"].append(new_id)

                                # Auto-name the session based on the first prompt
                                filtered_title = self.filter_title_text(prompt)
                                await self.update_session_title(
                                    user_id, new_id, filtered_title
                                )

                                if "session_metadata" not in self.user_data[user_id]:
                                    self.user_data[user_id]["session_metadata"] = {}

                                # Store model in metadata for persistence
                                if (
                                    new_id
                                    not in self.user_data[user_id]["session_metadata"]
                                ):
                                    self.user_data[user_id]["session_metadata"][
                                        new_id
                                    ] = {}

                                self.user_data[user_id]["session_metadata"][new_id][
                                    "model"
                                ] = current_model

                                self._save_user_data()
                                yield {"type": "init", "session_id": new_id}
                                session_uuid = new_id
                            captured_session_id = True

                        # Transform OpenCode events to Gemini format
                        transformed_data = None

                        if data.get("type") == "text":
                            if in_reasoning:
                                yield {"type": "reasoning_finish"}
                                in_reasoning = False
                            transformed_data = {
                                "type": "message",
                                "role": "assistant",
                                "content": data.get("part", {}).get("text", ""),
                            }
                        elif data.get("type") == "reasoning":
                            text = data.get("part", {}).get("text", "")
                            if not in_reasoning:
                                transformed_data = {
                                    "type": "reasoning_start",
                                    "content": text,
                                }
                                in_reasoning = True
                            else:
                                transformed_data = {
                                    "type": "reasoning",
                                    "content": text,
                                }
                        elif data.get("type") == "tool_use":
                            if in_reasoning:
                                yield {"type": "reasoning_finish"}
                                in_reasoning = False

                            tool_part = data.get("part", {})
                            state = tool_part.get("state", {})
                            if state.get("status") == "completed":
                                transformed_data = {
                                    "type": "tool_result",
                                    "tool_name": tool_part.get("tool"),
                                    "output": state.get("output", ""),
                                }
                            else:
                                # New event: tool started
                                transformed_data = {
                                    "type": "tool_use",
                                    "tool_name": tool_part.get("tool"),
                                    "parameters": tool_part.get("input", {}),
                                }
                        elif data.get("type") == "step_finish":
                            transformed_data = {
                                "type": "step_finish",
                                "tokens": data.get("part", {}).get("tokens", {}),
                                "cost": data.get("part", {}).get("cost", 0),
                            }

                        if not transformed_data:
                            continue

                        data = transformed_data

                        # Handle interactive questioning protocol
                        if (
                            data.get("type") == "message"
                            and data.get("role") == "assistant"
                        ):
                            content = data.get("content", "")

                            # Add to global buffer for full detection
                            current_message_content += content

                            # Logic to hide JSON and potential markdown backticks from the stream
                            cleaned_content = ""
                            i = 0
                            while i < len(content):
                                char = content[i]
                                if not in_json_block:
                                    # Lookahead for potential JSON start
                                    # Only buffer if we see { or ` and NOT in reasoning
                                    if (char == "{" or char == "`") and not in_reasoning:
                                        # Peek ahead for "type": "question" or ```json
                                        rem = content[i:]
                                        # Aggressive peek: if we see { followed soon by "type"
                                        if char == "{" and (
                                            '"type"' in rem[:50]
                                            or '"type"' in current_message_content[-50:]
                                        ):
                                            in_json_block = True
                                            json_buffer = char
                                        elif char == "`" and rem.startswith("```"):
                                            in_json_block = True
                                            json_buffer = char
                                        else:
                                            cleaned_content += char
                                    else:
                                        cleaned_content += char
                                else:
                                    json_buffer += char
                                    # Check for end of block
                                    if char == "}" or char == "`":
                                        # Heuristic: if valid question, stay in block until closed
                                        if (
                                            '"type": "question"' in json_buffer
                                            or '"type":"question"' in json_buffer
                                        ):
                                            try:
                                                # Try to extract JSON from the buffer (might have backticks)
                                                inner_json_match = re.search(
                                                    r"\{\s*\"type\"\s*:\s*\"question\".*?\}",
                                                    json_buffer,
                                                    re.DOTALL,
                                                )
                                                if inner_json_match:
                                                    json_text = inner_json_match.group(
                                                        0
                                                    )
                                                    json.loads(json_text)
                                                    # Balanced? Check if closed correctly
                                                    is_wrapped = json_buffer.startswith(
                                                        "```"
                                                    )
                                                    if (
                                                        is_wrapped
                                                        and json_buffer.endswith("```")
                                                    ) or (
                                                        not is_wrapped
                                                        and json_buffer.endswith("}")
                                                    ):
                                                        in_json_block = False
                                                        json_buffer = ""
                                            except:
                                                pass  # Not complete yet
                                        else:
                                            # Not a question. Flush it.
                                            # If buffer ends with ` (closing backtick) or looks too big
                                            if (
                                                char == "`" and json_buffer.endswith("```")
                                            ) or len(json_buffer) > 50:
                                                cleaned_content += json_buffer
                                                in_json_block = False
                                                json_buffer = ""
                                i += 1

                            data["content"] = cleaned_content

                            # Global buffer handles full detection and yielding
                            # We update the regex to optionally swallow surrounding backticks and newlines
                            question_pattern = r"(?:```(?:json)?\s*)?\{\s*\"type\"\s*:\s*\"question\".*?\}(?:\s*```)?"
                            question_match = re.search(
                                question_pattern, current_message_content, re.DOTALL
                            )
                            if question_match:
                                try:
                                    full_match_text = question_match.group(0)
                                    # Extract JUST the JSON part for parsing
                                    json_only_match = re.search(
                                        r"\{\s*\"type\"\s*:\s*\"question\".*?\}",
                                        full_match_text,
                                        re.DOTALL,
                                    )
                                    if json_only_match:
                                        question_data = json.loads(
                                            json_only_match.group(0)
                                        )
                                        yield question_data
                                        current_message_content = (
                                            current_message_content.replace(
                                                full_match_text, ""
                                            )
                                        )
                                except:
                                    pass

                            # If we have nothing to show yet (still buffering JSON/markdown), don't yield this chunk's message
                            if not data["content"] and in_json_block:
                                continue

                        # Truncate large tool outputs
                        if data.get("type") == "tool_result" and "output" in data:
                            output = data["output"]
                            threshold = 20 * 1024  # 20KB
                            if len(output) > threshold:
                                truncated = output[:threshold]
                                # Save full output to a file
                                try:
                                    fname = f"output_{uuid.uuid4().hex}.txt"
                                    fpath = os.path.join(config.UPLOAD_DIR, fname)
                                    with open(fpath, "w", encoding="utf-8") as f:
                                        f.write(output)
                                    data["full_output_path"] = f"/uploads/{fname}"
                                    data["output"] = (
                                        f"{truncated}\n\n[Output truncated. Full output available below.]"
                                    )
                                    log_debug(
                                        f"Truncated tool output and saved to {fpath}"
                                    )
                                except Exception as e:
                                    log_debug(f"Error saving full output: {str(e)}")
                                    data["output"] = (
                                        f"{truncated}\n\n[Output truncated. Error saving full version.]"
                                    )

                                log_debug(
                                    f"Truncated tool output from {len(output)} to {len(data['output'])} bytes"
                                )

                        # Check for capacity error in JSON chunks
                        content_to_check = str(data).lower()
                        if (
                            any(k in content_to_check for k in CAPACITY_KEYWORDS)
                            and attempt < max_attempts
                        ):
                            fallback = FALLBACK_MODELS.get(current_model)
                            if fallback:
                                log_debug(
                                    f"Capacity error detected in stdout, falling back to {fallback}"
                                )
                                yield {
                                    "type": "model_switch",
                                    "old_model": current_model,
                                    "new_model": fallback,
                                }
                                yield {
                                    "type": "message",
                                    "role": "assistant",
                                    "content": f"\n\n[Model {current_model} is currently busy or quota exhausted. Switching to {fallback} for a faster response...]\n\n",
                                }
                                current_model = fallback
                                should_fallback = True
                                break

                        yield data
                    except json.JSONDecodeError:
                        yield {"type": "raw", "content": line_str}

                if should_fallback:
                    try:
                        if proc.returncode is None:
                            proc.terminate()
                            await proc.wait()
                    except:
                        pass
                    continue

                await proc.wait()
                await stderr_task

                if in_reasoning:
                    yield {"type": "reasoning_finish"}
                    in_reasoning = False

                log_debug(f"Process exited with code {proc.returncode}")

                if high_demand_detected:
                    yield {
                        "type": "question",
                        "question": "We are currently experiencing high demand. Should I keep trying?",
                        "options": ["Retry", "Stop"],
                        "allow_multiple": False,
                        "is_retry": True,
                    }
                    break

                if plan_mode:
                    yield {
                        "type": "plan_status",
                        "status": "completed",
                        "message": "Plan complete. Review proposed changes below.",
                    }

                # Check for capacity error in stderr if process failed
                if proc.returncode != 0 and not should_fallback:
                    err_text = "\n".join(stderr_buffer).lower()
                    if (
                        any(k in err_text for k in CAPACITY_KEYWORDS)
                        and attempt < max_attempts
                    ):
                        fallback = FALLBACK_MODELS.get(current_model)
                        if fallback:
                            log_debug(
                                f"Capacity error detected in stderr, falling back to {fallback}"
                            )
                            yield {
                                "type": "model_switch",
                                "old_model": current_model,
                                "new_model": fallback,
                            }
                            yield {
                                "type": "message",
                                "role": "assistant",
                                "content": f"\n\n[Model {current_model} is currently busy or quota exhausted. Switching to {fallback}...]\n\n",
                            }
                            current_model = fallback
                            continue

                    # If not a capacity error, yield generic exit code error
                    yield {"type": "error", "content": f"Exit code {proc.returncode}"}

                break
            finally:
                if proc and proc.returncode is None:
                    try:
                        proc.terminate()
                        await proc.wait()
                    except:
                        pass

    async def generate_response(
        self,
        user_id: str,
        prompt: str,
        model: Optional[str] = None,
        agent_name: Optional[str] = None,
        file_paths: Optional[List[str]] = None,
        resume_session: Optional[str] = "AUTO",
    ) -> str:
        full_response = ""
        async for chunk in self.generate_response_stream(
            user_id, prompt, model, agent_name, file_paths, resume_session=resume_session
        ):
            if chunk.get("type") == "message":
                full_response += chunk.get("content", "")
            elif chunk.get("type") == "error":
                full_response += f"\n[Error: {chunk.get('content')}]"
            elif chunk.get("type") == "raw":
                full_response += chunk.get("content", "") + "\n"
        return full_response.strip()

    async def update_session_title(
        self, user_id: str, uuid: str, new_title: str
    ) -> bool:
        if user_id in self.user_data and uuid in self.user_data[user_id]["sessions"]:
            if "custom_titles" not in self.user_data[user_id]:
                self.user_data[user_id]["custom_titles"] = {}
            self.user_data[user_id]["custom_titles"][uuid] = new_title
            self._save_user_data()
            return True
        return False

    async def update_session_tags(
        self, user_id: str, uuid: str, tags: List[str]
    ) -> bool:
        if user_id in self.user_data and uuid in self.user_data[user_id]["sessions"]:
            if "session_tags" not in self.user_data[user_id]:
                self.user_data[user_id]["session_tags"] = {}
            self.user_data[user_id]["session_tags"][uuid] = tags
            self._save_user_data()
            return True
        return False

    def get_unique_tags(self, user_id: str) -> List[str]:
        if user_id not in self.user_data:
            return []
        user_info = self.user_data[user_id]
        all_tags = set()
        for tags in user_info.get("session_tags", {}).values():
            for t in tags:
                all_tags.add(t)
        return sorted(list(all_tags))

    def get_session_workspace(self, user_id: str, session_uuid: str) -> str:
        if user_id not in self.user_data:
            return WORKSPACE_ROOT
        user_info = self.user_data[user_id]
        workspaces = user_info.get("session_workspaces", {})
        path = workspaces.get(session_uuid)
        if not path:
            settings = user_info.get("settings", {})
            path = settings.get("default_workspace", WORKSPACE_ROOT)
        return path

    def update_session_workspace(
        self, user_id: str, session_uuid: str, workspace_path: str
    ):
        # Normalize paths for comparison
        # Use abspath to ensure we have the full path
        norm_root = os.path.normcase(os.path.abspath(WORKSPACE_ROOT))
        norm_path = os.path.normcase(os.path.abspath(workspace_path))
        
        # Security check: must be within root or equal to root
        try:
            common = os.path.normcase(os.path.commonpath([norm_root, norm_path]))
            is_within = common == norm_root
        except ValueError:
            is_within = False

        if not is_within:
            return False

        if user_id not in self.user_data:
            return False

        if "session_workspaces" not in self.user_data[user_id]:
            self.user_data[user_id]["session_workspaces"] = {}
        self.user_data[user_id]["session_workspaces"][session_uuid] = workspace_path
        self._save_user_data()
        return True

    def get_available_workspaces(self) -> List[str]:
        workspaces = []
        if not os.path.exists(WORKSPACE_ROOT):
            return [WORKSPACE_ROOT]

        workspaces.append(WORKSPACE_ROOT)
        try:
            # Walk with limited depth and ignore common massive folders
            ignore_dirs = {
                "node_modules",
                ".git",
                ".venv",
                "venv",
                "__pycache__",
                ".opencode",
                "tmp",
                "data",
            }
            for root, dirs, files in os.walk(WORKSPACE_ROOT):
                # Modify dirs in-place to prune the walk
                dirs[:] = [
                    d for d in dirs if d not in ignore_dirs and not d.startswith(".")
                ]

                # Limit total count to prevent UI lag
                if len(workspaces) > 500:
                    break

                for d in dirs:
                    full_path = os.path.join(root, d)
                    workspaces.append(full_path)

                # Limit depth by checking relative path
                rel_path = os.path.relpath(root, WORKSPACE_ROOT)
                if rel_path != "." and rel_path.count(os.sep) >= 2:
                    dirs[:] = []  # Don't go deeper than 3 levels

        except Exception as e:
            global_log(f"Error walking workspaces: {e}")

        return sorted(list(set(workspaces)))

    def is_user_session(self, user_id: str, session_uuid: str) -> bool:
        """Check if a session belongs to a user without filtering for sidebar."""
        if user_id not in self.user_data:
            return False
        return session_uuid in self.user_data[user_id].get("sessions", [])

    async def get_user_sessions(
        self,
        user_id: str,
        limit: Optional[int] = None,
        offset: int = 0,
        tags: Optional[List[str]] = None,
        force_sync: bool = False,
    ) -> Dict[str, Any]:
        global_log(f"get_user_sessions for {user_id}, limit={limit}, offset={offset}, force_sync={force_sync}")
        if user_id not in self.user_data:
            self.user_data[user_id] = {
                "active_session": None,
                "sessions": [],
                "session_tools": {},
                "pending_tools": [],
                "pinned_sessions": [],
                "session_metadata": {},
            }
            self._save_user_data()

        user_info = self.user_data[user_id]
        uuids = user_info.get("sessions", [])
        custom_titles = user_info.get("custom_titles", {})
        session_tags = user_info.get("session_tags", {})
        session_metadata = user_info.get("session_metadata", {})
        session_forks = user_info.get("session_forks", {})

        global_log(f"User has {len(uuids)} session UUIDs")

        # Check if we have metadata for all sessions
        missing_metadata = [u for u in uuids if u not in session_metadata]
        global_log(f"Missing metadata for {len(missing_metadata)} sessions")

        all_sessions = []

        # Force sync if list is empty or explicitly requested
        if not uuids or missing_metadata or force_sync:
            # Need to fetch from CLI
            try:
                global_log("Executing session list --format json...")
                proc = await self._create_subprocess(
                    [
                        self.opencode_cmd,
                        "session",
                        "list",
                        "--format",
                        "json",
                    ],
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=self.working_dir.replace("\\", "/"),
                )
                stdout, stderr = await proc.communicate()
                raw_content = stdout.decode().strip()

                if not raw_content:
                    parsed_sessions = []
                else:
                    # Find start of JSON array
                    json_start = raw_content.find("[")
                    if json_start != -1:
                        try:
                            parsed_sessions = json.loads(raw_content[json_start:])
                        except json.JSONDecodeError as e:
                            global_log(f"Failed to parse session list JSON: {e}")
                            parsed_sessions = []
                    else:
                        parsed_sessions = []

                global_log(f"CLI returned {len(parsed_sessions)} sessions")

                pinned_uuids = user_info.get("pinned_sessions", [])
                found_uuids = set()

                cli_sessions = []
                for sess in parsed_sessions:
                    u = sess.get("id")
                    if not u:
                        continue
                    found_uuids.add(u)

                    ts = sess.get("updated", sess.get("created", 0)) / 1000.0
                    time_str = dt_pkg.datetime.fromtimestamp(ts).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )

                    # Update metadata cache and ensure it's in user's session list
                    session_metadata[u] = {
                        "original_title": sess.get("title", "Unknown"),
                        "time": time_str,
                    }
                    
                    if u not in uuids:
                        uuids.append(u)
                        global_log(f"Auto-synced missing session {u} to user {user_id}")

                    current_tags = session_tags.get(u, [])
                    if tags:
                        if not all(tag in current_tags for tag in tags):
                            continue

                    title = custom_titles.get(u, sess.get("title", "Unknown"))

                    cli_sessions.append(
                        {
                            "uuid": u,
                            "title": title,
                            "time": time_str,
                            "active": (u == user_info.get("active_session")),
                            "pinned": (u in pinned_uuids),
                            "tags": current_tags,
                            "model": session_metadata[u].get(
                                "model"
                            ),  # Include model
                            "workspace": self.get_session_workspace(user_id, u),
                        }
                    )

                # Update user_data with new metadata
                self.user_data[user_id]["session_metadata"] = session_metadata
                self.user_data[user_id]["sessions"] = uuids

                self._save_user_data()
                all_sessions = list(cli_sessions)

                # If we have local sessions NOT in cli_sessions (e.g. older ones), we should probably add them from cache
                cached_ids = set(session_metadata.keys())
                cli_ids = {s["uuid"] for s in cli_sessions}

                for u in uuids:
                    if u not in cli_ids:
                        meta = session_metadata.get(
                            u, {"original_title": "Unknown Chat", "time": "Unknown"}
                        )
                        # Check tags filter
                        current_tags = session_tags.get(u, [])
                        if tags:
                            if not all(tag in current_tags for tag in tags):
                                continue

                        all_sessions.append(
                            {
                                "uuid": u,
                                "title": custom_titles.get(
                                    u, meta.get("original_title", "Unknown Chat")
                                ),
                                "time": meta.get("time", "Unknown"),
                                "active": (u == user_info.get("active_session")),
                                "pinned": (u in pinned_uuids),
                                "tags": current_tags,
                                "model": meta.get("model"),
                                "workspace": self.get_session_workspace(user_id, u),
                            }
                        )

                # Sort combined list by time descending
                all_sessions.sort(key=lambda x: x.get("time", ""), reverse=True)
            except Exception as e:
                global_log(
                    f"Error in get_user_sessions (fetching): {str(e)}", level="ERROR"
                )
                return {"pinned": [], "history": [], "total_unpinned": 0}

        else:
            # All metadata cached, build from cache
            pinned_uuids = user_info.get("pinned_sessions", [])
            for u in uuids:
                meta = session_metadata.get(
                    u, {"original_title": "Unknown", "time": "Unknown"}
                )

                # Check tags filter
                current_tags = session_tags.get(u, [])
                if tags:
                    if not all(tag in current_tags for tag in tags):
                        continue

                title = custom_titles.get(u, meta.get("original_title", "Unknown"))

                all_sessions.append(
                    {
                        "uuid": u,
                        "title": title,
                        "time": meta.get("time", "Unknown"),
                        "active": (u == user_info.get("active_session")),
                        "pinned": (u in pinned_uuids),
                        "tags": current_tags,
                        "model": meta.get("model"),
                        "workspace": self.get_session_workspace(user_id, u),
                    }
                )

            all_sessions.sort(key=lambda x: x.get("time", ""), reverse=True)

        global_log(f"Processing grouping for {len(all_sessions)} sessions")
        # --- Grouping Logic: Display them as one (the latest fork) ---
        # ... rest of function ...

        def get_root(u):
            """Find the root session UUID for a given session."""
            visited = set()
            curr = u
            while (
                curr in session_forks
                and session_forks[curr].get("parent")
                and curr not in visited
            ):
                visited.add(curr)
                curr = session_forks[curr]["parent"]
            return curr

        # Map root -> latest session in that group found in all_sessions
        # all_sessions is already ordered by time (newest first) because of [::-1]
        grouped_sessions = []
        seen_roots = set()

        for sess in all_sessions:
            root_uuid = get_root(sess["uuid"])
            if root_uuid not in seen_roots:
                grouped_sessions.append(sess)
                seen_roots.add(root_uuid)
            else:
                # If any fork in the group is active, the latest one shows it
                if sess["active"]:
                    for gs in grouped_sessions:
                        if get_root(gs["uuid"]) == root_uuid:
                            gs["has_active_fork"] = True
                            break

        # Common Pagination Logic
        pinned = [s for s in grouped_sessions if s["pinned"]]
        unpinned = [s for s in grouped_sessions if not s["pinned"]]

        total_unpinned = len(unpinned)

        if limit is not None:
            paged_unpinned = unpinned[offset : offset + limit]
        else:
            paged_unpinned = unpinned[offset:]

        return {
            "pinned": pinned if offset == 0 else [],
            "history": paged_unpinned,
            "total_unpinned": total_unpinned,
        }

    async def search_sessions(self, user_id: str, query: str) -> List[Dict]:
        sessions_data = await self.get_user_sessions(user_id)
        if not query:
            return sessions_data.get("pinned", []) + sessions_data.get("history", [])

        all_sessions = sessions_data.get("pinned", []) + sessions_data.get(
            "history", []
        )
        if not all_sessions:
            return []

        query = query.lower()
        results = []

        for sess in all_sessions:
            match = False
            # Check title
            if query in sess.get("title", "").lower():
                match = True

            if not match:
                # Check messages and attachments by exporting
                try:
                    msgs_data = await self.get_session_messages(sess["uuid"])
                    for msg in msgs_data.get("messages", []):
                        if query in msg.get("content", "").lower():
                            match = True
                            break
                except:
                    pass

            if match:
                results.append(sess)

        return results

    async def get_session_messages(
        self, session_uuid: str, limit: Optional[int] = None, offset: int = 0
    ) -> Dict:
        try:
            global_log(f"Exporting session {session_uuid} for messages...")
            proc = await self._create_subprocess(
                [self.opencode_cmd, "export", session_uuid],
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.working_dir.replace("\\", "/"),
            )
            stdout, stderr = await proc.communicate()
            content = stdout.decode().strip()

            # OpenCode export output starts with "Exporting session: ..."
            # We need to find the JSON start securely
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if not json_match:
                global_log(f"No JSON found in export output: {content[:100]}...")
                return {"messages": [], "total": 0}

            try:
                data = json.loads(json_match.group(0))
            except json.JSONDecodeError as e:
                global_log(f"Failed to parse session messages JSON: {e}")
                return {"messages": [], "total": 0}
            all_messages = data.get("messages", [])
            total = len(all_messages)

            if limit is not None:
                start = max(0, total - offset - limit)
                end = max(0, total - offset)
                messages_to_process = all_messages[start:end]
            else:
                start = 0
                messages_to_process = all_messages

            messages = []
            for idx, msg in enumerate(messages_to_process):
                role = msg.get("info", {}).get("role", "user")

                parts = msg.get("parts", [])
                text_parts = []
                for p in parts:
                    if p.get("type") == "text":
                        text_parts.append(p.get("text", ""))
                    elif p.get("type") == "reasoning":
                        text_parts.append(
                            f"[Thinking]\n{p.get('text', '')}\n[/Thinking]"
                        )

                content_text = "\n".join(text_parts).strip()
                if not content_text:
                    continue

                messages.append(
                    {
                        "role": "user" if role == "user" else "bot",
                        "content": content_text,
                        "raw_index": start + idx,
                    }
                )
            return {"messages": messages, "total": total}
        except Exception as e:
            print(f"Error loading session messages: {str(e)}")
            return {"messages": [], "total": 0}

    async def switch_session(self, user_id: str, uuid: str) -> bool:
        if user_id not in self.user_data:
            return False
            
        user_info = self.user_data[user_id]
        
        # More permissive switch: if it's in our metadata or we just found it
        if uuid in user_info.get("sessions", []) or uuid in user_info.get("session_metadata", {}):
            user_info["active_session"] = uuid
            if uuid not in user_info.setdefault("sessions", []):
                user_info["sessions"].append(uuid)
            self._save_user_data()
            return True
            
        # Last resort: check if it exists in CLI
        try:
            proc = await self._create_subprocess(
                [self.opencode_cmd, "session", "list", "--format", "json"],
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.working_dir.replace("\\", "/"),
            )
            stdout, _ = await proc.communicate()
            sessions = json.loads(stdout.decode())
            if any(s.get("id") == uuid for s in sessions):
                user_info["active_session"] = uuid
                if uuid not in user_info.setdefault("sessions", []):
                    user_info["sessions"].append(uuid)
                self._save_user_data()
                return True
        except:
            pass

        return False

    async def clone_session(
        self, user_id: str, original_uuid: str, message_index: int
    ) -> Optional[str]:
        """
        Clone a session up to a certain message index.
        Returns the new session UUID if successful.
        """
        if (
            user_id not in self.user_data
            or original_uuid not in self.user_data[user_id]["sessions"]
        ):
            return None

        try:
            if message_index == -1:
                # We want to start a new session but linked to this tree
                user_info = self.user_data[user_id]
                user_info["active_session"] = None  # Force new session in CLI

                # Store pending info to apply to the NEXT session created
                user_info["pending_fork"] = {
                    "parent": original_uuid,
                    "fork_point": -1,
                    "title": user_info.get("custom_titles", {}).get(original_uuid),
                    "tags": list(
                        user_info.get("session_tags", {}).get(original_uuid, [])
                    ),
                    "tools": list(
                        user_info.get("session_tools", {}).get(original_uuid, [])
                    ),
                }

                self._save_user_data()
                return "pending"  # Frontend will handle this

            # For specific index, we export, slice, and import
            global_log(f"Cloning session {original_uuid} at index {message_index}...")
            proc = await self._create_subprocess(
                [self.opencode_cmd, "export", original_uuid],
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.working_dir.replace("\\", "/"),
            )
            stdout, stderr = await proc.communicate()
            content = stdout.decode().strip()

            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if not json_match:
                return None

            try:
                data = json.loads(json_match.group(0))
            except json.JSONDecodeError as e:
                global_log(f"Failed to parse clone session JSON: {e}")
                return None
            if "messages" in data:
                data["messages"] = data["messages"][: message_index + 1]

            # Save to a temporary file for import
            temp_file = os.path.join(
                self.working_dir, f"temp_clone_{uuid.uuid4().hex}.json"
            )
            with open(temp_file, "w") as f:
                json.dump(data, f)

            try:
                proc = await self._create_subprocess(
                    [self.opencode_cmd, "import", temp_file.replace("\\", "/")],
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=self.working_dir.replace("\\", "/"),
                )
                stdout, stderr = await proc.communicate()
                output = stdout.decode().strip()

                # OpenCode import usually prints the new session ID
                # We need to extract it
                new_uuid_match = re.search(r"ses_[a-zA-Z0-9]+", output)
                if not new_uuid_match:
                    # Fallback: check latest session
                    new_uuid = await self._get_latest_session_uuid()
                else:
                    new_uuid = new_uuid_match.group(0)

                if new_uuid and new_uuid != original_uuid:
                    user_info = self.user_data[user_id]
                    if new_uuid not in user_info["sessions"]:
                        user_info["sessions"].append(new_uuid)

                    if "session_forks" not in user_info:
                        user_info["session_forks"] = {}
                    user_info["session_forks"][new_uuid] = {
                        "parent": original_uuid,
                        "fork_point": message_index,
                    }

                    # Inherit title and tags
                    orig_title = user_info.get("custom_titles", {}).get(original_uuid)
                    if orig_title:
                        if "custom_titles" not in user_info:
                            user_info["custom_titles"] = {}
                        user_info["custom_titles"][new_uuid] = f"{orig_title} (Fork)"

                    orig_tags = user_info.get("session_tags", {}).get(original_uuid)
                    if orig_tags:
                        if "session_tags" not in user_info:
                            user_info["session_tags"] = {}
                        user_info["session_tags"][new_uuid] = list(orig_tags)

                    self._save_user_data()
                    return new_uuid
            finally:
                if os.path.exists(temp_file):
                    os.remove(temp_file)

            return None
        except Exception as e:
            print(f"Error cloning session: {str(e)}")
            return None

    def get_session_forks(
        self, user_id: str, session_uuid: str
    ) -> Dict[int, List[str]]:
        """
        Get all forks related to this session, organized by fork point.
        Returns a dict: { message_index: [uuid1, uuid2, ...] }
        """
        if user_id not in self.user_data:
            return {}
        user_info = self.user_data[user_id]
        forks_info = user_info.get("session_forks", {})

        fork_map = {}

        def add_to_map(index, uid):
            if index not in fork_map:
                fork_map[index] = []
            if uid not in fork_map[index]:
                fork_map[index].append(uid)

        # Current session's parent and fork point (if any)
        my_info = forks_info.get(session_uuid)
        parent_uuid = my_info["parent"] if my_info else None
        my_fork_point = my_info["fork_point"] if my_info else None

        # 1. Any children of the current session
        for u, info in forks_info.items():
            if info["parent"] == session_uuid:
                add_to_map(info["fork_point"], u)

        # 2. If we have a parent, we are a fork at 'my_fork_point'
        # The parent is a "branch" at that point, and so are our siblings
        if parent_uuid:
            add_to_map(my_fork_point, parent_uuid)
            for u, info in forks_info.items():
                if (
                    u != session_uuid
                    and info["parent"] == parent_uuid
                    and info["fork_point"] == my_fork_point
                ):
                    add_to_map(my_fork_point, u)

        return fork_map

    def get_fork_graph(self, user_id: str) -> Dict[str, Dict]:
        """Get the full fork graph for all sessions of a user."""
        if user_id not in self.user_data:
            return {}
        user_info = self.user_data[user_id]
        forks_info = user_info.get("session_forks", {})
        custom_titles = user_info.get("custom_titles", {})
        session_metadata = user_info.get("session_metadata", {})
        sessions = user_info.get("sessions", [])

        graph = {}
        for uuid in sessions:
            info = forks_info.get(uuid, {})
            meta = session_metadata.get(uuid, {})
            title = custom_titles.get(uuid, meta.get("original_title", "Untitled Chat"))

            graph[uuid] = {
                "parent": info.get("parent"),
                "fork_point": info.get("fork_point"),
                "title": title,
            }
        return graph

    async def sync_session_updates(
        self,
        user_id: str,
        session_uuid: str,
        title: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ):
        """Sync title/tags across all related forks."""
        if user_id not in self.user_data:
            return
        user_info = self.user_data[user_id]
        forks_info = user_info.get("session_forks", {})

        # Find the root of the tree or just collect all related
        related_uuids = {session_uuid}

        # Simple iterative search to find all connected nodes in the fork tree
        changed = True
        while changed:
            changed = False
            for u, info in forks_info.items():
                if u in related_uuids and info["parent"] not in related_uuids:
                    related_uuids.add(info["parent"])
                    changed = True
                if info["parent"] in related_uuids and u not in related_uuids:
                    related_uuids.add(u)
                    changed = True

        # Apply updates
        for u in related_uuids:
            if title is not None:
                if "custom_titles" not in user_info:
                    user_info["custom_titles"] = {}
                user_info["custom_titles"][u] = title
            if tags is not None:
                if "session_tags" not in user_info:
                    user_info["session_tags"] = {}
                user_info["session_tags"][u] = tags

        self._save_user_data()

    async def new_session(self, user_id: str):
        self.user_data.setdefault(user_id, {})["active_session"] = None
        self.user_data[user_id].pop("pending_fork", None)
        self._save_user_data()

    async def delete_specific_session(self, user_id: str, uuid: str) -> bool:
        if (
            user_id not in self.user_data
            or uuid not in self.user_data[user_id]["sessions"]
        ):
            return False

        user_info = self.user_data[user_id]
        forks_info = user_info.get("session_forks", {})

        # Find all related sessions in the tree
        related_uuids = {uuid}
        changed = True
        while changed:
            changed = False
            for u, info in forks_info.items():
                parent = info.get("parent")
                if u in related_uuids and parent and parent not in related_uuids:
                    related_uuids.add(parent)
                    changed = True
                if parent in related_uuids and u not in related_uuids:
                    related_uuids.add(u)
                    changed = True

        success = True
        for target_uuid in list(related_uuids):
            try:
                # 1. Check if any OTHER user still has this session
                is_tracked_by_others = False
                for other_user_id, other_user_info in self.user_data.items():
                    if other_user_id == user_id:
                        continue
                    if target_uuid in other_user_info.get("sessions", []):
                        is_tracked_by_others = True
                        break

                # 2. Only delete from CLI if no other users are tracking it
                if not is_tracked_by_others:
                    await (
                        await self._create_subprocess(
                            [self.opencode_cmd, "session", "delete", target_uuid],
                            cwd=self.working_dir.replace("\\", "/"),
                        )
                    ).communicate()

                # 3. Cleanup local tracking
                if target_uuid in user_info["sessions"]:
                    user_info["sessions"].remove(target_uuid)

                if user_info.get("active_session") == target_uuid:
                    user_info["active_session"] = None

                if (
                    "session_metadata" in user_info
                    and target_uuid in user_info["session_metadata"]
                ):
                    del user_info["session_metadata"][target_uuid]

                if (
                    "custom_titles" in user_info
                    and target_uuid in user_info["custom_titles"]
                ):
                    del user_info["custom_titles"][target_uuid]

                if (
                    "session_tags" in user_info
                    and target_uuid in user_info["session_tags"]
                ):
                    del user_info["session_tags"][target_uuid]

                if (
                    "session_forks" in user_info
                    and target_uuid in user_info["session_forks"]
                ):
                    del user_info["session_forks"][target_uuid]

            except Exception as e:
                global_log(
                    f"Error deleting session {target_uuid}: {str(e)}", level="ERROR"
                )
                success = False

        self._save_user_data()
        return success

    async def clear_all_session_tags(self) -> int:
        """Clear session_tags for all users."""
        count = 0
        for user_id in self.user_data:
            if "session_tags" in self.user_data[user_id]:
                count += len(self.user_data[user_id]["session_tags"])
                self.user_data[user_id]["session_tags"] = {}
        self._save_user_data()
        return count

    async def share_session(
        self, user_id: str, session_uuid: str, target_username: str, user_manager: Any
    ) -> bool:
        """
        Share a session with another user.
        Fails silently if target_username does not exist.
        """
        # 1. Verify user_id has access to session_uuid
        if user_id not in self.user_data or session_uuid not in self.user_data[
            user_id
        ].get("sessions", []):
            return False

        # 2. Verify target_username exists via UserManager
        if target_username not in user_manager.users:
            return False

        # 3. Add session_uuid to target_username's session list in user_data
        if target_username not in self.user_data:
            self.user_data[target_username] = {
                "active_session": None,
                "sessions": [],
                "session_tools": {},
                "pending_tools": [],
                "pinned_sessions": [],
                "session_metadata": {},
                "settings": {
                    "show_mic": True,
                    "interactive_mode": True,
                    "copy_formatted": False,
                },
            }

        target_info = self.user_data[target_username]
        if "sessions" not in target_info:
            target_info["sessions"] = []
        if session_uuid not in target_info["sessions"]:
            target_info["sessions"].append(session_uuid)

        # 4. Copy custom_titles, session_tags, session_metadata, and session_tools to the target user
        source_info = self.user_data[user_id]

        if (
            "custom_titles" in source_info
            and session_uuid in source_info["custom_titles"]
        ):
            target_info.setdefault("custom_titles", {})[session_uuid] = source_info[
                "custom_titles"
            ][session_uuid]

        if (
            "session_tags" in source_info
            and session_uuid in source_info["session_tags"]
        ):
            target_info.setdefault("session_tags", {})[session_uuid] = list(
                source_info["session_tags"][session_uuid]
            )

        if (
            "session_metadata" in source_info
            and session_uuid in source_info["session_metadata"]
        ):
            target_info.setdefault("session_metadata", {})[session_uuid] = dict(
                source_info["session_metadata"][session_uuid]
            )

        if (
            "session_tools" in source_info
            and session_uuid in source_info["session_tools"]
        ):
            target_info.setdefault("session_tools", {})[session_uuid] = list(
                source_info["session_tools"][session_uuid]
            )

        # 5. Save user_sessions.json
        self._save_user_data()
        return True

    async def reset_chat(self, user_id: str) -> str:
        uuid = self.user_data.get(user_id, {}).get("active_session")
        if uuid:
            if await self.delete_specific_session(user_id, uuid):
                return "Conversation reset."
            return "Error resetting."
        return "No active session."
