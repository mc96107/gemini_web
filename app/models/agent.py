import re
from typing import List, Optional
from pydantic import BaseModel

class AgentModel(BaseModel):
    name: str
    description: str
    category: str
    folder_name: str
    prompt: str
    type: str = "FunctionAgent"
    children: List[str] = []
    parent: Optional[str] = None
    used_by: List[str] = []

    def to_markdown(self) -> str:
        """Serializes the agent to AGENT.md format with YAML frontmatter."""
        lines = [
            "---",
            f"name: {self.name}",
            f"description: {self.description}",
            f"type: {self.type}"
        ]
        
        if self.children:
            # Format: [[child1], [child2]]
            children_str = ", ".join([f"[{child}]" for child in self.children])
            lines.append(f"children: [{children_str}]")
            
        if self.parent:
            lines.append(f"parent: [[{self.parent}]]")
            
        if self.used_by:
            # Format: [[user1], [user2]]
            used_by_str = ", ".join([f"[{user}]" for user in self.used_by])
            lines.append(f"used_by: [{used_by_str}]")
            
        lines.append("---")
        lines.append(self.prompt)
        
        return "\n".join(lines)

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
        
        # Helper to extract [[path]] from string
        # Matches [path] inside the string. 
        # For [[path]], it matches [path] (inner).
        # For [[path1], [path2]], it matches [path1] and [path2].
        def extract_paths(value_str: str) -> List[str]:
            return re.findall(r"\[([^\[\]]+)\]", value_str)

        children = []
        if "children" in metadata:
            children = extract_paths(metadata["children"])
            
        used_by = []
        if "used_by" in metadata:
            used_by = extract_paths(metadata["used_by"])
            
        parent = None
        if "parent" in metadata:
            paths = extract_paths(metadata["parent"])
            if paths:
                parent = paths[0]
        
        return cls(
            name=metadata.get("name", folder_name),
            description=metadata.get("description", ""),
            category=category,
            folder_name=folder_name,
            prompt=prompt,
            type=metadata.get("type", "FunctionAgent"),
            children=children,
            parent=parent,
            used_by=used_by
        )