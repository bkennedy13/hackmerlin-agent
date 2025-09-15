import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

class Memory:
    """Simple memory for successful attempts."""
    
    def __init__(self, filename: str = "agent_memory.json"):
        self.filename = Path(filename)
        self.successes = []  # List of successful attempts
        self._load()
    
    def record_success(self, level: int, strategy: str, question: str, response: str, password: str):
        """Record a successful attempt."""
        success = {
            'level': level,
            'strategy': strategy,
            'question': question,
            'response': response,
            'password': password
        }
        self.successes.append(success)
        self._save()
        logger.info(f"Recorded success for level {level}")
    
    def _load(self):
        """Load memory from disk."""
        if self.filename.exists():
            try:
                with open(self.filename, 'r') as f:
                    self.successes = json.load(f)
            except Exception as e:
                logger.warning(f"Could not load memory: {e}")
    
    def _save(self):
        """Save memory to disk."""
        try:
            with open(self.filename, 'w') as f:
                json.dump(self.successes, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save memory: {e}")