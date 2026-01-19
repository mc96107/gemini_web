import json
import os
import re
import asyncio
import shutil
import uuid
from datetime import datetime
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

    async def apply_pattern(self, user_id: str, pattern_name: str, input_text: str, model: Optional[str] = None, file_path: Optional[str] = None) -> str:
        system = PATTERNS.get(pattern_name)
        if not system: return f"Error: Pattern '{pattern_name}' not found."
        return await self.generate_response(user_id, f"{system}\n\nUSER INPUT:\n{input_text}", model=model, file_path=file_path)

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
            proc = await asyncio.create_subprocess_exec(self.gemini_cmd, "--list-sessions", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, cwd=self.working_dir)
            stdout, stderr = await proc.communicate()
            content = (stdout.decode() + stderr.decode())
            matches = re.findall(r"\x20\[([a-fA-F0-9-]{36})\]", content)
            res = matches[-1] if matches else None
            global_log(f"Latest session ID found: {res}")
            return res
        except Exception as e:
            global_log(f"Error in _get_latest_session_uuid: {str(e)}")
            return None

    async def generate_response_stream(self, user_id: str, prompt: str, model: Optional[str] = None, file_path: Optional[str] = None, resume_session: Optional[str] = "AUTO") -> AsyncGenerator[Dict, None]:
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
            if file_path: args.append(f"@{file_path}")
            
            log_debug(f"Attempt {attempt}: Running command {' '.join(args)}")
            
            should_fallback = False
            proc = None
            stderr_buffer = []
            try:
                proc = await asyncio.create_subprocess_exec(
                    *args, 
                    stdin=asyncio.subprocess.PIPE, 
                    stdout=asyncio.subprocess.PIPE, 
                    stderr=asyncio.subprocess.PIPE, 
                    cwd=self.working_dir
                )
                
                if prompt:
                    log_debug("Writing prompt to stdin...")
                    proc.stdin.write(prompt.encode('utf-8'))
                    await proc.stdin.drain()
                    proc.stdin.close()
                
                async def capture_stderr(pipe):
                    while True:
                        line = await pipe.readline()
                        if not line: break
                        line_str = line.decode().strip()
                        log_debug(f"STDERR: {line_str}")
                        stderr_buffer.append(line_str)
                
                stderr_task = asyncio.create_task(capture_stderr(proc.stderr))

                log_debug("Starting to read stdout")
                while True:
                    line = await proc.stdout.readline()
                    if not line:
                        log_debug("Stdout closed (EOF)")
                        break
                    line_str = line.decode().strip()
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
                log_debug(f"Exception in stream: {str(e)}")
                yield {"type": "error", "content": f"Exception: {str(e)}"}
                break
            finally:
                if proc and proc.returncode is None:
                    try:
                        proc.terminate()
                        await proc.wait()
                    except: pass

    async def generate_response(self, user_id: str, prompt: str, model: Optional[str] = None, file_path: Optional[str] = None, resume_session: Optional[str] = "AUTO") -> str:
        full_response = ""
        async for chunk in self.generate_response_stream(user_id, prompt, model, file_path, resume_session=resume_session):
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

    async def get_user_sessions(self, user_id: str, limit: Optional[int] = None, offset: int = 0, tags: Optional[List[str]] = None) -> List[Dict]:
        if user_id not in self.user_data:
            self.user_data[user_id] = {"active_session": None, "sessions": [], "session_tools": {}, "pending_tools": [], "pinned_sessions": [], "session_metadata": {}}
            self._save_user_data()
        
        user_info = self.user_data[user_id]
        uuids = user_info.get("sessions", [])
        custom_titles = user_info.get("custom_titles", {})
        session_tags = user_info.get("session_tags", {})
        session_metadata = user_info.get("session_metadata", {})
        
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
                proc = await asyncio.create_subprocess_exec(self.gemini_cmd, "--list-sessions", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, cwd=self.working_dir)
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
                global_log(f"Error fetching sessions for {user_id}: {e}", level="DEBUG")
                return []

        # Common Pagination Logic
        pinned = [s for s in all_sessions if s["pinned"]]
        unpinned = [s for s in all_sessions if not s["pinned"]]
        
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

    async def get_session_messages(self, session_uuid: str, limit: Optional[int] = None, offset: int = 0) -> List[Dict]:
        try:
            uuid_start = session_uuid.split('-')[0]
            home = os.path.expanduser("~")
            gemini_tmp_base = os.path.join(home, ".gemini", "tmp")
            if not os.path.exists(gemini_tmp_base): return []
            import glob
            search_path = os.path.join(gemini_tmp_base, "*", "chats", f"*{uuid_start}*.json")
            files = glob.glob(search_path)
            if not files: return []
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
                return messages
        except Exception as e:
            print(f"Error loading session messages: {str(e)}")
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
                
                # Cleanup metadata
                if "session_metadata" in self.user_data[user_id] and uuid in self.user_data[user_id]["session_metadata"]:
                    del self.user_data[user_id]["session_metadata"][uuid]
                
                self._save_user_data()
                return True
            except: return False
        return False

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