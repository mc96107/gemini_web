import os
import shutil
import glob
import re
from typing import List, Optional
from app.core import config
from app.models.agent import AgentModel

class AgentManager:
    def __init__(self):
        self.base_dir = config.AGENT_BASE_DIR
        self.project_root = os.getcwd()
        self._ensure_base_dir()

    def _ensure_base_dir(self):
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir, exist_ok=True)

    def _get_agent_path(self, category: str, folder_name: str) -> str:
        return os.path.join(self.base_dir, category, folder_name, "AGENT.md")

    def _get_root_agent_path(self) -> str:
        return os.path.join(self.project_root, "AGENT.md")

    def list_agents(self) -> List[AgentModel]:
        """Lists all agents by recursively scanning the base directory."""
        agents = []
        # Search for all AGENT.md files
        pattern = os.path.join(self.base_dir, "**", "AGENT.md")
        files = glob.glob(pattern, recursive=True)
        
        for file_path in files:
            try:
                # Extract category and folder_name from path
                # Structure: base_dir/category/folder_name/AGENT.md
                rel_path = os.path.relpath(file_path, self.base_dir)
                parts = rel_path.split(os.sep)
                
                if len(parts) >= 3:
                    category = parts[0]
                    folder_name = parts[1]
                    
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        
                    agent = AgentModel.from_markdown(content, category, folder_name)
                    agents.append(agent)
            except Exception as e:
                print(f"Error loading agent from {file_path}: {e}")
                continue
                
        return agents

    def get_agent(self, category: str, folder_name: str) -> Optional[AgentModel]:
        """Reads a specific agent."""
        path = self._get_agent_path(category, folder_name)
        if not os.path.exists(path):
            return None
            
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            return AgentModel.from_markdown(content, category, folder_name)
        except Exception as e:
            print(f"Error reading agent {category}/{folder_name}: {e}")
            return None

    def save_agent(self, agent: AgentModel) -> bool:
        """Saves or updates an agent."""
        # Sanitize check (basic)
        if ".." in agent.category or ".." in agent.folder_name:
            return False
            
        dir_path = os.path.join(self.base_dir, agent.category, agent.folder_name)
        os.makedirs(dir_path, exist_ok=True)
        
        file_path = os.path.join(dir_path, "AGENT.md")
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(agent.to_markdown())
            return True
        except Exception as e:
            print(f"Error saving agent {agent.name}: {e}")
            return False

    def delete_agent(self, category: str, folder_name: str) -> bool:
        """Deletes an agent folder."""
        if ".." in category or ".." in folder_name:
            return False
            
        dir_path = os.path.join(self.base_dir, category, folder_name)
        if os.path.exists(dir_path):
            try:
                shutil.rmtree(dir_path)
                
                # Check if category folder is empty, if so delete it
                cat_path = os.path.join(self.base_dir, category)
                if os.path.exists(cat_path) and not os.listdir(cat_path):
                    os.rmdir(cat_path)
                    
                return True
            except Exception as e:
                print(f"Error deleting agent {category}/{folder_name}: {e}")
                return False
        return False

    def get_root_orchestrator(self) -> Optional[AgentModel]:
        """Reads the root AGENT.md file."""
        path = self._get_root_agent_path()
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            return AgentModel.from_markdown(content, "root", "root")
        except Exception as e:
            print(f"Error reading root orchestrator: {e}")
            return None

    def save_root_orchestrator(self, agent: AgentModel) -> bool:
        """Saves the root AGENT.md file."""
        path = self._get_root_agent_path()
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(agent.to_markdown())
            return True
        except Exception as e:
            print(f"Error saving root orchestrator: {e}")
            return False

    def initialize_root_orchestrator(self):
        """Creates a default root AGENT.md if it doesn't exist."""
        path = self._get_root_agent_path()
        if not os.path.exists(path):
            root_agent = AgentModel(
                name="Root Orchestrator",
                description="The central AI agent that manages sub-agents.",
                category="root",
                folder_name="root",
                type="Orchestrator",
                prompt="You are the Root Orchestrator. You manage several sub-agents to fulfill user requests."
            )
            self.save_root_orchestrator(root_agent)

    def set_agent_enabled(self, category: str, folder_name: str, enabled: bool) -> bool:
        """Links or unlinks a sub-agent to the root orchestrator."""
        root = self.get_root_orchestrator()
        if not root:
            self.initialize_root_orchestrator()
            root = self.get_root_orchestrator()
            
        agent = self.get_agent(category, folder_name)
        if not agent:
            return False
            
        # Determine relative path from project root to agent's AGENT.md
        agent_abs_path = self._get_agent_path(category, folder_name)
        agent_rel_path = os.path.relpath(agent_abs_path, self.project_root).replace(os.sep, '/')
        
        root_rel_path = "AGENT.md" # Always at project root
        
        if enabled:
            # Link TO root
            if agent_rel_path not in root.children:
                root.children.append(agent_rel_path)
            # Link FROM agent
            agent.parent = root_rel_path
            # used_by tracking
            if root_rel_path not in agent.used_by:
                agent.used_by.append(root_rel_path)
        else:
            # Unlink FROM root
            if agent_rel_path in root.children:
                root.children.remove(agent_rel_path)
            # Unlink FROM agent
            agent.parent = None
            # used_by tracking
            if root_rel_path in agent.used_by:
                agent.used_by.remove(root_rel_path)
                
        # Atomic-ish update
        success_root = self.save_root_orchestrator(root)
        success_agent = self.save_agent(agent)
        
        return success_root and success_agent

    def validate_orchestration(self) -> List[str]:
        """Validates that all enabled agents are referenced in the root prompt."""
        root = self.get_root_orchestrator()
        if not root:
            return []
            
        warnings = []
        for child_path in root.children:
            # Try to load the child to get its name
            # path is relative to project root
            # e.g. data/agents/functions/fabric/AGENT.md
            full_path = os.path.join(self.project_root, child_path)
            if not os.path.exists(full_path):
                warnings.append(f"Referenced agent at {child_path} does not exist.")
                continue
                
            try:
                # We need to extract category and folder_name from child_path
                # child_path is relative to project root. 
                # AgentManager works relative to base_dir (data/agents)
                # Let's find relative path from base_dir to child_path
                rel_to_base = os.path.relpath(full_path, self.base_dir)
                parts = rel_to_base.split(os.sep)
                if len(parts) >= 2:
                    category = parts[0]
                    folder_name = parts[1]
                    child_agent = self.get_agent(category, folder_name)
                    if child_agent:
                        # Check if name or slug or path is in prompt
                        if child_agent.name not in root.prompt and child_agent.folder_name not in root.prompt and child_path not in root.prompt:
                            warnings.append(f"Agent '{child_agent.name}' is enabled but not referenced in the Orchestrator's prompt.")
            except Exception:
                continue
                
        return warnings

    def initialize_defaults(self):
        """Initializes default agents if they don't exist."""
        # functions/fabric/AGENT.md
        fabric_path = self._get_agent_path("functions", "fabric")
        if not os.path.exists(fabric_path):
            fabric_agent = AgentModel(
                name="Fabric Agent",
                description="Bridge to Fabric patterns and prompts.",
                category="functions",
                folder_name="fabric",
                prompt="You are a Fabric orchestrator. You can use any of the available patterns to process input."
            )
            self.save_agent(fabric_agent)
        
        self.initialize_root_orchestrator()