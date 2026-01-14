import json
import os
import re
import asyncio
import shutil
from typing import Optional, List, Dict, AsyncGenerator
from app.core.patterns import PATTERNS

FALLBACK_MODELS = {
    "gemini-3-pro-preview": "gemini-3-flash-preview",
    "gemini-2.5-pro": "gemini-2.5-flash",
    "gemini-1.5-pro": "gemini-1.5-flash"
}

class GeminiAgent:
    def __init__(self, model: str = "gemini-2.5-flash", working_dir: Optional[str] = None):
        self.model_name = model
        self.working_dir = working_dir or os.getcwd()
        self.session_file = os.path.join(self.working_dir, "user_sessions.json")
        self.gemini_cmd = shutil.which("gemini") or "gemini"
        self.user_data = self._load_user_data()
        self.yolo_mode = False

    def _load_user_data(self) -> Dict:
        if os.path.exists(self.session_file):
            try:
                with open(self.session_file, "r") as f:
                    data = json.load(f)
                    if not data: return {}
                    # Migration for old flat format
                    if isinstance(next(iter(data.values())), str):
                        return {uid: {"active_session": suid, "sessions": [suid], "session_tools": {}} for uid, suid in data.items()}
                    # Ensure all entries have the expected keys
                    for uid in data:
                        if "sessions" not in data[uid]:
                            data[uid]["sessions"] = []
                        if "active_session" not in data[uid]:
                            data[uid]["active_session"] = None
                        if "session_tools" not in data[uid]:
                            data[uid]["session_tools"] = {}
                        if "pending_tools" not in data[uid]:
                            data[uid]["pending_tools"] = []
                    return data
            except: return {}
        return {}

    def _save_user_data(self):
        with open(self.session_file, "w") as f: json.dump(self.user_data, f, indent=2)

    def get_session_tools(self, user_id: str, session_uuid: str) -> List[str]:
        user_info = self.user_data.get(user_id)
        if not user_info: return []
        if session_uuid == "pending":
            return user_info.get("pending_tools", [])
        return user_info.get("session_tools", {}).get(session_uuid, [])

    def set_session_tools(self, user_id: str, session_uuid: str, tools: List[str]):
        if user_id not in self.user_data:
            self.user_data[user_id] = {"active_session": None, "sessions": [], "session_tools": {}, "pending_tools": []}
        
        if session_uuid == "pending":
            self.user_data[user_id]["pending_tools"] = tools
        else:
            if "session_tools" not in self.user_data[user_id]:
                self.user_data[user_id]["session_tools"] = {}
            self.user_data[user_id]["session_tools"][session_uuid] = tools
        self._save_user_data()

    def list_patterns(self) -> List[str]:
        return sorted([k for k in PATTERNS.keys() if k != "__explanations__"])

    async def apply_pattern(self, user_id: str, pattern_name: str, input_text: str, model: Optional[str] = None, file_path: Optional[str] = None) -> str:
        system = PATTERNS.get(pattern_name)
        if not system: return f"Error: Pattern '{pattern_name}' not found."
        return await self.generate_response(user_id, f"{system}\n\nUSER INPUT:\n{input_text}", model=model, file_path=file_path)

    def _filter_errors(self, err: str) -> str:
        err = re.sub(r".*?\[DEP0151\] DeprecationWarning:.*?(\n|$)", "", err)
        err = re.sub(r".*?Default \"index\" lookups for the main are deprecated for ES modules..*?(\n|$)", "", err)
        return "\n".join([s for s in err.splitlines() if s.strip()]).strip()

    async def _get_latest_session_uuid(self) -> Optional[str]:
        try:
            proc = await asyncio.create_subprocess_exec(self.gemini_cmd, "--list-sessions", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, cwd=self.working_dir)
            stdout, stderr = await proc.communicate()
            content = (stdout.decode() + stderr.decode())
            matches = re.findall(r"\\[([a-fA-F0-9-]{36})\\]", content)
            return matches[-1] if matches else None
        except: return None

    async def generate_response_stream(self, user_id: str, prompt: str, model: Optional[str] = None, file_path: Optional[str] = None) -> AsyncGenerator[Dict, None]:
        def log_debug(msg):
            try:
                with open("agent_debug.log", "a", encoding="utf-8") as f:
                    f.write(f"[{user_id}] {msg}\n")
            except: pass

        if user_id not in self.user_data:
            self.user_data[user_id] = {"active_session": None, "sessions": [], "session_tools": {}, "pending_tools": []}
        else:
            if "sessions" not in self.user_data[user_id]:
                self.user_data[user_id]["sessions"] = []
            if "active_session" not in self.user_data[user_id]:
                self.user_data[user_id]["active_session"] = None
            if "session_tools" not in self.user_data[user_id]:
                self.user_data[user_id]["session_tools"] = {}
            if "pending_tools" not in self.user_data[user_id]:
                self.user_data[user_id]["pending_tools"] = []

        session_uuid = self.user_data[user_id].get("active_session")
        current_model = model or self.model_name
        
        attempt = 0
        max_attempts = 2
        
        while attempt < max_attempts:
            attempt += 1
            # Get enabled tools for this session
            enabled_tools = []
            if session_uuid:
                enabled_tools = self.get_session_tools(user_id, session_uuid)
            else:
                enabled_tools = self.get_session_tools(user_id, "pending")
            
            args = [self.gemini_cmd]
            args.extend(["--output-format", "stream-json"])
            
            if enabled_tools:
                args.extend(["--allowed-tools", ",".join(enabled_tools)])
            else:
                args.extend(["--allowed-tools", "none"])
            
            args.extend(["--approval-mode", "default"])

            if self.yolo_mode: args.append("--yolo")
            if session_uuid: args.extend(["--resume", session_uuid])
            if current_model: args.extend(["--model", current_model])
            args.extend(["--include-directories", self.working_dir])
            if file_path: args.append(f"@{file_path}")
            
            log_debug(f"Attempt {attempt}: Running command {" ".join(args)}")
            
            should_fallback = False
            proc = None
            try:
                proc = await asyncio.create_subprocess_exec(
                    *args, 
                    stdin=asyncio.subprocess.PIPE, 
                    stdout=asyncio.subprocess.PIPE, 
                    stderr=asyncio.subprocess.PIPE, 
                    cwd=self.working_dir
                )
                
                if prompt:
                    proc.stdin.write(prompt.encode('utf-8'))
                    await proc.stdin.drain()
                    proc.stdin.close()
                
                # To prevent deadlock, read stderr concurrently
                async def read_stderr(stderr_pipe):
                    try:
                        data = await stderr_pipe.read()
                        return data.decode()
                    except Exception as e: 
                        log_debug(f"Error reading stderr: {str(e)}")
                        return ""

                stderr_task = asyncio.create_task(read_stderr(proc.stderr))

                # Read stdout line by line
                while True:
                    line = await proc.stdout.readline()
                    if not line:
                        break
                    line_str = line.decode().strip()
                    if not line_str: continue
                    
                    # Detect 429 Capacity Error
                    if ("429" in line_str or "No capacity available" in line_str) and attempt < max_attempts:
                        fallback = FALLBACK_MODELS.get(current_model)
                        if fallback:
                            log_debug(f"Capacity error detected, falling back to {fallback}")
                            yield {"type": "model_switch", "old_model": current_model, "new_model": fallback}
                            yield {"type": "message", "role": "assistant", "content": f"\n\n[Model {current_model} is currently busy. Switching to {fallback} for a faster response...]\n\n"}
                            current_model = fallback
                            should_fallback = True
                            break # Break stdout loop to retry
                    
                    try:
                        data = json.loads(line_str)
                        yield data
                    except json.JSONDecodeError:
                        yield {"type": "raw", "content": line_str}
                
                if should_fallback:
                    try:
                        if proc.returncode is None:
                            proc.terminate()
                            await proc.wait()
                    except: pass
                    continue # Retry while loop with fallback model

                await proc.wait()
                stderr_output = await stderr_task
                log_debug(f"Process exited with code {proc.returncode}")
                
                if proc.returncode != 0:
                    err = self._filter_errors(stderr_output.strip())
                    log_debug(f"Error output: {err}")
                    
                    # Also check stderr for 429
                    if ("429" in err or "No capacity available" in err) and attempt < max_attempts:
                        fallback = FALLBACK_MODELS.get(current_model)
                        if fallback:
                            yield {"type": "message", "role": "assistant", "content": f"\n\n[Model {current_model} is currently busy. Switching to {fallback}...]\n\n"}
                            current_model = fallback
                            continue # Retry while loop

                    if session_uuid and any(x in err.lower() for x in ["no session", "not found", "invalid session"]):
                        self.user_data[user_id]["active_session"] = None
                        yield {"type": "error", "content": f"Session error: {err}"}
                    else:
                        yield {"type": "error", "content": f"Error: {err}"}
                
                break # Success, exit retry loop

            except Exception as e:
                log_debug(f"Exception in stream: {str(e)}")
                yield {"type": "error", "content": f"Exception: {str(e)}"}
                break
            finally:
                # Capture session ID if this was a new session
                if not session_uuid:
                    log_debug("New session detected, attempting to capture ID")
                    await asyncio.sleep(0.5)
                    new_uuid = await self._get_latest_session_uuid()
                    if new_uuid:
                        log_debug(f"Captured new session ID: {new_uuid}")
                        self.user_data[user_id]["active_session"] = new_uuid
                        if new_uuid not in self.user_data[user_id]["sessions"]:
                            self.user_data[user_id]["sessions"].append(new_uuid)
                        
                        pending = self.user_data[user_id].get("pending_tools", [])
                        if pending:
                            if "session_tools" not in self.user_data[user_id]:
                                self.user_data[user_id]["session_tools"] = {}
                            self.user_data[user_id]["session_tools"][new_uuid] = pending
                            self.user_data[user_id]["pending_tools"] = []
                            
                        self._save_user_data()
                
                if proc and proc.returncode is None:
                    try:
                        proc.terminate()
                        await proc.wait()
                    except: pass

    async def generate_response(self, user_id: str, prompt: str, model: Optional[str] = None, file_path: Optional[str] = None) -> str:
        full_response = ""
        async for chunk in self.generate_response_stream(user_id, prompt, model, file_path):
            if chunk.get("type") == "message":
                full_response += chunk.get("content", "")
            elif chunk.get("type") == "error":
                full_response += f"\n[Error: {chunk.get('content')}]"
            elif chunk.get("type") == "raw":
                 full_response += chunk.get("content", "") + "\n"
        return full_response.strip()

    async def get_user_sessions(self, user_id: str) -> List[Dict]:
        if user_id not in self.user_data:
            self.user_data[user_id] = {"active_session": None, "sessions": [], "session_tools": {}, "pending_tools": []}
            self._save_user_data()
            
        user_info = self.user_data[user_id]
        uuids = user_info.get("sessions", [])
        if not uuids: return []
        
        try:
            proc = await asyncio.create_subprocess_exec(self.gemini_cmd, "--list-sessions", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, cwd=self.working_dir)
            stdout, stderr = await proc.communicate()
            content = self._filter_errors(stdout.decode() + stderr.decode())
            pattern = r"^\s+\d+\.\s+(?P<title>.*?)\s+\((?P<time>.*?)\)\s+\[(?P<uuid>[a-fA-F0-9-]{36})\]"
            matches = re.finditer(pattern, content, re.MULTILINE)
            sessions = []
            for m in matches:
                info = m.groupdict()
                # Only show sessions that are explicitly in this user's list
                if info["uuid"] in uuids:
                    info["active"] = (info["uuid"] == user_info.get("active_session"))
                    sessions.append(info)
            
            return sessions[::-1]
        except: 
            return [{"uuid": u, "title": "Unknown", "time": "Unknown", "active": (u == user_info.get("active_session"))} for u in uuids]

    async def get_session_messages(self, session_uuid: str, limit: Optional[int] = None, offset: int = 0) -> List[Dict]:
        try:
            # Try to find the session file
            uuid_start = session_uuid.split('-')[0]
            
            # Find the .gemini/tmp directory
            home = os.path.expanduser("~")
            gemini_tmp_base = os.path.join(home, ".gemini", "tmp")
            
            if not os.path.exists(gemini_tmp_base):
                return []

            import glob
            # Search in all project hash folders under .gemini/tmp/
            search_path = os.path.join(gemini_tmp_base, "*", "chats", f"*{uuid_start}*.json")
            files = glob.glob(search_path)
            
            if not files:
                return []
            
            # Use the most recently modified file if multiple match
            files.sort(key=os.path.getmtime, reverse=True)
            with open(files[0], 'r', encoding='utf-8') as f:
                data = json.load(f)
                all_messages = data.get("messages", [])
                
                # Apply pagination: get latest messages first
                total = len(all_messages)
                if limit is not None:
                    start = max(0, total - offset - limit)
                    end = max(0, total - offset)
                    messages_to_process = all_messages[start:end]
                else:
                    messages_to_process = all_messages
                
                messages = []
                for msg in messages_to_process:
                    content = msg.get("content", "")
                    if not content or content.strip() == "":
                        continue
                    messages.append({
                        "role": "user" if msg.get("type") == "user" else "bot",
                        "content": content
                    })
                return messages
        except Exception as e:
            print(f"Error loading session messages for {session_uuid}: {str(e)}")
            return []

    async def switch_session(self, user_id: str, uuid: str) -> bool:
        if user_id in self.user_data and uuid in self.user_data[user_id]["sessions"]:
            self.user_data[user_id]["active_session"] = uuid
            self._save_user_data()
            return True
        return False

    async def new_session(self, user_id: str):
        self.user_data.setdefault(user_id, {})["active_session"] = None
        self._save_user_data()

    async def delete_specific_session(self, user_id: str, uuid: str) -> bool:
        if user_id in self.user_data and uuid in self.user_data[user_id]["sessions"]:
            try:
                await (await asyncio.create_subprocess_exec(self.gemini_cmd, "--delete-session", uuid, cwd=self.working_dir)).communicate()
                self.user_data[user_id]["sessions"].remove(uuid)
                if self.user_data[user_id]["active_session"] == uuid: self.user_data[user_id]["active_session"] = None
                self._save_user_data()
                return True
            except: return False
        return False

    async def reset_chat(self, user_id: str) -> str:
        uuid = self.user_data.get(user_id, {}).get("active_session")
        if uuid:
            if await self.delete_specific_session(user_id, uuid): return "Conversation reset."
            return "Error resetting."
        return "No active session."