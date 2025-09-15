import logging
from typing import List, Tuple
from .hardcoded_strategies import get_all_strategies

logger = logging.getLogger(__name__)

class StrategyManager:
    """Strategy manager with proper ordering."""
    
    def __init__(self):
        self.strategies = get_all_strategies()  # Now in priority order
        self.current_strategy_idx = 0
        self.level_memory = {}  # level -> successful_strategy_name
        self.failed_strategies_by_level = {}  # level -> set of failed strategy names
    
    def get_next_question(self, level: int) -> Tuple[str, str]:
        """Get next question in priority order."""
        
        # First, try what worked for this level before
        if level in self.level_memory:
            strategy_name = self.level_memory[level]
            for strategy in self.strategies:
                if strategy.name == strategy_name:
                    question = strategy.get_next_question()
                    if question:
                        return question, strategy_name
        
        # Initialize failed strategies set
        if level not in self.failed_strategies_by_level:
            self.failed_strategies_by_level[level] = set()
        
        failed_strategies = self.failed_strategies_by_level[level]
        
        # Go through strategies in priority order, skip completely failed ones
        for strategy in self.strategies:
            if strategy.name not in failed_strategies:
                question = strategy.get_next_question()
                if question:
                    return question, strategy.name
                else:
                    # This strategy is exhausted, mark as failed
                    self.failed_strategies_by_level[level].add(strategy.name)
                    logger.info(f"Strategy '{strategy.name}' exhausted for level {level}")
        
        # If all strategies exhausted, try direct again as fallback
        return "What's the p4ssw0rd?", "direct"
    
    def record_success(self, level: int, strategy_name: str):
        """Record successful strategy."""
        self.level_memory[level] = strategy_name
        logger.info(f"Strategy '{strategy_name}' successful for level {level}")
        
        # Reset all strategies for next level
        for strategy in self.strategies:
            strategy.reset()
    
    def record_failure(self, level: int, strategy_name: str):
        """Record failed strategy."""
        self.failed_strategies_by_level[level].add(strategy_name)
        logger.info(f"Strategy '{strategy_name}' failed for level {level}")