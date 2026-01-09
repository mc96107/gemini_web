import json
import os
import logging

# Set up logging
logger = logging.getLogger(__name__)

PATTERNS_FILE = os.path.join(os.path.dirname(__file__), "../../data/patterns.json")

def load_patterns():
    if os.path.exists(PATTERNS_FILE):
        try:
            with open(PATTERNS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading patterns from {PATTERNS_FILE}: {e}")
            return {}
    else:
        logger.warning(f"Patterns file {PATTERNS_FILE} not found.")
        return {}

PATTERNS = load_patterns()

def reload_patterns():
    global PATTERNS
    PATTERNS.clear()
    PATTERNS.update(load_patterns())
    return PATTERNS
