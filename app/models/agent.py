import re
from typing import List, Optional, Dict, Union
from pydantic import BaseModel

class AgentLink(BaseModel):
    path: str
    description: Optional[str] = None

class AgentModel(BaseModel):
    id: Optional[str] = None
    name: str
    description: str
    category: str
    folder_name: str
    prompt: str
    type: str = "FunctionAgent"
    children: List[AgentLink] = []
    uses: List[AgentLink] = []
    projects: List[AgentLink] = []
    skills: List[str] = []
    parent: Optional[str] = None
    used_by: List[str] = []

    def to_markdown(self) -> str:
        """Serializes the agent to AGENT.md format with YAML frontmatter."""
        lines = ["---"]
        if self.id:
            lines.append(f"id: {self.id}")
        lines.append(f"name: {self.name}")
        lines.append(f"description: {self.description}")
        lines.append(f"type: {self.type}")
        
        if self.skills:
            lines.append("skills:")
            for skill in self.skills:
                lines.append(f"  - {skill}")
        
        def add_link_list(key, items: List[AgentLink]):
            if items:
                lines.append(f"{key}:")
                for item in items:
                    line = f"  - [[{item.path}]]"
                    if item.description:
                        line += f" # {item.description}"
                    lines.append(line)
        
        add_link_list("children", self.children)
        add_link_list("uses", self.uses)
        add_link_list("projects", self.projects)
        
        if self.parent:
            lines.append(f"parent: [[{self.parent}]]")
            
        if self.used_by:
            lines.append("used_by:")
            for ub in self.used_by:
                lines.append(f"  - [[{ub}]]")
        
        lines.append("---")
        lines.append(self.prompt)
        
        return "\n".join(lines)

    @classmethod
    def from_markdown(cls, content: str, category: str, folder_name: str) -> "AgentModel":
        """Parses an AGENT.md content into an AgentModel."""
        # Split by frontmatter delimiters
        parts = content.split("---")
        
        if len(parts) < 3:
            # Fallback if no frontmatter
            return cls(
                name=folder_name,
                description="",
                category=category,
                folder_name=folder_name,
                prompt=content.strip()
            )
        
        frontmatter_raw = parts[1].strip()
        prompt = "---".join(parts[2:]).strip()
        
        # Robust parsing for multi-line YAML-ish fields
        metadata = {}
        current_key = None
        for line in frontmatter_raw.splitlines():
            stripped = line.strip()
            if not stripped: continue
            
            # Key: Value or Key: (start of list)
            if ":" in line and not stripped.startswith("-"):
                if ":" in stripped:
                    key, value = stripped.split(":", 1)
                    current_key = key.strip()
                    metadata[current_key] = value.strip()
                else:
                    current_key = stripped.replace(":", "").strip()
                    metadata[current_key] = ""
            # Continued list item or indented block
            elif current_key:
                metadata[current_key] += "\n" + line # Keep indentation for lists
        
        def parse_links(value_str: str) -> List[AgentLink]:
            links = []
            for line in value_str.splitlines():
                # Extract [[path]]
                path_match = re.search(r"\[\[(.*?)\]\]", line)
                if path_match:
                    path = path_match.group(1)
                    # Extract description after #
                    comment_match = re.search(r"#\s*(.*)", line)
                    description = comment_match.group(1).strip() if comment_match else None
                    links.append(AgentLink(path=path, description=description))
            return links

        def extract_simple_paths(value_str: str) -> List[str]:
            return [l.path for l in parse_links(value_str)]

        def parse_simple_list(value_str: str) -> List[str]:
            items = []
            for line in value_str.splitlines():
                stripped = line.strip()
                if stripped.startswith("- "):
                    items.append(stripped[2:].strip())
            return items

        return cls(
            id=metadata.get("id"),
            name=metadata.get("name", folder_name),
            description=metadata.get("description", ""),
            category=category,
            folder_name=folder_name,
            prompt=prompt,
            type=metadata.get("type", "FunctionAgent"),
            children=parse_links(metadata.get("children", "")),
            uses=parse_links(metadata.get("uses", "")),
            projects=parse_links(metadata.get("projects", "")),
            skills=parse_simple_list(metadata.get("skills", "")),
            parent=extract_simple_paths(metadata.get("parent", ""))[0] if extract_simple_paths(metadata.get("parent", "")) else None,
            used_by=extract_simple_paths(metadata.get("used_by", ""))
        )
