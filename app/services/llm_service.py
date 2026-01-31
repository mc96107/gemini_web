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
from typing import Optional, List, Dict, AsyncGenerator
from app.core.patterns import PATTERNS
from app.core import config

FALLBACK_MODELS = {
    "gemini-3-pro-preview": "gemini-3-flash-preview",
    "gemini-2.5-pro": "gemini-2.5-flash",
    "gemini-1.5-pro": "gemini-1.5-flash"
}

CAPACITY_KEYWORDS = ["429", "capacity", "quota", "exhausted", "rate limit"]

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
    except: pass

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
            for line in iter(self.pipe.readline, b''):
                self.loop.call_soon_threadsafe(self.queue.put_nowait, line)
        finally:
            self.loop.call_soon_threadsafe(self.queue.put_nowait, None)

    async def readline(self):
        line = await self.queue.get()
        return line if line is not None else b''

class ThreadedProcess:
    """Minimal wrapper for subprocess.Popen to match asyncio.subprocess.Process."""
    def __init__(self, popen_proc, loop):
        self.proc = popen_proc
        self.loop = loop
        self.stdout = ThreadedStreamReader(popen_proc.stdout, loop) if popen_proc.stdout else None
        self.stderr = ThreadedStreamReader(popen_proc.stderr, loop) if popen_proc.stderr else None
        self.stdin = popen_proc.stdin # synchronous writing usually works ok if not blocked
        self.returncode = None

    async def wait(self):
        while self.proc.poll() is None:
            await asyncio.sleep(0.1)
        self.returncode = self.proc.returncode
        return self.returncode

    async def communicate(self, input=None):
        if input:
            self.proc.stdin.write(input)
            self.proc.stdin.flush()
        
        stdout_content = b''
        stderr_content = b''
        
        if self.stdout:
            while True:
                line = await self.stdout.readline()
                if not line: break
                stdout_content += line
        
        if self.stderr:
            while True:
                line = await self.stderr.readline()
                if not line: break
                stderr_content += line
                
        await self.wait()
        return stdout_content, stderr_content

    def terminate(self):
        self.proc.terminate()

