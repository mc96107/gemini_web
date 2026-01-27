import re
from typing import Optional
from pydantic import BaseModel

class AgentModel(BaseModel):
    name: str
    description: str
    category: str
    folder_name: str
    prompt: str

    def to_markdown(self) -> str:
        """Serializes the agent to AGENT.md format with YAML frontmatter."""
        return f"---\nname: {self.name}\ndescription: {self.description}\n---\n{self.prompt}"

    @classmethod
    def from_markdown(cls, content: str, category: str, folder_name: str) -> "AgentModel":
        """Parses an AGENT.md content into an AgentModel."""
        # Simple regex to extract YAML frontmatter
        # Matches:
        # ---
        # key: value
        # ---
        # content
        pattern = r"^---\s*\n(.*?)\n---\s*\n(.*)$"
        match = re.search(pattern, content, re.DOTALL | re.MULTILINE)
        
        if not match:
            # Fallback if no frontmatter
            return cls(
                name=folder_name,
                description="",
                category=category,
                folder_name=folder_name,
                prompt=content.strip()
            )
        
        frontmatter_raw = match.group(1)
        prompt = match.group(2).strip()
        
        metadata = {}
        for line in frontmatter_raw.splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                metadata[key.strip()] = value.strip()
        
        return cls(
            name=metadata.get("name", folder_name),
            description=metadata.get("description", ""),
            category=category,
            folder_name=folder_name,
            prompt=prompt
        )
