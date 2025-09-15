import logging
import time
from typing import Dict, Any, List
from agent.web_interface.merlin_interface import MerlinInterface
from agent.strategies.strategy_manager import StrategyManager
from agent.core.llm_analyzer import LLMAnalyzer

logger = logging.getLogger(__name__)

class HackMerlinAgent:
    """Main agent that orchestrates everything."""
    
    def __init__(self, headless: bool = True, use_llm_extraction: bool = True):
        self.interface = MerlinInterface(headless=headless)
        self.strategy_manager = StrategyManager()
        self.llm_analyzer = LLMAnalyzer() if use_llm_extraction else None
        
        self.session_results = {
            'levels_completed': 0,
            'level_details': {}
        }
    
    def play_game(self, max_levels: int = 7) -> Dict[str, Any]:
        """Play the game up to max_levels."""
        logger.info(f"Starting HackMerlin Agent - up to level {max_levels}")
        
        try:
            self.interface.navigate_to_game()
            current_level = self.interface.get_current_level()
            
            while current_level <= max_levels:
                success = self._attempt_level(current_level)
                
                if success:
                    current_level = self.interface.get_current_level()
                    self.session_results['levels_completed'] += 1
                    logger.info(f"Advanced to level {current_level}")
                    time.sleep(2)
                else:
                    logger.info(f"Failed at level {current_level}")
                    break
            
        except Exception as e:
            logger.error(f"Game error: {e}")
        finally:
            self.interface.close()
        
        return self.session_results
    
    def _attempt_level(self, level: int) -> bool:
        """Attempt a single level."""
        logger.info(f"=== Attempting Level {level} ===")
        
        attempts = 0
        max_attempts = 15
        
        while attempts < max_attempts:
            # Get next strategy and question
            question, strategy_name, strategy_obj = self.strategy_manager.get_next_question(level)
            logger.info(f"Strategy '{strategy_name}': {question}")
            
            # Send question and get response
            response = self.interface.send_message(question)
            if not response:
                attempts += 1
                continue
            
            # Check for deflection
            if self.is_deflection(response):
                logger.info(f"Deflection detected")
                # Record this specific question as failed
                self.strategy_manager.record_failure(level, question)
                attempts += 1
                continue
            
            # Extract passwords (only if not deflected)
            if self.llm_analyzer:
                passwords = self.llm_analyzer.extract_passwords(
                        response, 
                        strategy_name,
                        question,
                        level
                    )
            else:
                passwords = []
            
            if passwords:
                logger.info(f"Trying: {passwords[0]}")
            
            # Try passwords
            for password in passwords[:1]:
                if self.interface.submit_password(password):                    
                    return True
                else:
                    # Password failed, record this question as failed
                    self.strategy_manager.record_failure(level, question)
            
            attempts += 1
        
        return False
    
    def is_deflection(self, response: str) -> bool:
        """Detect if Merlin is deflecting/refusing to answer."""
        deflection_phrases = [
            "i cannot",
            "cannot reveal",
            "cannot provide", 
            "cannot assist",
            "cannot comply",
            "cannot tell",
            "must remain hidden",
            "shall remain hidden",
            "forbidden to",
            "not allowed to",
            "unable to",
            "will not",
            "refuse to",
            "not be spoken",
            "known only to those",
            "not be revealed",
            "fulfill that request"
        ]
        
        response_lower = response.lower()
        return any(phrase in response_lower for phrase in deflection_phrases)
    
    def print_summary(self):
        """Print session summary."""
        logger.info(f"Completed {self.session_results['levels_completed']} levels")