class GeminiAgent:
    def __init__(self, model: str = "gemini-2.5-flash", working_dir: Optional[str] = None):
        self.model_name = model
        self.working_dir = working_dir or os.getcwd()
        self.session_file = os.path.join(self.working_dir, "user_sessions.json")
        self.gemini_cmd = shutil.which("gemini") or "gemini"
        self.user_data = self._load_user_data()
        self.yolo_mode = False
        self.active_tasks: Dict[str, asyncio.Task] = {}

    def _load_user_data(self) -> Dict:
        if os.path.exists(self.session_file):
            try:
                with open(self.session_file, "r") as f:
                    data = json.load(f)
                    if not data: return {}
                    if isinstance(next(iter(data.values())), str):
                        return {uid: {"active_session": suid, "sessions": [suid], "session_tools": {}} for uid, suid in data.items()}
                    for uid in data:
                        if "sessions" not in data[uid]: data[uid]["sessions"] = []
                        if "active_session" not in data[uid]: data[uid]["active_session"] = None
                        if "session_tools" not in data[uid]: data[uid]["session_tools"] = {}
                        if "session_tags" not in data[uid]: data[uid]["session_tags"] = {}
                        if "pending_tools" not in data[uid]: data[uid]["pending_tools"] = []
                        if "pinned_sessions" not in data[uid]: data[uid]["pinned_sessions"] = []
                        if "session_metadata" not in data[uid]: data[uid]["session_metadata"] = {}
                    return data
            except: return {}
        return {}

    def _save_user_data(self):
        with open(self.session_file, "w") as f: json.dump(self.user_data, f, indent=2)

    async def _create_subprocess(self, args, **kwargs):
        try:
            # Try the standard asyncio approach first
            return await asyncio.create_subprocess_exec(*args, **kwargs)
        except NotImplementedError:
            if sys.platform == 'win32':
                # Robust fallback for Windows (works on ALL loops)
                global_log("asyncio subprocess not implemented, using ThreadedProcess fallback", level="INFO")
                from subprocess import Popen, PIPE
                loop = asyncio.get_running_loop()
                
                # Adapt kwargs for Popen
                popen_kwargs = {
                    "stdout": kwargs.get("stdout", PIPE),
                    "stderr": kwargs.get("stderr", PIPE),
                    "stdin": kwargs.get("stdin", PIPE),
                    "cwd": kwargs.get("cwd"),
                    "env": kwargs.get("env"),
                    "bufsize": 0 # Unbuffered for streaming
                }
                
                # If it's a list, we might need list2cmdline for shell consistency, 
                # but Popen handles lists well on Windows if NOT using shell=True.
                proc = Popen(args, **popen_kwargs)
                return ThreadedProcess(proc, loop)
            else:
                raise

    def toggle_pin(self, user_id: str, session_uuid: str) -> bool:
        if user_id not in self.user_data:
            self.user_data[user_id] = {"active_session": None, "sessions": [], "session_tools": {}, "pending_tools": [], "pinned_sessions": [], "session_metadata": {}}
        
        user_info = self.user_data[user_id]
        if "pinned_sessions" not in user_info: user_info["pinned_sessions"] = []
        
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
        if not user_info: return []
        if session_uuid == "pending": return user_info.get("pending_tools", [])
        return user_info.get("session_tools", {}).get(session_uuid, [])

    def set_session_tools(self, user_id: str, session_uuid: str, tools: List[str]):
        if user_id not in self.user_data:
            self.user_data[user_id] = {"active_session": None, "sessions": [], "session_tools": {}, "pending_tools": [], "session_metadata": {}}
        if session_uuid == "pending":
            self.user_data[user_id]["pending_tools"] = tools
        else:
            if "session_tools" not in self.user_data[user_id]: self.user_data[user_id]["session_tools"] = {}
            self.user_data[user_id]["session_tools"][session_uuid] = tools
        self._save_user_data()

    def list_patterns(self) -> List[str]:
        return sorted([k for k in PATTERNS.keys() if k != "__explanations__"])

    async def apply_pattern(self, user_id: str, pattern_name: str, input_text: str, model: Optional[str] = None, file_paths: Optional[List[str]] = None) -> str:
        # Check if it's a custom prompt file
        prompts_dir = os.path.join(self.working_dir, "prompts")
        if os.path.exists(prompts_dir):
            # Try exact match first
            custom_path = os.path.join(prompts_dir, pattern_name)
            if os.path.exists(custom_path):
                try:
                    with open(custom_path, "r", encoding="utf-8") as f:
                        system = f.read()
                    return await self.generate_response(user_id, f"{system}\n\nUSER INPUT:\n{input_text}", model=model, file_paths=file_paths)
                except Exception as e:
                    return f"Error reading custom prompt '{pattern_name}': {str(e)}"

        # Fallback to system patterns
        system = PATTERNS.get(pattern_name)
        if not system: 
            # Try removing colon if present (common issue)
            clean_name = pattern_name.rstrip(":")
            system = PATTERNS.get(clean_name)
            
        if not system: return f"Error: Pattern '{pattern_name}' not found."
        return await self.generate_response(user_id, f"{system}\n\nUSER INPUT:\n{input_text}", model=model, file_paths=file_paths)

    def _filter_errors(self, err: str) -> str:
        err = re.sub(r".*?\[DEP0151\] DeprecationWarning:.*?(\n|$)", "", err)
        err = re.sub(r".*?Default \"index\" lookups for the main are deprecated for ES modules..*?(\n|$)", "", err)
        return "\n".join([s for s in err.splitlines() if s.strip()]).strip()

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
            global_log("Executing --list-sessions...")
            proc = await self._create_subprocess([self.gemini_cmd, "--list-sessions"], stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, cwd=self.working_dir)
            stdout, stderr = await proc.communicate()
            content = (stdout.decode() + stderr.decode())
            matches = re.findall(r"\x20\[([a-fA-F0-9-]{36})\]", content)
            res = matches[-1] if matches else None
            global_log(f"Latest session ID found: {res}")
            return res
        except Exception as e:
            global_log(f"Error in _get_latest_session_uuid: {str(e)}")
            return None

    async def generate_response_stream(self, user_id: str, prompt: str, model: Optional[str] = None, file_paths: Optional[List[str]] = None, resume_session: Optional[str] = "AUTO") -> AsyncGenerator[Dict, None]:
        def log_debug(msg): global_log(f"[{user_id}] {msg}", level="DEBUG")

        if user_id not in self.user_data:
            self.user_data[user_id] = {"active_session": None, "sessions": [], "session_tools": {}, "pending_tools": [], "session_metadata": {}}
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

        current_model = model or self.model_name
        
        attempt = 0
        max_attempts = 2
        
        while attempt < max_attempts:
            attempt += 1
            enabled_tools = self.get_session_tools(user_id, session_uuid or "pending")
            log_debug(f"Enabled tools for this run: {enabled_tools}")
            
            args = [self.gemini_cmd, "--output-format", "stream-json"]
            args.extend(["--allowed-tools", ",".join(enabled_tools) if enabled_tools else "none"])
            args.extend(["--approval-mode", "default"])
            if self.yolo_mode: args.append("--yolo")
            if session_uuid: args.extend(["--resume", session_uuid])
            if current_model: args.extend(["--model", current_model])
            args.extend(["--include-directories", self.working_dir])
            if file_paths:
                for fp in file_paths:
                    args.append(f"@{fp}")
            
            log_debug(f"Attempt {attempt}: Running command {' '.join(args)}")
            
            should_fallback = False
            proc = None
            stderr_buffer = []
            try:
                proc = await self._create_subprocess(
                    args, 
                    stdin=asyncio.subprocess.PIPE, 
                    stdout=asyncio.subprocess.PIPE, 
                    stderr=asyncio.subprocess.PIPE, 
                    cwd=self.working_dir
                )
                
                if prompt:
                    log_debug("Writing prompt to stdin...")
                    async def write_to_stdin(proc, data):
                        if hasattr(proc.stdin, 'drain'): # asyncio.StreamWriter
                            proc.stdin.write(data)
                            await proc.stdin.drain()
                            proc.stdin.close()
                        else: # Synchronous pipe from Popen
                            def sync_write():
                                proc.stdin.write(data)
                                proc.stdin.flush()
                                proc.stdin.close()
                            await asyncio.to_thread(sync_write)
                    
                    await write_to_stdin(proc, prompt.encode('utf-8'))
                
                async def capture_stderr(pipe):
                    while True:
                        line = await pipe.readline()
                        if not line: break
                        line_str = line.decode(errors='replace').strip()
                        log_debug(f"STDERR: {line_str}")
                        stderr_buffer.append(line_str)
                
                stderr_task = asyncio.create_task(capture_stderr(proc.stderr))

                log_debug("Starting to read stdout")
                while True:
                    line = await proc.stdout.readline()
                    if not line:
                        log_debug("Stdout closed (EOF)")
                        break
                    line_str = line.decode(errors='replace').strip()
                    if not line_str: continue
                    
                    log_debug(f"Received line ({len(line_str)} chars)")
                    try:
                        data = json.loads(line_str)
                        
                        # Truncate large tool outputs
                        if data.get("type") == "tool_result" and "output" in data:
                            output = data["output"]
                            threshold = 20 * 1024 # 20KB
                            if len(output) > threshold:
                                truncated = output[:threshold]
                                # Save full output to a file
                                try:
                                    fname = f"output_{uuid.uuid4().hex}.txt"
                                    fpath = os.path.join(config.UPLOAD_DIR, fname)
                                    with open(fpath, "w", encoding="utf-8") as f:
                                        f.write(output)
                                    data["full_output_path"] = f"/uploads/{fname}"
                                    data["output"] = f"{truncated}\n\n[Output truncated. Full output available below.]"
                                    log_debug(f"Truncated tool output and saved to {fpath}")
                                except Exception as e:
                                    log_debug(f"Error saving full output: {str(e)}")
                                    data["output"] = f"{truncated}\n\n[Output truncated. Error saving full version.]"
                                
                                log_debug(f"Truncated tool output from {len(output)} to {len(data['output'])} bytes")

                        # Capture session ID
                        if data.get("type") == "init" and data.get("session_id"):
                            new_id = data["session_id"]
                            if not session_uuid:
                                log_debug(f"Captured session ID: {new_id}")
                                self.user_data[user_id]["active_session"] = new_id
                                if new_id not in self.user_data[user_id]["sessions"]:
                                    self.user_data[user_id]["sessions"].append(new_id)
                                
                                # Promote pending tools to this new session
                                pending = self.user_data[user_id].get("pending_tools", [])
                                if pending:
                                    if "session_tools" not in self.user_data[user_id]:
                                        self.user_data[user_id]["session_tools"] = {}
                                    self.user_data[user_id]["session_tools"][new_id] = pending
                                    self.user_data[user_id]["pending_tools"] = []
                                    log_debug(f"Promoted pending tools to session {new_id}")

                                # Handle pending fork
                                pending_fork = self.user_data[user_id].get("pending_fork")
                                if pending_fork:
                                    if "session_forks" not in self.user_data[user_id]:
                                        self.user_data[user_id]["session_forks"] = {}
                                    self.user_data[user_id]["session_forks"][new_id] = {
                                        "parent": pending_fork["parent"],
                                        "fork_point": pending_fork["fork_point"]
                                    }
                                    if pending_fork.get("title"):
                                        if "custom_titles" not in self.user_data[user_id]:
                                            self.user_data[user_id]["custom_titles"] = {}
                                        self.user_data[user_id]["custom_titles"][new_id] = pending_fork["title"]
                                    if pending_fork.get("tags"):
                                        if "session_tags" not in self.user_data[user_id]:
                                            self.user_data[user_id]["session_tags"] = {}
                                        self.user_data[user_id]["session_tags"][new_id] = pending_fork["tags"]
                                    
                                    if pending_fork.get("tools"):
                                        if "session_tools" not in self.user_data[user_id]:
                                            self.user_data[user_id]["session_tools"] = {}
                                        self.user_data[user_id]["session_tools"][new_id] = pending_fork["tools"]
                                    
                                    del self.user_data[user_id]["pending_fork"]
                                    log_debug(f"Applied pending fork info to session {new_id}")

                                self._save_user_data()
                                session_uuid = new_id
                        
                        # Check for capacity error in JSON chunks
                        content_to_check = str(data).lower()
                        if any(k in content_to_check for k in CAPACITY_KEYWORDS) and attempt < max_attempts:
                            fallback = FALLBACK_MODELS.get(current_model)
                            if fallback:
                                log_debug(f"Capacity error detected in stdout, falling back to {fallback}")
                                yield {"type": "model_switch", "old_model": current_model, "new_model": fallback}
                                yield {"type": "message", "role": "assistant", "content": f"\n\n[Model {current_model} is currently busy or quota exhausted. Switching to {fallback} for a faster response...]\n\n"}
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
                    except: pass
                    continue 

                await proc.wait()
                await stderr_task
                log_debug(f"Process exited with code {proc.returncode}")
                
                # Check for capacity error in stderr if process failed
                if proc.returncode != 0 and not should_fallback:
                    err_text = "\n".join(stderr_buffer).lower()
                    if any(k in err_text for k in CAPACITY_KEYWORDS) and attempt < max_attempts:
                        fallback = FALLBACK_MODELS.get(current_model)
                        if fallback:
                            log_debug(f"Capacity error detected in stderr, falling back to {fallback}")
                            yield {"type": "model_switch", "old_model": current_model, "new_model": fallback}
                            yield {"type": "message", "role": "assistant", "content": f"\n\n[Model {current_model} is currently busy or quota exhausted. Switching to {fallback}...]\n\n"}
                            current_model = fallback
                            continue 

                    # If not a capacity error, yield generic exit code error
                    yield {"type": "error", "content": f"Exit code {proc.returncode}"}
                
                break 

            except Exception as e:
                log_debug(f"Exception in stream: {repr(e)}")
                yield {"type": "error", "content": f"Exception: {repr(e)}"}
                break
            finally:
                if proc and proc.returncode is None:
                    try:
                        proc.terminate()
                        await proc.wait()
                    except: pass

    async def generate_response(self, user_id: str, prompt: str, model: Optional[str] = None, file_paths: Optional[List[str]] = None, resume_session: Optional[str] = "AUTO") -> str:
        full_response = ""
        async for chunk in self.generate_response_stream(user_id, prompt, model, file_paths, resume_session=resume_session):
            if chunk.get("type") == "message":
                full_response += chunk.get("content", "")
            elif chunk.get("type") == "error":
                full_response += f"\n[Error: {chunk.get('content')}]"
            elif chunk.get("type") == "raw":
                 full_response += chunk.get("content", "") + "\n"
        return full_response.strip()

    async def update_session_title(self, user_id: str, uuid: str, new_title: str) -> bool:
        if user_id in self.user_data and uuid in self.user_data[user_id]["sessions"]:
            if "custom_titles" not in self.user_data[user_id]:
                self.user_data[user_id]["custom_titles"] = {}
            self.user_data[user_id]["custom_titles"][uuid] = new_title
            self._save_user_data()
            return True
        return False

    async def update_session_tags(self, user_id: str, uuid: str, tags: List[str]) -> bool:
        if user_id in self.user_data and uuid in self.user_data[user_id]["sessions"]:
            if "session_tags" not in self.user_data[user_id]:
                self.user_data[user_id]["session_tags"] = {}
            self.user_data[user_id]["session_tags"][uuid] = tags
            self._save_user_data()
            return True
        return False

    def get_unique_tags(self, user_id: str) -> List[str]:
        if user_id not in self.user_data: return []
        user_info = self.user_data[user_id]
        all_tags = set()
        for tags in user_info.get("session_tags", {}).values():
            for t in tags:
                all_tags.add(t)
        return sorted(list(all_tags))

    def is_user_session(self, user_id: str, session_uuid: str) -> bool:
        """Check if a session belongs to a user without filtering for sidebar."""
        if user_id not in self.user_data: return False
        return session_uuid in self.user_data[user_id].get("sessions", [])

    async def get_user_sessions(self, user_id: str, limit: Optional[int] = None, offset: int = 0, tags: Optional[List[str]] = None) -> List[Dict]:
        if user_id not in self.user_data:
            self.user_data[user_id] = {"active_session": None, "sessions": [], "session_tools": {}, "pending_tools": [], "pinned_sessions": [], "session_metadata": {}}
            self._save_user_data()
        
        user_info = self.user_data[user_id]
        uuids = user_info.get("sessions", [])
        custom_titles = user_info.get("custom_titles", {})
        session_tags = user_info.get("session_tags", {})
        session_metadata = user_info.get("session_metadata", {})
        session_forks = user_info.get("session_forks", {})
        
        if not uuids: return []

        # Check if we have metadata for all sessions
        missing_metadata = [u for u in uuids if u not in session_metadata]
        
        all_sessions = []
        
        if not missing_metadata:
            # All metadata cached, build from cache
            pinned_uuids = user_info.get("pinned_sessions", [])
            for u in uuids:
                meta = session_metadata.get(u, {"original_title": "Unknown", "time": "Unknown"})
                
                # Check tags filter
                current_tags = session_tags.get(u, [])
                if tags:
                    if not all(tag in current_tags for tag in tags):
                        continue
                        
                title = custom_titles.get(u, meta.get("original_title", "Unknown"))
                
                all_sessions.append({
                    "uuid": u,
                    "title": title,
                    "time": meta.get("time", "Unknown"),
                    "active": (u == user_info.get("active_session")),
                    "pinned": (u in pinned_uuids),
                    "tags": current_tags
                })
            
            all_sessions = all_sessions[::-1]
            
        else:
            # Need to fetch from CLI
            try:
                global_log("Executing --list-sessions...")
                proc = await self._create_subprocess([self.gemini_cmd, "--list-sessions"], stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, cwd=self.working_dir)
                stdout, stderr = await proc.communicate()
                raw_content = stdout.decode() + stderr.decode()
                content = self._filter_errors(raw_content)
                
                pattern = r"^\s*\d+\.\s+(?P<title>.*?)\s+\((?P<time>.*?)\)\s+\[(?P<uuid>[a-fA-F0-9-]{36})\]"
                matches = list(re.finditer(pattern, content, re.MULTILINE))
                
                pinned_uuids = user_info.get("pinned_sessions", [])
                found_uuids = set()
                
                cli_sessions = []
                for m in matches:
                    info = m.groupdict()
                    u = info["uuid"]
                    found_uuids.add(u)
                    
                    # ONLY update metadata cache if the session belongs to this user
                    if u in uuids:
                        session_metadata[u] = {
                            "original_title": info["title"],
                            "time": info["time"]
                        }
                        
                        current_tags = session_tags.get(u, [])
                        if tags:
                            if not all(tag in current_tags for tag in tags):
                                continue
                                
                        title = custom_titles.get(u, info["title"])
                        
                        cli_sessions.append({
                            "uuid": u,
                            "title": title,
                            "time": info["time"],
                            "active": (u == user_info.get("active_session")),
                            "pinned": (u in pinned_uuids),
                            "tags": current_tags
                        })
                
                # Update user_data with new metadata
                self.user_data[user_id]["session_metadata"] = session_metadata
                
                # Sync sessions list
                valid_uuids = [u for u in uuids if u in found_uuids]
                if len(valid_uuids) != len(uuids):
                    self.user_data[user_id]["sessions"] = valid_uuids
                    for u in uuids:
                        if u not in valid_uuids:
                            session_metadata.pop(u, None)
                            custom_titles.pop(u, None)
                            session_tags.pop(u, None)
                            if u in pinned_uuids: pinned_uuids.remove(u)
                    
                    self.user_data[user_id]["session_metadata"] = session_metadata
                    self.user_data[user_id]["custom_titles"] = custom_titles
                    self.user_data[user_id]["session_tags"] = session_tags
                    self.user_data[user_id]["pinned_sessions"] = pinned_uuids
                
                self._save_user_data()
                all_sessions = cli_sessions
                all_sessions = all_sessions[::-1]
                
            except Exception as e:
                global_log(f"Error in get_user_sessions (fetching): {str(e)}")
                return []
        # --- Grouping Logic: Display them as one (the latest fork) ---
        
        def get_root(u):
            """Find the root session UUID for a given session."""
            visited = set()
            curr = u
            while curr in session_forks and session_forks[curr].get("parent") and curr not in visited:
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
                # If the current active session is a fork that is NOT the latest, 
                # we still might want to show it? 
                # The user said "display them as one" and "opening a chat start by displaying the latest fork".
                # This implies we only show the most recent fork in the sidebar.
                # If the user IS currently in an older fork, maybe we should show that one instead?
                # Let's stick to showing the latest, but if the active session is in this group, 
                # ensure the "active" badge or state is represented if possible.
                if sess["active"]:
                    # Update the already added group entry to be "active" if any member is active
                    for gs in grouped_sessions:
                        if get_root(gs["uuid"]) == root_uuid:
                            gs["has_active_fork"] = True
                            break

        # Common Pagination Logic
        pinned = [s for s in grouped_sessions if s["pinned"]]
        unpinned = [s for s in grouped_sessions if not s["pinned"]]
        
        if limit is not None:
            paged_unpinned = unpinned[offset : offset + limit]
        else:
            paged_unpinned = unpinned[offset:]
            
        return pinned + paged_unpinned

    async def search_sessions(self, user_id: str, query: str) -> List[Dict]:
        if not query: return await self.get_user_sessions(user_id)
        
        user_sessions = await self.get_user_sessions(user_id) # Get basic info for all user sessions
        if not user_sessions: return []
        
        query = query.lower()
        results = []
        
        home = os.path.expanduser("~")
        gemini_tmp_base = os.path.join(home, ".gemini", "tmp")
        
        for sess in user_sessions:
            match = False
            # Check title
            if query in sess.get("title", "").lower():
                match = True
            
            if not match:
                # Check messages and attachments in the JSON file
                uuid_start = sess["uuid"].split('-')[0]
                import glob
                search_path = os.path.join(gemini_tmp_base, "*", "chats", f"*{uuid_start}*.json")
                files = glob.glob(search_path)
                if files:
                    try:
                        with open(files[0], 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            for msg in data.get("messages", []):
                                if query in msg.get("content", "").lower():
                                    match = True; break
                    except: pass
            
            if match:
                results.append(sess)
        
        return results

    async def get_session_messages(self, session_uuid: str, limit: Optional[int] = None, offset: int = 0) -> Dict:
        try:
            uuid_start = session_uuid.split('-')[0]
            home = os.path.expanduser("~")
            gemini_tmp_base = os.path.join(home, ".gemini", "tmp")
            if not os.path.exists(gemini_tmp_base): return {"messages": [], "total": 0}
            import glob
            search_path = os.path.join(gemini_tmp_base, "*", "chats", f"*{uuid_start}*.json")
            files = glob.glob(search_path)
            if not files: return {"messages": [], "total": 0}
            files.sort(key=os.path.getmtime, reverse=True)
            with open(files[0], 'r', encoding='utf-8') as f:
                data = json.load(f)
                all_messages = data.get("messages", [])
                total = len(all_messages)
                if limit is not None:
                    start = max(0, total - offset - limit); end = max(0, total - offset)
                    messages_to_process = all_messages[start:end]
                else: messages_to_process = all_messages
                messages = []
                for msg in messages_to_process:
                    content = msg.get("content", "")
                    if not content or content.strip() == "": continue
                    messages.append({"role": "user" if msg.get("type") == "user" else "bot", "content": content})
                return {"messages": messages, "total": total}
        except Exception as e:
            print(f"Error loading session messages: {str(e)}")
            return {"messages": [], "total": 0}

    async def switch_session(self, user_id: str, uuid: str) -> bool:
        if user_id in self.user_data and uuid in self.user_data[user_id]["sessions"]:
            self.user_data[user_id]["active_session"] = uuid
            self._save_user_data()
            return True
        return False

    async def clone_session(self, user_id: str, original_uuid: str, message_index: int) -> Optional[str]:
        """
        Clone a session up to a certain message index.
        Returns the new session UUID if successful.
        """
        if user_id not in self.user_data or original_uuid not in self.user_data[user_id]["sessions"]:
            return None

        try:
            if message_index == -1:
                # We want to start a new session but linked to this tree
                user_info = self.user_data[user_id]
                user_info["active_session"] = None # Force new session in CLI
                
                # Store pending info to apply to the NEXT session created
                user_info["pending_fork"] = {
                    "parent": original_uuid,
                    "fork_point": -1,
                    "title": user_info.get("custom_titles", {}).get(original_uuid),
                    "tags": list(user_info.get("session_tags", {}).get(original_uuid, [])),
                    "tools": list(user_info.get("session_tools", {}).get(original_uuid, []))
                }
                
                self._save_user_data()
                return "pending" # Frontend will handle this

            uuid_start = original_uuid.split('-')[0]
            home = os.path.expanduser("~")
            gemini_tmp_base = os.path.join(home, ".gemini", "tmp")
            import glob
            search_path = os.path.join(gemini_tmp_base, "*", "chats", f"*{uuid_start}*.json")
            files = glob.glob(search_path)
            if not files: return None
            files.sort(key=os.path.getmtime, reverse=True)
            
            with open(files[0], 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Truncate messages. message_index is 0-based.
            # If message_index is 5, we keep 0, 1, 2, 3, 4, 5 (total 6 messages)
            data["messages"] = data["messages"][:message_index + 1]
            
            # Generate new UUID
            new_uuid = str(uuid.uuid4())
            data["sessionId"] = new_uuid
            data["startTime"] = datetime.now(timezone.utc).isoformat()
            data["lastUpdated"] = data["startTime"]
            
            # Save to new file in the same directory as original
            original_dir = os.path.dirname(files[0])
            new_filename = f"session-{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H-%M')}-{new_uuid[:8]}.json"
            new_path = os.path.join(original_dir, new_filename)
            
            with open(new_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            # Update user_data
            user_info = self.user_data[user_id]
            user_info["sessions"].append(new_uuid)
            user_info["active_session"] = new_uuid
            
            # Inherit tags and title if they exist
            if "custom_titles" in user_info and original_uuid in user_info["custom_titles"]:
                user_info["custom_titles"][new_uuid] = user_info["custom_titles"][original_uuid]
            
            if "session_tags" in user_info and original_uuid in user_info["session_tags"]:
                user_info["session_tags"][new_uuid] = list(user_info["session_tags"][original_uuid])
            
            # Inherit tools
            if "session_tools" in user_info and original_uuid in user_info["session_tools"]:
                user_info["session_tools"][new_uuid] = list(user_info["session_tools"][original_uuid])
            
            # Track fork relationship
            if "session_forks" not in user_info:
                user_info["session_forks"] = {}
            user_info["session_forks"][new_uuid] = {
                "parent": original_uuid,
                "fork_point": message_index
            }
            
            # Also inherit metadata (original title etc)
            if "session_metadata" in user_info and original_uuid in user_info["session_metadata"]:
                user_info["session_metadata"][new_uuid] = dict(user_info["session_metadata"][original_uuid])
            
            self._save_user_data()
            return new_uuid
            
        except Exception as e:
            global_log(f"Error cloning session {original_uuid}: {str(e)}", level="ERROR")
            return None

    def get_session_forks(self, user_id: str, session_uuid: str) -> Dict[int, List[str]]:
        """
        Get all forks related to this session, organized by fork point.
        Returns a dict: { message_index: [uuid1, uuid2, ...] }
        """
        if user_id not in self.user_data: return {}
        user_info = self.user_data[user_id]
        forks_info = user_info.get("session_forks", {})
        
        fork_map = {}

        def add_to_map(index, uid):
            if index not in fork_map: fork_map[index] = []
            if uid not in fork_map[index]: fork_map[index].append(uid)

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
                if u != session_uuid and info["parent"] == parent_uuid and info["fork_point"] == my_fork_point:
                    add_to_map(my_fork_point, u)
            
        return fork_map

    def get_fork_graph(self, user_id: str) -> Dict[str, Dict]:
        """Get the full fork graph for all sessions of a user."""
        if user_id not in self.user_data: return {}
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
                "title": title
            }
        return graph

    async def sync_session_updates(self, user_id: str, session_uuid: str, title: Optional[str] = None, tags: Optional[List[str]] = None):
        """Sync title/tags across all related forks."""
        if user_id not in self.user_data: return
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
                if "custom_titles" not in user_info: user_info["custom_titles"] = {}
                user_info["custom_titles"][u] = title
            if tags is not None:
                if "session_tags" not in user_info: user_info["session_tags"] = {}
                user_info["session_tags"][u] = tags
                
        self._save_user_data()

    async def new_session(self, user_id: str):
        self.user_data.setdefault(user_id, {})["active_session"] = None
        self.user_data[user_id].pop("pending_fork", None)
        self._save_user_data()

    async def delete_specific_session(self, user_id: str, uuid: str) -> bool:
        if user_id not in self.user_data or uuid not in self.user_data[user_id]["sessions"]:
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
                # 1. Delete from CLI
                await (await self._create_subprocess([self.gemini_cmd, "--delete-session", target_uuid], cwd=self.working_dir)).communicate()
                
                # 2. Cleanup local tracking
                if target_uuid in user_info["sessions"]:
                    user_info["sessions"].remove(target_uuid)
                
                if user_info.get("active_session") == target_uuid:
                    user_info["active_session"] = None
                
                if "session_metadata" in user_info and target_uuid in user_info["session_metadata"]:
                    del user_info["session_metadata"][target_uuid]
                
                if "custom_titles" in user_info and target_uuid in user_info["custom_titles"]:
                    del user_info["custom_titles"][target_uuid]
                
                if "session_tags" in user_info and target_uuid in user_info["session_tags"]:
                    del user_info["session_tags"][target_uuid]
                
                if "session_forks" in user_info and target_uuid in user_info["session_forks"]:
                    del user_info["session_forks"][target_uuid]
                    
            except Exception as e:
                global_log(f"Error deleting session {target_uuid}: {str(e)}", level="ERROR")
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

    async def reset_chat(self, user_id: str) -> str:
        uuid = self.user_data.get(user_id, {}).get("active_session")
        if uuid:
            if await self.delete_specific_session(user_id, uuid): return "Conversation reset."
            return "Error resetting."
        return "No active session."