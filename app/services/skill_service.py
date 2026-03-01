import os
import re
import json
import asyncio
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
import subprocess
import logging

logger = logging.getLogger(__name__)


@dataclass
class Skill:
    name: str
    description: str
    content: str
    workspace_path: str
    keywords: List[str] = field(default_factory=list)
    execution_type: str = "context"  # "context" or "script"
    script_path: Optional[str] = None
    script_args: List[str] = field(default_factory=list)


class SkillService:
    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root
        self.skills_cache: Dict[str, Skill] = {}
        self._load_skills()

    def _get_skills_dir(self) -> str:
        return os.path.join(self.workspace_root, ".opencode", "skills")

    def _load_skills(self):
        """Load all skills from the workspace skills directory."""
        skills_dir = self._get_skills_dir()
        if not os.path.exists(skills_dir):
            logger.warning(f"Skills directory not found: {skills_dir}")
            return

        for skill_name in os.listdir(skills_dir):
            skill_path = os.path.join(skills_dir, skill_name)
            if not os.path.isdir(skill_path):
                continue

            skill_md = os.path.join(skill_path, "SKILL.md")
            if not os.path.exists(skill_md):
                continue

            try:
                with open(skill_md, "r", encoding="utf-8") as f:
                    content = f.read()

                skill = self._parse_skill(skill_name, skill_path, content)
                if skill:
                    self.skills_cache[skill_name] = skill
                    logger.info(f"Loaded skill: {skill_name}")
            except Exception as e:
                logger.error(f"Error loading skill {skill_name}: {e}")

    def _parse_skill(self, name: str, skill_path: str, content: str) -> Optional[Skill]:
        """Parse skill from SKILL.md content."""
        description = "Workspace Skill"
        execution_type = "context"
        script_path = None
        
        # Skill-specific keyword overrides for better detection
        skill_keywords = {
            'searxng-researcher': ['search', 'web', 'searxng', 'research', 'privacy', 'aggregated'],
            'search-email-archive': ['email', 'mail', 'archive', 'inbox'],
            'recoll-researcher': ['recoll', 'technical', 'search'],
            'daily-agenda-manager': ['agenda', 'calendar', 'meeting', 'schedule', 'today', 'tomorrow', 'daily'],
            'obsidian-rclone-saver': ['obsidian', 'save', 'export', 'note'],
            'boq-estimator': ['boq', 'bill', 'quantity', 'estimate', 'cost', 'pricing'],
            'crypto-finance-analyzer': ['crypto', 'nexo', 'cryptocurrency', 'portfolio', 'financial'],
            'loyalty-ratio-analyzer': ['loyalty', 'ratio', 'x coefficient', 'rebalancing'],
            'milestone-generator': ['milestone', 'calendar', 'ics', 'regenerate'],
            'team-manager': ['team', 'hr', 'leadership', 'coach', 'slii'],
            'technical-compliance-auditor': ['compliance', 'technical', 'fire', 'electrical', 'energy', 'e/m'],
            'content-distiller': ['content', 'distiller', 'fabric', 'summarize'],
            'high-precision-reviewer': ['review', 'precision', 'verify', 'quality', 'critique'],
        }

        lines = content.split("\n")
        
        # Parse frontmatter if present
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter = parts[1]
                for line in frontmatter.split("\n"):
                    if line.startswith("description:"):
                        description = line.split(":", 1)[1].strip().strip('"').strip("'")
                    elif line.startswith("execution_type:"):
                        execution_type = line.split(":", 1)[1].strip()
                    elif line.startswith("script_path:"):
                        script_path = line.split(":", 1)[1].strip()
        
        # If no frontmatter description, try first # heading after title
        if description == "Workspace Skill":
            for i, line in enumerate(lines[1:], 1):
                line = line.strip()
                if line.startswith("# ") and "Identity" not in line and "Purpose" not in line:
                    description = line.lstrip("# ").strip()
                    break
        
        # Use predefined keywords if available, else extract from content
        if name in skill_keywords:
            keywords = skill_keywords[name]
        else:
            keywords = self._extract_keywords(description, content)

        return Skill(
            name=name,
            description=description,
            content=content,
            workspace_path=skill_path,
            keywords=keywords,
            execution_type=execution_type,
            script_path=script_path,
        )

    def _extract_keywords(self, description: str, content: str) -> List[str]:
        """Extract keywords from skill description and content."""
        keywords = set()

        # Focus on description and first few sections for better keywords
        text = f"{description} {content}".lower()

        # Extract important words
        words = re.findall(r'\b[a-zA-Zα-ωά-ώ]{4,}\b', text)
        keywords.update(words)

        # Filter out common stopwords
        stopwords = {
            'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can',
            'had', 'her', 'was', 'one', 'our', 'out', 'has', 'have', 'been',
            'would', 'could', 'there', 'their', 'what', 'about', 'which',
            'when', 'make', 'like', 'time', 'just', 'know', 'take', 'into',
            'year', 'your', 'some', 'them', 'than', 'then', 'look', 'only',
            'come', 'its', 'over', 'think', 'also', 'back', 'after', 'use',
            'two', 'how', 'first', 'being', 'other', 'these', 'give', 'day',
            'used', 'using', 'from', 'this', 'that', 'with', 'will', 'each',
            'should', 'may', 'want', 'need', 'must', 'skill', 'identity', 
            'purpose', 'tasks', 'steps', 'example', 'parameters', 'reference', 
            'configuration', 'optional', 'required', 'always', 'never',
            'execute', 'return', 'following', 'section', 'details', 'information'
        }
        
        greek_stopwords = {
            'και', 'ή', 'το', 'την', 'τον', 'της', 'των', 'στο', 'στην',
            'στον', 'με', 'για', 'από', 'σε', 'ότι', 'είναι', 'μπορεί',
            'πρέπει', 'όπως', 'ήδη', 'κάθε', 'όλα', 'όλες', 'κάποιο',
            'κάποια', 'αυτό', 'αυτή', 'αυτά', 'εκεί', 'εδώ', 'μέσα',
            'του', 'μου', 'σου', 'μας', 'τους', 'αυτών', 'όποιο'
        }

        filtered = [w for w in keywords if w not in stopwords and w not in greek_stopwords]

        # Prioritize domain-specific keywords
        priority_keywords = {'search', 'web', 'research', 'email', 'calendar', 
                           'agenda', 'schedule', 'project', 'milestone', 'construction',
                           'compliance', 'technical', 'boq', 'estimate', 'crypto',
                           'content', 'distiller', 'loyalty', 'ratio', 'review',
                           'milestone', 'generator', 'team', 'manager', 'obsidian',
                           'rclone', 'saver', 'recoll', 'searxng', 'privacy'}

        prioritized = [w for w in filtered if w in priority_keywords]
        prioritized.extend([w for w in filtered if w not in priority_keywords][:30])

        return prioritized[:50]

    def get_all_skills(self) -> List[Skill]:
        return list(self.skills_cache.values())

    def get_skill(self, name: str) -> Optional[Skill]:
        return self.skills_cache.get(name)

    def detect_skill(self, message: str) -> Optional[Skill]:
        """
        Hybrid skill detection:
        1. Exact match (skill name in message)
        2. Keyword matching with weighted scoring
        3. Return None (no skill detected)
        """
        msg_lower = message.lower()

        # 1. Exact match - skill name in message
        for name, skill in self.skills_cache.items():
            if name.lower() in msg_lower:
                logger.info(f"Exact skill match: {name}")
                return skill

        # 2. Weighted keyword matching
        scores = {}
        for name, skill in self.skills_cache.items():
            score = 0
            skill_keywords = set(skill.keywords + [skill.name.lower()])
            
            msg_words = set(re.findall(r'\b[a-zA-Z]{3,}\b', msg_lower))
            
            for keyword in skill_keywords:
                if keyword.lower() in msg_words:
                    score += 1
                elif keyword in msg_lower:  # Partial match
                    score += 0.5
            
            if score > 0:
                scores[name] = score
        
        if scores:
            best_skill = max(scores, key=scores.get)
            if scores[best_skill] >= 1:  # Minimum threshold
                logger.info(f"Keyword match: {best_skill} (score: {scores[best_skill]})")
                return self.skills_cache[best_skill]

        return None

    async def execute_skill_script(
        self, 
        skill: Skill, 
        message: str, 
        user: str
    ) -> str:
        """Execute skill script and return output."""
        if skill.execution_type != "script":
            return ""

        if not skill.script_path:
            return f"[Error: Script path not defined for skill {skill.name}]"

        script_path = skill.script_path
        if not os.path.isabs(script_path):
            script_path = os.path.join(skill.workspace_path, script_path)

        if not os.path.exists(script_path):
            return f"[Error: Script not found: {script_path}]"

        try:
            cmd = ["python3", script_path, message, user]
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode != 0:
                logger.error(f"Script error: {stderr.decode()}")
                return f"[Error executing script: {stderr.decode()}]"
            
            return stdout.decode()
        except Exception as e:
            logger.error(f"Exception executing script: {e}")
            return f"[Error: {str(e)}]"

    def inject_context(
        self, 
        skill: Skill, 
        message: str, 
        script_output: Optional[str] = None
    ) -> str:
        """Inject skill context into the user message."""
        context_parts = [
            f"\n\n[SKILL ACTIVATED: {skill.name}]",
            f"Description: {skill.description}",
            f"\n{skill.content}",
        ]

        if script_output:
            context_parts.append(f"\n[SKILL OUTPUT]\n{script_output}")

        context_parts.append(f"\n[END SKILL CONTEXT]\n")

        return message + "".join(context_parts)

    def should_use_llm_routing(self, message: str) -> bool:
        """Check if message might need LLM routing (fallback for unclear cases)."""
        if self.detect_skill(message):
            return False

        routing_indicators = [
            'schedule', 'calendar', 'meeting', 'agenda', 'today', 'tomorrow',
            'search', 'research', 'web', 'find', 'look up', 'email', 'mail',
            'project', 'task', 'deadline', 'milestone', 'construction',
            'schedule', 'calendar', 'meeting', 'agenda', 'today', 'tomorrow',
            'πρόγραμμα', 'ημερολόγιο', 'συνάντηση', 'εργασία', 'σήμερα', 'αύριο',
            'email', 'έργο', 'προθεσμία', 'κατασκευή'
        ]
        
        msg_lower = message.lower()
        return any(indicator in msg_lower for indicator in routing_indicators)

    def get_llm_routing_prompt(self, message: str) -> str:
        """Generate LLM routing prompt for unclear cases."""
        skills_info = []
        for name, skill in self.skills_cache.items():
            skills_info.append(f"- {name}: {skill.description}")

        skills_str = "\n".join(skills_info) if skills_info else "No skills available."

        return f"""User message: {message}

Available skills:
{skills_str}

Should any skill be activated? Reply with:
- The skill name if a skill should be used
- "none" if no skill is needed

Reply only with the skill name or "none":"""


_skill_service_instance: Optional[SkillService] = None


def get_skill_service(workspace_root: str) -> SkillService:
    global _skill_service_instance
    if _skill_service_instance is None or _skill_service_instance.workspace_root != workspace_root:
        _skill_service_instance = SkillService(workspace_root)
    return _skill_service_instance
