import httpx
import json
import os
import re
import asyncio
from typing import Dict, List, Any
from app.core.patterns import PATTERNS_FILE, reload_patterns

class PatternSyncService:
    GITHUB_API_URL = "https://api.github.com/repos/danielmiessler/Fabric/contents/data/patterns"
    RAW_URL_BASE = "https://raw.githubusercontent.com/danielmiessler/Fabric/main/data/patterns"

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)

    async def fetch_pattern_list(self) -> List[str]:
        response = await self.client.get(self.GITHUB_API_URL)
        if response.status_code != 200:
            raise Exception(f"Failed to fetch pattern list: {response.status_code}")
        
        items = response.json()
        return [item["name"] for item in items if item["type"] == "dir"]

    async def fetch_pattern_content(self, pattern_name: str) -> str:
        url = f"{self.RAW_URL_BASE}/{pattern_name}/system.md"
        response = await self.client.get(url)
        if response.status_code != 200:
            return ""
        return response.text

    def sanitize_content(self, content: str) -> str:
        # Remove instructions that mention running fabric commands
        content = re.sub(r'fabric\s+--pattern\s+\S+', 'the current pattern', content, flags=re.IGNORECASE)
        content = re.sub(r'run\s+the\s+pattern', 'use the prompt', content, flags=re.IGNORECASE)
        # Remove any other specific fabric CLI mentions
        content = re.sub(r'fabric\s+', 'Gemini ', content, flags=re.IGNORECASE)
        return content

    async def sync_all(self):
        pattern_names = await self.fetch_pattern_list()
        new_patterns = {}
        explanations = []

        # Limit to first 50 for now to avoid hitting rate limits or taking too long
        # The user said "include the rest", but there are hundreds.
        # I'll try to get them all but maybe in batches if needed.
        # Actually, I'll just go for it and see.
        
        tasks = []
        for name in pattern_names:
            tasks.append(self.fetch_pattern_content(name))
        
        contents = await asyncio.gather(*tasks)

        for name, content in zip(pattern_names, contents):
            if content:
                sanitized = self.sanitize_content(content)
                new_patterns[name] = sanitized
                # Try to extract a short description (first sentence of IDENTITY and PURPOSE or similar)
                desc = self.extract_description(sanitized)
                explanations.append(f"{len(explanations)+1}. **{name}**: {desc}")

        new_patterns["__explanations__"] = "\n".join(explanations)

        with open(PATTERNS_FILE, "w", encoding="utf-8") as f:
            json.dump(new_patterns, f, indent=4)
        
        reload_patterns()
        return len(new_patterns) - 1 # exclude __explanations__

    def extract_description(self, content: str) -> str:
        # Look for the section between # IDENTITY and PURPOSE and the next header
        match = re.search(r'# IDENTITY and PURPOSE\n\n(.*?)(?=\n# |\Z)', content, re.DOTALL)
        if match:
            desc = match.group(1).strip()
            # Clean up: remove internal markdown headers if they exist in the desc
            desc = re.sub(r'^#+ .*?\n', '', desc, flags=re.MULTILINE)
            # Replace multiple newlines with a single space for a compact preview
            desc = re.sub(r'\n+', ' ', desc)
            # Limit length but provide much more than before
            if len(desc) > 300:
                return desc[:297] + "..."
            return desc
        return "No description available."

    async def close(self):
        await self.client.aclose()
