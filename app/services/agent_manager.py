import os
import shutil
import glob
from typing import List, Optional
from app.core import config
from app.models.agent import AgentModel

class AgentManager:
    def __init__(self):
        self.base_dir = config.AGENT_BASE_DIR
        self._ensure_base_dir()

    def _ensure_base_dir(self):
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir, exist_ok=True)

    def _get_agent_path(self, category: str, folder_name: str) -> str:
        return os.path.join(self.base_dir, category, folder_name, "AGENT.md")

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
